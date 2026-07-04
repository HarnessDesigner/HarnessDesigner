# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

def main():
    import sys

    base_import = list(sys.modules.keys())

    import os
    import shutil
    from builder import spawn

    build_installer = False
    debug_build = False
    installer_args = []

    for i, arg in enumerate(sys.argv[:]):

        if arg == '--installer':
            sys.argv.remove(arg)
            build_installer = True

        if arg == '--no-cython':
            sys.argv.remove(arg)
            installer_args.append('--no-cython')

        if arg == '--debug':
            sys.argv.remove(arg)
            debug_build = True

    if sys.platform.startswith('win'):
        import ctypes
        import comtypes._safearray  # NOQA

        setattr(comtypes._safearray, 'VARIANT_BOOL', ctypes.c_short)  # NOQA

        import pyMSVC

        env = pyMSVC.setup_environment()
        print(env)
        print()

    from setuptools import setup

    # Without an explicit build type, assimp's CMakeLists defaults to a Debug
    # build — hence the "d" suffix on assimp-vc*-mtd.dll and the multi-hundred-MB
    # .pdb/.ilk files that come with it. --debug opts back into that for local
    # debugging; everything else (including CI) gets a proper Release build.
    cmake_build_type = '' if debug_build else ' -DCMAKE_BUILD_TYPE=Release'

    p_cmd = (
        'cd libs/assimp&&'
        f'cmake -G Ninja -DASSIMP_BUILD_TESTS=off -DASSIMP_INSTALL=off{cmake_build_type} -S . -B build&&'
        'cd build&&'
        'ninja'
    )

    spawn.spawn(p_cmd)

    base_path = os.path.dirname(__file__)

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
            not file.endswith('.dynlib')
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

    import importlib.util
    import subprocess
    try:
        subprocess.run(
            [sys.executable, '-m', 'pip', 'install', '--no-build-isolation', assimp_path],
            check=True,
        )
    finally:
        if os.path.exists(toml_bak):
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
                not file.endswith('.dynlib')
            ):
                continue

            src = os.path.join(assimp_binary_path, file)
            dst = os.path.join(installed_pkg_dir, file)
            shutil.copyfile(src, dst)

    while base_path in sys.path:
        sys.path.remove(base_path)

    sys.path.insert(0, base_path)

    os.chdir(base_path)

    from builder import build_pyx

    build_pyx.run('harness_designer')

    from setuptools import find_packages

    packages = ['harness_designer.' + pack for pack in find_packages("harness_designer")]
    packages.insert(0, 'harness_designer')

    setup(
        name="harness_designer",
        version="0.0.1",
        author='Kevin G. Schlosser',
        description="Wiring harness design software.",
        url="https://github.com/HarnessDesigner/HarnessDesigner",
        packages=packages,
        zip_safe=False,
        setup_requires=[
            "setuptools==62.0.0",
            "Cython==3.2.4",
            "wheel==0.46.3",
            "pyinstaller==6.19.0",
            "pyMSVC@git+https://github.com/kdschlosser/python_msvc ; sys_platform=='win32'",
        ],
        install_requires=[
            "PySide6==6.11.1",
            "PyOpenGL==3.1.10",
            "PyOpenGL-accelerate==3.1.10; sys_platform != 'darwin' or platform_machine == 'x86_64'",
            "requests==2.33.1",
            "numpy==2.2.6",
            "pillow==12.2.0",
            "mpmath==1.3.0",
            "lib3mf==2.4.1.post1",
            "ezdxf==1.4.3",
            "scipy==1.17.1",
            "sympy==1.14.0",
            "pyfqmr==0.4.0",
            "meshio==5.3.5",
            "cadquery-ocp==7.8.1.1",
            "build123d==0.10.0",
            "keyring==25.7.0",
            "pyopencl==2026.1.2",
            "pandas==3.0.3",
            'apple_smi==0.1.4; sys_platform == "darwin"',
            'nvidia-ml-py==13.610.43; sys_platform != "darwin"',
            'amdsmi==7.0.2; sys_platform != "darwin"',
            "pyassimp",
        ]
    )

    # Every `builder` submodule needed past this point must be imported now,
    # while base_path is still on sys.path — once it comes off below, `builder`
    # itself becomes unresolvable (base_path is also what made it importable
    # in the first place), so there is no safe point to import it later.
    from builder import compile_harness_designer
    from builder import build
    from builder import installer

    # setup() just installed a plain, uncompiled copy of harness_designer into
    # site-packages. Everything imported since the top of this function must
    # be purged from sys.modules now — merely changing sys.path does not undo
    # an already-cached import, so without this, `import harness_designer`
    # below could silently return a copy already cached from the repo.
    full_imports = set(sys.modules.keys())
    for item in sorted(full_imports.difference(base_import)):
        del sys.modules[item]

    # base_path must come off sys.path before the import below, otherwise it
    # resolves to the repo instead of the installed copy — and
    # compile_harness_designer deletes .py sources after compiling them, so
    # pointed at the repo it wipes out the source tree instead of the install.
    while base_path in sys.path:
        sys.path.remove(base_path)

    import harness_designer

    hd_path = os.path.dirname(harness_designer.__file__)

    # Hard safety check: hd_path must never be inside the repo. If it is, the
    # cleanup above failed silently, and letting compile_harness_designer run
    # against this path would delete the repo's source tree instead of the
    # installed copy in site-packages — abort loudly instead.
    _hd_abs = os.path.abspath(hd_path)
    _base_abs = os.path.abspath(base_path)
    if os.path.commonpath([_hd_abs, _base_abs]) == _base_abs:
        raise RuntimeError(
            f'harness_designer resolved to {hd_path!r}, inside the repo '
            f'({base_path!r}) instead of the installed site-packages copy. '
            'Refusing to compile — this would delete the repo source tree.'
        )

    compile_harness_designer.run(hd_path, False)

    path = 'harness_designer'

    def iter_harness_designer(p=''):
        if p:
            dpath = os.path.join(path, p)
        else:
            dpath = path

        for file_path in os.listdir(dpath):
            if file_path == '__pycache__':
                continue

            src_ = os.path.join(dpath, file_path)
            if os.path.isdir(src_):
                if p:
                    iter_harness_designer(os.path.join(p, file_path))
                else:
                    iter_harness_designer(file_path)

            elif (
                src_.endswith('.png') or
                src_.endswith('.pyi') or
                src_.endswith('.pyd') or
                src_.endswith('.so')
            ):
                if p:
                    dst_ = os.path.join(hd_path, p)
                else:
                    dst_ = os.path.join(hd_path)

                if not os.path.exists(dst_):
                    os.makedirs(dst_)

                dst_ = os.path.join(dst_, file_path)

                try:
                    shutil.copyfile(src_, dst_)
                except:  # NOQA
                    pass

    iter_harness_designer()

    if build_installer:
        os.chdir(base_path)

        # build/installer were already imported above, before base_path came
        # off sys.path — re-importing `builder` here would fail.
        from harness_designer import __version__

        build.build_installer(base_import)
        build.build_dependency_installer()

        if sys.platform.startswith('win'):
            installer.build_windows(__version__.string)

        elif sys.platform == 'darwin':
            installer.build_macos(__version__.string, False)
        else:
            installer.build_linux(__version__.string)


if __name__ == '__main__':
    main()
