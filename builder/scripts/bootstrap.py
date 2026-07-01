# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

import sys
import os
import importlib


def _lib_dir():
    return os.path.join(os.path.dirname(sys.executable), '_internal')


def _python_exe():
    # PyInstaller extracts bundled binaries to sys._MEIPASS at runtime.
    # python.exe is added to the bundle explicitly in build.py so that
    # pip's internal subprocess calls (used during wheel installs) use a
    # real interpreter rather than the frozen bootstrap exe.
    meipass = getattr(sys, '_MEIPASS', None)
    if meipass:
        candidate = os.path.join(meipass, 'python.exe')
        if os.path.exists(candidate):
            return candidate
    return sys.executable


def _is_importable(name):
    try:
        importlib.import_module(name)
        return True
    except ImportError:
        return False


def install(package, import_name=None):
    lib = _lib_dir()

    if lib not in sys.path:
        sys.path.insert(0, lib)

    if _is_importable(import_name or package):
        return True

    os.makedirs(lib, exist_ok=True)

    original_executable = sys.executable
    sys.executable = _python_exe()
    try:
        from pip._internal.cli.main import main as pip_main
        exit_code = pip_main([
            'install',
            '--target', lib,
            '--quiet',
            package,
        ])
    finally:
        sys.executable = original_executable

    importlib.invalidate_caches()
    return exit_code == 0


def run():
    lib = _lib_dir()
    if lib not in sys.path:
        sys.path.insert(0, lib)

    # Mirror the PACKAGES list in installer.py.
    # The Inno Setup installer normally handles these, but this catches
    # the case where the app is run without going through the installer.
    install('PySide6')
