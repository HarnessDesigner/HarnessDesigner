# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

import sys
import os
import importlib


def _lib_dir():
    return os.path.dirname(sys.executable)


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


def _fix_permissions(path):
    """See dep_installer.py's _fix_permissions -- same fix, same reason.

    bootstrap.install() mirrors dep_installer's own pip --target install for
    the "app run without going through the installer" fallback case, so it
    needs the same defensive re-inherit-permissions step.
    """
    if sys.platform != 'win32':
        return

    import subprocess

    try:
        subprocess.run(
            ['icacls', path, '/reset', '/T', '/C', '/Q'],
            capture_output=True, check=False,
        )
    except OSError:
        pass


def _run_pyside6_install_ui():
    """Show the PySide6/Qt license Accept/Cancel screen and, on Accept, the
    pip-install progress -- in the same window (same Tk root), not two
    separate dialogs. Returns True once PySide6 is installed, False if the
    user cancelled at the license screen (nothing is installed in that
    case). Shares the license screen with dep_installer.py's Windows/macOS
    --phase install, via license_screen.py.
    """
    import threading
    import tkinter as tk
    from tkinter import ttk

    import license_screen

    root = tk.Tk()
    root.title('PySide6 Installation')
    root.geometry('520x440')
    root.resizable(False, False)
    root.protocol('WM_DELETE_WINDOW', lambda: None)

    accepted = {'value': None}

    def _on_accept():
        accepted['value'] = True
        root.quit()

    def _on_cancel():
        accepted['value'] = False
        root.quit()

    license_screen.build_license_screen(
        root,
        license_screen.resolve_licenses_dir('harness_designer/licenses'),
        _on_accept,
        _on_cancel,
    )
    root.mainloop()

    if not accepted['value']:
        root.destroy()
        return False

    # Same window, same root -- swap the license frame for a progress
    # screen and run the actual pip install in a background thread so the
    # window stays responsive.
    for child in root.winfo_children():
        child.destroy()

    root.geometry('440x160')

    frame = tk.Frame(root, padx=20, pady=16)
    frame.pack(fill='both', expand=True)
    tk.Label(
        frame, text='Installing PySide6, please wait…',
        font=('Segoe UI', 10), pady=8,
    ).pack()
    bar = ttk.Progressbar(frame, length=380, mode='indeterminate')
    bar.pack(pady=6)
    bar.start(12)

    result = {'ok': None}

    def worker():
        result['ok'] = install('PySide6')
        root.after(0, root.quit)

    threading.Thread(target=worker, daemon=True).start()
    root.mainloop()
    root.destroy()

    return bool(result['ok'])


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

    _fix_permissions(os.path.join(lib, (import_name or package).split('.')[0]))

    importlib.invalidate_caches()
    return exit_code == 0


def run():
    lib = _lib_dir()
    if lib not in sys.path:
        sys.path.insert(0, lib)

    # Mirror the PACKAGES list in installer.py.
    # The Inno Setup/macOS installers normally handle this ahead of time;
    # this catches the case where the app is run without going through
    # them -- always true on Linux, which has no separate install-time step
    # for this any more (see installer_scripts/linux/install.sh and
    # builder/installer.py's build_deb()).
    if _is_importable('PySide6'):
        return

    if not _run_pyside6_install_ui():
        sys.exit(0)
