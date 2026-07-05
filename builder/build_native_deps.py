# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>
#
# Builds assimp from source (CMake + Ninja) and installs pyassimp's Python
# bindings against it, vendoring the compiled assimp shared library into
# wherever pip installed pyassimp — upstream's PyAssimp setup.py has no
# package_data for the compiled library, so pyassimp.helper.search_library()
# can't find it otherwise.
#
# Must run before `pip install .` for harness_designer itself, which depends
# on pyassimp being importable.
#
# Usage:
#   python -m builder.build_native_deps [--debug]

import argparse
import importlib.util
import os
import shutil
import subprocess
import sys

from . import msvc_env, spawn


def main():
    parser = argparse.ArgumentParser(
        description='Build assimp from source and install pyassimp against it.',
    )
    parser.add_argument(
        '--debug', action='store_true',
        help='Build assimp in Debug mode instead of Release (for local debugging).',
    )
    args = parser.parse_args()

    # cmake/ninja need the MSVC toolchain on PATH to find cl.exe; no-op on
    # non-Windows platforms.
    msvc_env.activate()

    # Without an explicit build type, assimp's CMakeLists defaults to a Debug
    # build — hence the "d" suffix on assimp-vc*-mtd.dll and the multi-hundred-MB
    # .pdb/.ilk files that come with it. --debug opts back into that for local
    # debugging; everything else (including CI) gets a proper Release build.
    cmake_build_type = '' if args.debug else ' -DCMAKE_BUILD_TYPE=Release'

    p_cmd = (
        'cd libs/assimp&&'
        f'cmake -G Ninja -DASSIMP_BUILD_TESTS=off -DASSIMP_INSTALL=off{cmake_build_type} -S . -B build&&'
        'cd build&&'
        'ninja'
    )

    if sys.platform.startswith('linux'):
        os.environ['CPPFLAGS'] = '-Wno-error=maybe-uninitialized'
        os.environ['CFLAGS'] = '-Wno-error=maybe-uninitialized'
        os.environ['CXXFLAGS'] = '-Wno-error=maybe-uninitialized'

    spawn.spawn(p_cmd)

    base_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))

    assimp_binary_path = os.path.join(base_path, 'libs/assimp/build/bin')
    assimp_path = os.path.join(base_path, 'libs/assimp/port/PyAssimp')
    assimp_lib_path = os.path.join(assimp_path, 'pyassimp')

    # Rename pyproject.toml if present so pip uses the legacy setup.py path
    # and does not attempt an isolated build (which would lose the pre-copied DLLs).
    toml_path = os.path.join(assimp_path, 'pyproject.toml')
    toml_bak = toml_path + '.bak'
    if os.path.exists(toml_path) and not os.path.exists(toml_bak):
        os.rename(toml_path, toml_bak)

    for file in os.listdir(assimp_binary_path):
        if (
            not file.endswith('.so') and
            not file.endswith('.dll') and
            not file.endswith('.dylib')
        ):
            continue

        src = os.path.join(assimp_binary_path, file)
        dst = os.path.join(assimp_lib_path, file)
        shutil.copyfile(src, dst)

    os.environ['PATH'] += os.pathsep + assimp_binary_path
    if sys.platform.startswith('darwin'):
        dyld = os.environ.get('DYLD_LIBRARY_PATH', '')
        os.environ['DYLD_LIBRARY_PATH'] = assimp_binary_path + (os.pathsep + dyld if dyld else '')
    elif sys.platform.startswith('linux'):
        ld = os.environ.get('LD_LIBRARY_PATH', '')
        os.environ['LD_LIBRARY_PATH'] = assimp_binary_path + (os.pathsep + ld if ld else '')

    try:
        subprocess.run(
            [sys.executable, '-m', 'pip', 'install', '--no-build-isolation', assimp_path],
            check=True,
        )
    finally:
        if os.path.exists(toml_bak):
            if os.path.exists(toml_path):
                os.remove(toml_path)

            os.rename(toml_bak, toml_path)

    # The upstream PyAssimp setup.py has no package_data for the compiled
    # assimp library, so pip only installs the Python files.  Find where
    # pyassimp landed in site-packages and copy the library there so that
    # pyassimp.helper.search_library() can find it at import time.
    importlib.invalidate_caches()
    spec = importlib.util.find_spec('pyassimp')
    if spec and spec.origin:
        installed_pkg_dir = os.path.dirname(spec.origin)
        for file in os.listdir(assimp_binary_path):
            if (
                not file.endswith('.so') and
                not file.endswith('.dll') and
                not file.endswith('.dylib')
            ):
                continue

            src = os.path.join(assimp_binary_path, file)
            dst = os.path.join(installed_pkg_dir, file)
            shutil.copyfile(src, dst)


if __name__ == '__main__':
    main()
