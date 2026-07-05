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


def _run(cmd_parts):
    cmd = ' '.join(_quote(p) for p in cmd_parts)
    returncode, error_lines = spawn.spawn(cmd)
    if returncode != 0:
        raise RuntimeError(
            f'command failed ({returncode}): {cmd}\n' + '\n'.join(error_lines)
        )


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
    # /IMPLIB is redirected next to the object file — otherwise link.exe
    # drops an unwanted .lib import file next to the .pyd in the staged
    # wheel tree.
    implib_path = obj_path + '.lib'
    return [
        'link.exe', '/nologo', '/DLL', '/INCREMENTAL:NO', '/LTCG',
        f'/LIBPATH:{libs_dir}',
        f'/EXPORT:PyInit_{init_name}',
        obj_path,
        f'/OUT:{out_path}',
        f'/IMPLIB:{implib_path}',
    ]


def compile_one(dotted_name, c_path, output_path, include_dirs):
    """Compile one Cython-generated .c file into its final .pyd/.so."""
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    obj_path = output_path + ('.obj' if sys.platform.startswith('win') else '.o')

    if sys.platform.startswith('win'):
        _run(_windows_compile_cmd(c_path, obj_path, include_dirs))
        _run(_windows_link_cmd(obj_path, output_path, dotted_name))
    else:
        _run(_posix_compile_cmd(c_path, obj_path, include_dirs))
        _run(_posix_link_cmd(obj_path, output_path))


def compile_all(jobs, max_workers=None):
    """jobs: iterable of (dotted_name, c_path, output_path, include_dirs)."""
    max_workers = max_workers or os.cpu_count()

    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as pool:
        futures = [
            pool.submit(compile_one, dotted_name, c_path, output_path, include_dirs)
            for dotted_name, c_path, output_path, include_dirs in jobs
        ]
        for future in concurrent.futures.as_completed(futures):
            future.result()
