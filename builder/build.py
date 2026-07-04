# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

def build_dependency_installer():
    """Build dep_installer.exe — the lightweight GUI that installs external packages."""
    import sys
    import os

    base_path = os.path.abspath(os.path.dirname(__file__))

    ico = os.path.join(
        base_path, '..', 'installer_scripts', 'windows', 'assets',
        'harness_designer.ico',
    )

    args = [
        f'--add-binary={sys.executable}{os.pathsep}.',
        '--collect-all=pip',
        # distlib.resources.finder() resolves finders by loader type; PyInstaller's
        # FrozenImporter is not registered, causing DistlibException at pip import
        # time.  This hook patches finder() before installer.py runs.
        '--runtime-hook=rthook_pip_distlib.py',
        '--name=dep_installer',
        '--onefile',
        '--noconfirm',
        '--clean',
        '--windowed',
    ]

    if os.path.exists(ico):
        args.append(f'--icon={os.path.normpath(ico)}')

    args.append('dep_installer.py')

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
      - .py   — Python source files (bytecode is in PyInstaller's archive)
      - .pyi / .pyx / .c / .cpp / .h — stubs and other source files
      - *.dist-info/  — package metadata; license files are extracted first
      - __pycache__/  — bytecode cache dirs
      - _tcl_data / _tk_data — Tcl/Tk runtime data (not needed with PySide6)
      - empty directories left over after the above removals

    Collects all license files from *.dist-info into a single 'licenses/'
    directory at the root of app_dir so they can be displayed in the app.
    """
    import os
    import shutil

    # .py — redundant: PyInstaller already compiled everything it analyzed into
    # its internal archive as bytecode; the .py copies left on disk are from
    # --collect-all data collection and are never imported by the frozen app.
    _REMOVE_EXTS = frozenset(['.py', '.pyi', '.pyx', '.c', '.cpp', '.h'])
    # _tcl_data / _tk_data must be kept — PyInstaller's pyi_rth__tkinter runtime
    # hook checks for _tcl_data at startup and crashes with FileNotFoundError
    # if it is absent, even when the app itself does not call tkinter directly.
    _REMOVE_DATADIRS = frozenset()
    # PyOpenGL ships freeglut/gle DLLs for vc9 (VS2008) and vc10 (VS2010) that
    # require MSVCR90.dll / MSVCR100.dll — old runtimes absent on modern Windows.
    # The vc15 (VS2017+) variants use the universal CRT and are sufficient.
    import sys as _sys
    _remove_dll_suffixes = ('.vc9.dll', '.vc10.dll') if _sys.platform.startswith('win') else ()
    # File names (lower-cased) treated as license files worth keeping
    _LICENSE_NAMES = frozenset([
        'license', 'license.txt', 'license.md', 'license.rst',
        'licence', 'licence.txt',
        'copying', 'copying.txt', 'copying.rst',
        'notice', 'notice.txt',
        'license.apache', 'license.bsd', 'license.external', 'license.lgpl',
        'authors', 'authors.txt', 'authors.rst',
    ])

    n_files = 0
    n_dirs = 0

    licenses_dir = os.path.join(app_dir, 'licenses')
    os.makedirs(licenses_dir, exist_ok=True)

    for root, dirs, files in os.walk(app_dir, topdown=False):
        # Remove unwanted individual files
        for fname in files:
            flower = fname.lower()
            if os.path.splitext(fname)[1] in _REMOVE_EXTS or any(
                flower.endswith(s) for s in _remove_dll_suffixes
            ):
                try:
                    os.remove(os.path.join(root, fname))
                    n_files += 1
                except OSError:
                    pass

        # Remove unwanted directories (walking bottom-up so children go first)
        for dname in dirs:
            dir_path = os.path.join(root, dname)
            if dname in _REMOVE_DATADIRS or dname == '__pycache__':
                try:
                    shutil.rmtree(dir_path, ignore_errors=True)
                    n_dirs += 1
                except OSError:
                    pass
            elif dname.endswith('.dist-info'):
                # Extract every license-like file before nuking the dir
                pkg_name = dname.replace('.dist-info', '')
                for lic_root, _, lic_files in os.walk(dir_path):
                    for lic_fname in lic_files:
                        if lic_fname.lower() in _LICENSE_NAMES:
                            src = os.path.join(lic_root, lic_fname)
                            # Unique dest: pkgname + relative path joined with _
                            rel = os.path.relpath(src, dir_path)
                            rel_flat = rel.replace(os.sep, '_')
                            dest = os.path.join(licenses_dir, f'{pkg_name}_{rel_flat}')
                            try:
                                shutil.copy2(src, dest)
                            except OSError:
                                pass
                try:
                    shutil.rmtree(dir_path, ignore_errors=True)
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

    lic_count = len(os.listdir(licenses_dir)) if os.path.isdir(licenses_dir) else 0
    print(f'_clean_dist: removed {n_files} files, {n_dirs} dirs; '
          f'collected {lic_count} license files -> {licenses_dir}')


def build_installer(base_import):
    import sys
    import os
    import platform
    import warnings

    # Setuptools/pkg_resources emit EasyInstallDeprecationWarning and
    # SetuptoolsDeprecationWarning whenever those modules are imported.
    # PyInstaller's analysis phase imports them to trace dependencies, so
    # these warnings flood the build log.  Filter them before PyInstaller runs.
    # In-process filter (covers the analysis phase which runs in this process):
    warnings.filterwarnings('ignore', category=DeprecationWarning, module='setuptools')
    warnings.filterwarnings('ignore', category=DeprecationWarning, module='pkg_resources')
    # Subprocess filter (covers any workers PyInstaller forks for collection):
    _pw = os.environ.get('PYTHONWARNINGS', '')
    _suppress = 'ignore::DeprecationWarning:setuptools,ignore::DeprecationWarning:pkg_resources'
    os.environ['PYTHONWARNINGS'] = f'{_pw},{_suppress}' if _pw else _suppress

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
        'scipy._lib.array_api_compat.torch',    # needs torch
        # scipy 1.17.1 removed _cdflib but its PyInstaller hook still declares it
        'scipy.special._cdflib',
        # OpenGL Tk/Togl integration — not available in headless environments
        'OpenGL.Tk',
        # GLES3 is a mobile/embedded-only API — unavailable on all desktop platforms
        'OpenGL.raw.GLES3',
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
        # ipykernel is the Jupyter kernel — not needed at runtime
        'ipykernel',
        'matplotlib_inline',    # IPython/Jupyter display hook
        # Cython compiler itself — already ran at build time, not needed at runtime
        'Cython',
        'prompt_toolkit.contrib.ssh',           # needs asyncssh which is not installed
    ):
        args.extend([f'--exclude-module={mod}'])

    info_plist = None
    if sys.platform.startswith('win'):
        args.extend(['--icon=../../harness_designer/image/icon_256x256.png'])
        args.extend(['--name=HD'])
        for mod in (
            '_curses',
            'curses',
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
        # These three packages use lazy/dynamic imports that PyInstaller's
        # static analysis cannot fully trace:
        #   IPython      — __getattr__-based lazy loading in __init__.py; 100+
        #                  submodules only resolved at attribute access time.
        #   prompt_toolkit — registry-based lazy imports; submodules like
        #                  auto_suggest/filters/keys are never explicitly imported.
        #   pygments     — entry-points / plugin-registry for lexers, formatters,
        #                  and styles; none are explicit imports in the package.
        '--collect-all=IPython',
        '--collect-all=prompt_toolkit',
        '--collect-all=pygments',
        # With --name=HD the executable is always HD or HD.exe — no longer
        # collides with the harness_designer/ package dir on any platform.
        '--contents-directory=.',
        # Strip assert statements from archived bytecode (level 1 keeps
        # docstrings; level 2 also removes them which can break packages
        # that use __doc__ at runtime).
        '--optimize=1',
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
