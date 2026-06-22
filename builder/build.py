# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

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

    info_plist = None
    if sys.platform.startswith('win'):
        args.extend(['--icon=../../harness_designer/image/icon_256x256.png'])
        args.extend(['--name=harness_designer'])
    elif sys.platform.startswith('darwin'):
        arch = platform.machine()   # x86_64 or arm64
        args.extend([f'--target-arch={arch}'])
        args.extend(['--icon=../../harness_designer/image/icon_256x256.png'])
        args.extend(['--name=harness_designer'])
        args.extend(['--osx-bundle-identifier=com.kevinschlosser.harnessdesigner'])
        _candidate = os.path.join(
            os.path.dirname(base_path), 'installer_scripts', 'macos', 'Info.plist'
        )
        if os.path.exists(_candidate):
            info_plist = _candidate

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

    scripts_dir = os.path.join(base_path, 'scripts')
    os.chdir(scripts_dir)

    # --noconfirm overwrites files but os.symlink() raises FileExistsError if a
    # symlink already exists (common on macOS re-runs in CI).  Remove the old
    # output directory explicitly so PyInstaller starts with a clean slate.
    import shutil
    for candidate in ('harness_designer.app', 'harness_designer'):
        old_dist = os.path.join(scripts_dir, 'dist', candidate)
        if os.path.exists(old_dist):
            shutil.rmtree(old_dist)
            break

    import gc
    gc.collect()

    import PyInstaller.__main__
    PyInstaller.__main__.run(args)

    # --info-plist is not a valid PyInstaller CLI flag; merge custom keys into
    # the generated Info.plist after the build instead.
    if info_plist:
        import plistlib
        app_plist = os.path.join(
            scripts_dir, 'dist', 'harness_designer.app', 'Contents', 'Info.plist'
        )
        if os.path.exists(app_plist):
            with open(app_plist, 'rb') as _f:
                _app_data = plistlib.load(_f)
            with open(info_plist, 'rb') as _f:
                _custom = plistlib.load(_f)
            _app_data.update(_custom)
            with open(app_plist, 'wb') as _f:
                plistlib.dump(_app_data, _f)

    os.chdir(cwd)
