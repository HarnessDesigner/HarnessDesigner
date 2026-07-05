# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>
#
# Per-platform compile/link for the .c files Cython generates. Every file
# gets the exact same arguments — there's no per-module customization here,
# since the two hand-written extensions (bvh/culling) don't need anything
# the auto-discovered modules don't also get for free (numpy's include dir
# and API macro are harmless on files that don't touch numpy's C API).
#
# POSIX flags are derived from sysconfig, which already encodes the correct
# platform-specific recipe (e.g. -fPIC on Linux; -arch arm64 -arch x86_64
# -fno-common -dynamic for a universal2 build on macOS) — confirmed against
# real captured compile/link lines from this project's own CI runs. Windows
# has no sysconfig equivalent, so its flags are the stable, hardcoded recipe
# distutils._msvccompiler has used since Python 3.5, also confirmed against
# a captured CI log. MSVC/Windows-SDK include and lib search paths are not
# re-specified here — cl.exe/link.exe auto-search the INCLUDE/LIB
# environment variables, which builder.msvc_env.activate() already sets.

import concurrent.futures
import os
import sys
import sysconfig

from . import spawn

_DEFINES = [('NPY_NO_DEPRECATED_API', 'NPY_1_7_API_VERSION')]


def ext_suffix():
    return sysconfig.get_config_var('EXT_SUFFIX')


def python_include_dir():
    return sysconfig.get_paths()['include']


def _module_init_name(dotted_name):
    return dotted_name.rsplit('.', 1)[-1]


def _quote(arg):
    return f'"{arg}"' if ' ' in arg else arg


def _run(cmd_parts, expected_output):
    """Run a command via spawn.spawn() and verify it actually produced
    expected_output.

    Every subprocess in this codebase goes through spawn.spawn() — its
    stdout/stderr collection loop is the one working way to read both pipes
    from a child process on Windows without deadlocking (Windows has no
    equivalent of POSIX's non-blocking-pipe-fd trick), so its internals are
    off limits here regardless of what else changes.

    spawn.spawn()'s own returncode isn't trustworthy for detecting failure
    though — it pipes cmd into a bare shell's stdin rather than running it
    directly (`cmd.exe`/`bash` with no `/c`/`-c`), and on Windows a bare
    `cmd.exe` fed a command this way exits 0 on natural EOF regardless of
    that command's own exit status. So failure is decided here instead, from
    what spawn.spawn() returns: a nonzero returncode, a missing expected
    output file, or stderr text that doesn't look like a warning all raise.
    Checking for "warning" (lowercased first, so casing can't dodge the
    check) rather than "error" is deliberate — Cython-generated C is full of
    identifiers containing "error" as a plain substring (its own goto-label
    exception-propagation convention names things like __pyx_L1_error,
    __PYX_ERR), which GCC/Clang echo back verbatim as source-code context
    on plain warnings, giving false positives on an "error" check that have
    nothing to do with diagnostic severity. Neither compiler generates
    identifiers containing "warning", so it's the reliable signal here.

    Returns the captured stderr text (empty string if none) on success.
    """
    # Remove any stale output from a previous run first — otherwise a
    # leftover file from an earlier successful build could make this run's
    # failure look like a success purely because the file already existed.
    if os.path.exists(expected_output):
        os.remove(expected_output)

    cmd = ' '.join(_quote(p) for p in cmd_parts)
    returncode, error_text = spawn.spawn(cmd)

    is_error = (
        returncode != 0
        or not os.path.exists(expected_output)
        or (error_text and 'warning' not in error_text.lower())
    )
    if is_error:
        raise RuntimeError(
            f'command failed ({returncode}), expected output missing: '
            f'{expected_output!r}\n{cmd}\n{error_text}'
        )

    return error_text


def _posix_compile_cmd(c_path, obj_path, include_dirs):
    cmd = sysconfig.get_config_var('CC').split()
    cmd += sysconfig.get_config_var('CFLAGS').split()

    # distutils compiles files destined for a shared object with
    # CFLAGS + CCSHARED, not CFLAGS alone (see customize_compiler() /
    # compiler_so in distutils.sysconfig) — CCSHARED is -fPIC on Linux.
    # Omitting it links fine on macOS (PIC is the default there) but fails
    # on Linux with "recompile with -fPIC".
    ccshared = sysconfig.get_config_var('CCSHARED')
    if ccshared:
        cmd += ccshared.split()

    if sys.platform.startswith('linux'):
        cmd.append('-Wno-error=maybe-uninitialized')

    for macro, value in _DEFINES:
        cmd.append(f'-D{macro}={value}')

    for include_dir in include_dirs:
        cmd.append(f'-I{include_dir}')

    cmd += ['-c', c_path, '-o', obj_path]
    return cmd


