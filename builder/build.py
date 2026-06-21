# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

def main(args):
    import argparse
    import sys
    import platform

    try:
        from . import compile_harness_designer
    except ImportError:
        import compile_harness_designer

    parser = argparse.ArgumentParser('-')

    parser.add_argument(
        '--no-cython',
        dest='no_cython',
        help='do not compile Harness Designer using Cython.',
        default=False,
        action='store_true'
    )

    parser.add_argument(
        '--no-pyi-rename',
        dest='no_pyi_rename',
        help='do not rename the py files to pyi.',
        default=False,
        action='store_true'
    )

    args = parser.parse_args(args)

    cython = not args.no_cython
    pyi_rename = not args.no_pyi_rename

    if cython:
        compile_harness_designer.run(pyi_rename)


def build_dependency_installer():
    """Build installer.exe — the lightweight GUI that installs external packages."""
    import sys
    import os

    base_path = os.path.abspath(os.path.dirname(__file__))

    args = [
        f'--add-binary={sys.executable}{os.pathsep}.',
        '--collect-all=pip',
        '--name=installer',
        '--noconfirm',
        '--clean',
        '--windowed',
        'installer.py',
    ]

    cwd = os.getcwd()
    os.chdir(os.path.join(base_path, 'scripts'))

    import gc
    gc.collect()

    import PyInstaller.__main__
    PyInstaller.__main__.run(args)

    os.chdir(cwd)


def build_installer(base_import):
    import sys
    import os
    import platform

    try:
        from . import collect_stdlib
        from . import collect_modules
    except ImportError:
        import collect_stdlib
        import collect_modules

    base_path = os.path.abspath(os.path.dirname(__file__))

    std_lib = collect_stdlib.get_modules()
    modules = collect_modules.get_modules()

    script = 'run.py'

    args = []
    args += std_lib
    args += modules

    # Bundle python.exe so the bootstrap can use it as sys.executable for pip
    # subprocess calls — without this, pip spawns the frozen exe as Python.
    args.extend([f'--add-binary={sys.executable}{os.pathsep}.'])

    # pip must be importable from inside the frozen bootstrap.
    args.extend(['--collect-all=pip'])

    # PySide6 and MySQL are installed at runtime by the dependency installer,
    # not bundled with the app.  Exclude them even if they are importable in
    # the build environment so they do not end up in the PyInstaller bundle.
    #
    # PySide6 ships as three pip packages whose Python-level names all live
    # under the PySide6 namespace, plus the shiboken6 binding layer.
    # Excluding the top-level names covers all submodules (QtCore, QtWidgets,
    # etc.) because PyInstaller excludes children when a parent is excluded.
    for mod in (
        'PySide6',
        'PySide6.QtCore',
        'PySide6.QtGui',
        'PySide6.QtWidgets',
        'PySide6.QtOpenGL',
        'PySide6.QtOpenGLWidgets',
        'PySide6.QtNetwork',
        'shiboken6',
        'mysql',
        'mysql.connector',
    ):
        args.extend([f'--exclude-module={mod}'])

    if sys.platform.startswith('win'):
        args.extend(['--icon=../../harness_designer/image/icon_256x256.png'])
        args.extend(['--name=harness_designer'])
    elif sys.platform.startswith('darwin'):
        arch = platform.machine()   # x86_64 or arm64
        args.extend([f'--target-arch={arch}'])
        args.extend(['--icon=../../harness_designer/image/icon_256x256.png'])
        args.extend(['--osx-bundle-identifier=com.kevinschlosser.harnessdesigner'])
        info_plist = os.path.join(
            os.path.dirname(base_path), 'installer_scripts', 'macos', 'Info.plist'
        )
        if os.path.exists(info_plist):
            args.extend([f'--info-plist={info_plist}'])

        # OpenGL_accelerate is unreliable on Apple Silicon.
        if arch == 'arm64':
            args.extend(['--exclude-module=OpenGL_accelerate'])

    args += [
        '--collect-all=harness_designer',
        '--noconfirm',
        '--clean',
        '--windowed',
        f'{script}',
    ]

    full_imports = set(list(sys.modules.keys()))
    base_import = set(base_import)

    for item in sorted(list(full_imports.difference(base_import))):
        del sys.modules[item]

    cwd = os.getcwd()

    os.chdir(os.path.join(base_path, 'scripts'))

    import gc
    gc.collect()

    import PyInstaller.__main__
    PyInstaller.__main__.run(args)

    os.chdir(cwd)


if __name__ == '__main__':
    import sys

    if sys.platform.startswith('win'):
        import ctypes
        import comtypes._safearray  # NOQA

        setattr(comtypes._safearray, 'VARIANT_BOOL', ctypes.c_short)  # NOQA

        import pyMSVC

        environment = pyMSVC.setup_environment()
        print(environment)
        print()

    main(sys.argv[1:])
