#!/usr/bin/env python3
# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>
#
# Full local build, start to finish, with no stale state left over from a
# previous run: wipe every build-output directory, uninstall any existing
# harness_designer from this interpreter, reinstall it fresh from this repo
# (cythonizing everything), freeze it with PyInstaller, then package the
# platform installer.
#
# No arguments -- run it with whichever interpreter should do the build:
#   py -3.11 manual_build.py
#
# Does NOT run builder.build_native_deps (building assimp from source via
# CMake/Ninja) -- that's a once-per-libs/assimp-change step, not a normal
# per-build one, and isn't run here. Run it yourself first if the assimp
# submodule changed.
#
# Each of the three steps below (pip install ., python -m builder, python -m
# builder.installer) is run with subprocess.run() and NO stdout/stderr
# capture -- deliberately not through builder/spawn.py's spawn(). spawn()
# exists for leaf-level compiler invocations (one cl.exe/link.exe/cmake call
# at a time from compiler.py's own thread pool) specifically because
# capturing a child's output through a pipe risks a Windows deadlock if that
# child's own grandchild inherits the pipe's write handle and never closes
# it. Each step here is itself an ORCHESTRATOR that fans out into many of
# its own subprocesses internally (pip install . alone spawns dozens of
# parallel cl.exe invocations via that same thread pool) -- wrapping one of
# these in another layer of piped capture hands that same deadlock risk to
# every grandchild it spawns, and was confirmed to actually hang this way
# (2026-10-19). Not capturing output at all sidesteps the problem instead of
# needing spawn()'s draining-loop workaround: with no pipe, there's no EOF
# signal for a grandchild to withhold, so it doesn't matter how many
# subprocesses a step spawns underneath. This also gives a fully reliable
# return code, which spawn() cannot (see its own header comment).

import os
import shutil
import subprocess
import sys
import tempfile
import time

REPO_ROOT = os.path.dirname(os.path.abspath(__file__))

_CLEAN_DIRS = (
    'build',
    'dist',
    os.path.join('builder', 'scripts', 'build'),
    os.path.join('builder', 'scripts', 'dist'),
)


def _banner(text):
    print(f'\n=== {text} ===\n', flush=True)


def clean():
    _banner('Cleaning build directories')
    for rel in _CLEAN_DIRS:
        path = os.path.join(REPO_ROOT, rel)
        if os.path.isdir(path):
            print(f'Removing {path}')
            shutil.rmtree(path, ignore_errors=True)
        else:
            print(f'Already clean: {path}')


def _harness_designer_importable():
    # cwd=tempdir, not REPO_ROOT -- `python -c` puts cwd on sys.path, and
    # REPO_ROOT contains a real harness_designer/ source directory that
    # would shadow the installed (possibly cythonized) copy, making a
    # failed install look like a success.
    result = subprocess.run(
        [sys.executable, '-c', 'import harness_designer'],
        cwd=tempfile.gettempdir(),
    )
    return result.returncode == 0


def _onedir_output_exists():
    dist_dir = os.path.join(REPO_ROOT, 'builder', 'scripts', 'dist')
    dep_installer = 'dep_installer.exe' if sys.platform.startswith('win') else 'dep_installer'
    return (
        os.path.exists(os.path.join(dist_dir, dep_installer))
        and os.path.isdir(dist_dir)
        and any(
            name not in ('dep_installer.exe', 'dep_installer')
            for name in os.listdir(dist_dir)
        )
    )


def _installer_output_exists():
    dist_dir = os.path.join(REPO_ROOT, 'dist')
    if not os.path.isdir(dist_dir):
        return False
    for _root, _dirs, files in os.walk(dist_dir):
        if files:
            return True
    return False


def run_step(cmd_parts, verify=None):
    _banner('Running: ' + ' '.join(cmd_parts))
    result = subprocess.run(cmd_parts, cwd=REPO_ROOT)

    if result.returncode != 0:
        raise RuntimeError(f'command failed ({result.returncode}): {" ".join(cmd_parts)}')

    if verify is not None and not verify():
        raise RuntimeError(f'command exited 0 but verification failed: {" ".join(cmd_parts)}')


def main():
    started = time.monotonic()

    clean()

    # Best-effort -- a nonzero exit here just means harness_designer wasn't
    # currently installed, which is normal and not a real failure.
    subprocess.run([sys.executable, '-m', 'pip', 'uninstall', '-y', 'harness_designer'],
                   cwd=REPO_ROOT)

    run_step(
        [sys.executable, '-m', 'pip', 'install', '-v', '.', '--no-input'],
        verify=_harness_designer_importable,
    )
    run_step([sys.executable, '-m', 'builder'], verify=_onedir_output_exists)
    run_step([sys.executable, '-m', 'builder.installer'], verify=_installer_output_exists)

    elapsed = time.monotonic() - started
    _banner(f'Build complete in {elapsed / 60:.1f} minutes')


if __name__ == '__main__':
    main()