def _posix_link_cmd(obj_path, out_path):
    cmd = sysconfig.get_config_var('LDSHARED').split()
    cmd += [obj_path, '-o', out_path]
    return cmd


def _windows_compile_cmd(c_path, obj_path, include_dirs):
    cmd = ['cl.exe', '/c', '/nologo', '/O2', '/W3', '/GL', '/DNDEBUG', '/MD']

    for macro, value in _DEFINES:
        cmd.append(f'/D{macro}={value}')

    for include_dir in include_dirs:
        cmd.append(f'-I{include_dir}')

    cmd += [f'/Tc{c_path}', f'/Fo{obj_path}']
    return cmd


def _windows_link_cmd(obj_path, out_path, dotted_name):
    libs_dir = os.path.join(sys.base_prefix, 'libs')
    init_name = _module_init_name(dotted_name)
    # /GL (compile step) requires /LTCG at link time, and /INCREMENTAL:NO
    # pairs with /LTCG (incremental linking is incompatible with it).
    # /IMPLIB is derived from obj_path, which the caller places in a scratch
    # obj_dir — not next to the final .pyd — so the .lib (and the .exp
    # link.exe writes alongside it automatically) never end up in the
    # staged wheel tree.
    implib_path = obj_path + '.lib'
    return [
        'link.exe', '/nologo', '/DLL', '/INCREMENTAL:NO', '/LTCG',
        f'/LIBPATH:{libs_dir}',
        f'/EXPORT:PyInit_{init_name}',
        obj_path,
        f'/OUT:{out_path}',
        f'/IMPLIB:{implib_path}',
    ]


def compile_one(dotted_name, c_path, output_path, obj_dir, include_dirs):
    """Compile one Cython-generated .c file into its final .pyd/.so.

    Intermediate artifacts (.obj/.o, and on Windows the .lib/.exp
    import-library byproducts) are written to obj_dir — a scratch directory
    entirely separate from output_path's directory, which is the staging
    tree that gets zipped into the wheel. Naming the object file after
    dotted_name (globally unique) rather than mirroring the package
    directory structure means obj_dir doesn't need subdirectories at all.

    Returns this module's combined warning text (empty string if none).
    Raises if either step fails outright — see _run().
    """
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    os.makedirs(obj_dir, exist_ok=True)

    obj_ext = '.obj' if sys.platform.startswith('win') else '.o'
    obj_path = os.path.join(obj_dir, dotted_name + obj_ext)

    if sys.platform.startswith('win'):
        compile_warning = _run(_windows_compile_cmd(c_path, obj_path, include_dirs), obj_path)
        link_warning = _run(_windows_link_cmd(obj_path, output_path, dotted_name), output_path)
    else:
        compile_warning = _run(_posix_compile_cmd(c_path, obj_path, include_dirs), obj_path)
        link_warning = _run(_posix_link_cmd(obj_path, output_path), output_path)

    return '\n'.join(w for w in (compile_warning, link_warning) if w)


def compile_all(jobs, max_workers=None):
    """jobs: iterable of (dotted_name, c_path, output_path, obj_dir, include_dirs).

    Every job runs to completion regardless of whether earlier ones failed
    or warned — both are collected, not acted on immediately, so a single
    bad or noisy file doesn't cut the batch short and hide whatever else is
    also wrong. Warnings are printed together (grouped by module) once
    everything's done, so they're easy to review and address, but they
    don't fail the build. Errors are also reported together, and if there
    are any, the build fails after every job has finished and been reported.
    """
    max_workers = max_workers or os.cpu_count()

    failures = []
    warnings = []

    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as pool:
        future_to_name = {
            pool.submit(compile_one, dotted_name, c_path, output_path, obj_dir, include_dirs): dotted_name
            for dotted_name, c_path, output_path, obj_dir, include_dirs in jobs
        }
        for future in concurrent.futures.as_completed(future_to_name):
            dotted_name = future_to_name[future]
            try:
                warning_text = future.result()
            except Exception as exc:
                failures.append(f'{dotted_name}:\n{exc}')
            else:
                if warning_text:
                    warnings.append(f'{dotted_name}:\n{warning_text}')

    if warnings:
        print(f'\n{len(warnings)} module(s) compiled with warnings:\n')
        print('\n\n'.join(warnings))
        print()

    if failures:
        raise RuntimeError(
            f'{len(failures)} of {len(future_to_name)} module(s) failed to compile:\n\n'
            + '\n\n'.join(failures)
        )
