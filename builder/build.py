# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

def build_dependency_installer():
    """Build installer.exe — the lightweight GUI that installs external packages."""
    import sys
    import os

    base_path = os.path.abspath(os.path.dirname(__file__))

    args = [
        f'--add-binary={sys.executable}{os.pathsep}.',
        '--collect-all=pip',
        # distlib.resources.finder() resolves finders by loader type; PyInstaller's
        # FrozenImporter is not registered, causing DistlibException at pip import
        # time.  This hook patches finder() before installer.py runs.
        '--runtime-hook=rthook_pip_distlib.py',
        '--name=installer',
        '--onefile',
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


def _clean_dist(app_dir):
    """
    Remove files and directories from a PyInstaller onedir (or .app bundle)
    that are not needed at runtime, reducing installer size.

    Removes:
      - .pyi  — type stubs (IDE-only, never imported)
      - .pyx  — Cython sources (already compiled to .so / .pyd)
      - .c / .cpp / .h — C/C++ sources that slipped through data collection
      - *.dist-info/  — package metadata (not used inside a frozen app)
      - __pycache__/  — bytecode cache dirs (frozen app uses its own archive)
      - empty directories left over after the above removals
    """
    import os
    import shutil

    _REMOVE_EXTS = frozenset(['.pyi', '.pyx', '.c', '.cpp', '.h'])

    n_files = 0
    n_dirs = 0

    for root, dirs, files in os.walk(app_dir, topdown=False):
        # Remove unwanted files
        for fname in files:
            if os.path.splitext(fname)[1] in _REMOVE_EXTS:
                try:
                    os.remove(os.path.join(root, fname))
                    n_files += 1
                except OSError:
                    pass

        # Remove unwanted directories
        for dname in dirs:
            if dname == '__pycache__' or dname.endswith('.dist-info'):
                try:
                    shutil.rmtree(os.path.join(root, dname), ignore_errors=True)
                    n_dirs += 1
                except OSError:
                    pass

        # Remove the directory itself if it is now empty (skip root)
        if root != app_dir and os.path.isdir(root):
            try:
                os.rmdir(root)
                n_dirs += 1
            except OSError:
                pass

    print(f'_clean_dist: removed {n_files} files, {n_dirs} directories from {app_dir}')


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
    test_excludes = collect_modules.get_test_excludes()

    script = 'run.py'

    args = []
    args += std_lib
    args += modules
    args += test_excludes

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
        # optional extras whose dependencies are not installed
        'pyparsing.diagram',                    # needs railroad
        'prompt_toolkit.contrib.ssh',           # needs asyncssh
        'scipy._lib.array_api_compat.torch',    # needs torch
        # OpenGL Tk/Togl integration — not available in headless environments
        'OpenGL.Tk',
        # distutils sub-modules that do not exist in Python 3.11 but are
        # referenced by pip's metadata, causing spurious ERROR log lines
        'distutils._collections',
        'distutils._macos_compat',
        'distutils.command.bdist_msi',
        'distutils.command.bdist_wininst',
        'distutils.command.py37compat',
        'distutils.py35compat',
        'distutils.py38compat',
        # VTK optional modules that do not exist in the installed VTK version
        'vtkmodules.util.data_model',
        'vtkmodules.util.execution_model',
        'vtkmodules.vtkRenderingVRModels',
        # pycparser generates these at runtime; they are not bundled
        'pycparser.lextab',
        'pycparser.yacctab',
        # closing_dialog is not committed to the repo yet; suppress analysis error
        'harness_designer.ui.dialogs.closing_dialog',
    ):
        args.extend([f'--exclude-module={mod}'])

    info_plist = None
    if sys.platform.startswith('win'):
        args.extend(['--icon=../../harness_designer/image/icon_256x256.png'])
        args.extend(['--name=HD'])
        for mod in (
            '_curses',
            'curses',
            'OpenGL.raw.GLES3',                     # GLES not available on Windows
        ):
            args.extend([f'--exclude-module={mod}'])
    elif sys.platform.startswith('darwin'):
        arch = platform.machine()   # x86_64 or arm64
        args.extend([f'--target-arch={arch}'])
        args.extend(['--icon=../../harness_designer/image/icon_256x256.png'])
        args.extend(['--name=HD'])
        args.extend(['--osx-bundle-identifier=com.kevinschlosser.harnessdesigner'])
        _candidate = os.path.join(
            os.path.dirname(base_path), 'installer_scripts', 'macos', 'Info.plist'
        )
        if os.path.exists(_candidate):
            info_plist = _candidate

        # OpenGL_accelerate is unreliable on Apple Silicon.
        if arch == 'arm64':
            args.extend(['--exclude-module=OpenGL_accelerate'])
    else:
        # Linux: no platform-specific icon flag; name binary HD so it doesn't
        # collide with the harness_designer/ Python package directory.
        args.extend(['--name=HD'])
        for mod in (
            'OpenGL.osmesa',                        # software renderer, not needed
        ):
            args.extend([f'--exclude-module={mod}'])

    args += [
        '--collect-all=harness_designer',
        # With --name=HD the executable is always HD or HD.exe — no longer
        # collides with the harness_designer/ package dir on any platform.
        '--contents-directory=.',
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
    # symlink already exists.  Clean both the PyInstaller outputs (HD.app / HD)
    # and the post-renamed paths (harness_designer.app / harness_designer) so
    # neither leaves stale symlinks for the next build.
    import shutil
    for candidate in ('harness_designer.app', 'harness_designer', 'HD.app', 'HD'):
        old_dist = os.path.join(scripts_dir, 'dist', candidate)
        if os.path.exists(old_dist):
            shutil.rmtree(old_dist)

    import gc
    gc.collect()

    import PyInstaller.__main__

    # PyInstaller 6.x on macOS can add the Python framework symlink to COLLECT's
    # TOC twice, causing os.symlink() to fail with FileExistsError on the second
    # attempt.  Additionally, PyInstaller sometimes copies the Python binary as a
    # regular file first and then tries to create a symlink at the same path,
    # also causing FileExistsError.  Use lexists (catches both regular files and
    # symlinks, including broken ones) and unlink before recreating.
    _orig_symlink = os.symlink
    if sys.platform.startswith('darwin'):
        def _dedup_symlink(src, dst, *_a, **_kw):
            if os.path.lexists(dst):
                os.unlink(dst)
            _orig_symlink(src, dst, *_a, **_kw)
        os.symlink = _dedup_symlink

    try:
        PyInstaller.__main__.run(args)
    finally:
        os.symlink = _orig_symlink

    # Rename HD.app / HD / HD/ → harness_designer.app / harness_designer so that
    # installer scripts find the expected paths without modification.  The binary
    # inside the onedir is always named HD (or HD.exe on Windows).
    if sys.platform.startswith('darwin'):
        _old = os.path.join(scripts_dir, 'dist', 'HD.app')
        _new = os.path.join(scripts_dir, 'dist', 'harness_designer.app')
    else:
        _old = os.path.join(scripts_dir, 'dist', 'HD')
        _new = os.path.join(scripts_dir, 'dist', 'harness_designer')
    if os.path.exists(_old):
        shutil.move(_old, _new)

    # Strip type stubs, C sources, dist-info, __pycache__, and empty dirs from
    # the PyInstaller output before the installer packages everything up.
    if sys.platform.startswith('darwin'):
        _clean_dist(os.path.join(scripts_dir, 'dist', 'harness_designer.app'))
    else:
        _clean_dist(os.path.join(scripts_dir, 'dist', 'harness_designer'))

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
