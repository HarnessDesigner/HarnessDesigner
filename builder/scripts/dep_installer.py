# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

import sys
import os
import threading
import tkinter as tk
from tkinter import ttk


# Required packages — always installed.
# Format: ('pip install name', 'import name', 'friendly label')
#
# GPU vendor SMI bindings are excluded from the PyInstaller bundle (see
# builder/build.py / builder/collect_modules.py) because CI build machines
# have no GPU driver installed for PyInstaller to resolve against, and are
# installed here instead — on the actual target machine — same as PySide6.
# Versions match the platform markers in pyproject.toml.
if sys.platform == 'darwin':
    _GPU_PACKAGES = [
        ('apple_smi==0.1.4', 'apple_smi', 'Apple SMI (GPU/SoC monitoring)'),
    ]
else:
    _GPU_PACKAGES = [
        ('nvidia-ml-py==13.610.43', 'pynvml', 'NVIDIA Management Library (GPU monitoring)'),
        ('amdsmi==7.0.2', 'amdsmi', 'AMD SMI (GPU monitoring)'),
    ]

REQUIRED_PACKAGES = [
    ('PySide6', 'PySide6', 'PySide6 (Qt UI framework)'),
] + _GPU_PACKAGES

# Installed only when the installer is launched with --with-mysql — the
# Inno Setup wizard's "mysqlconnector" task selects this, not a checkbox here.
MYSQL_PACKAGE = ('mysql-connector-python', 'mysql.connector', 'MySQL Connector/Python')


def _python_exe():
    meipass = getattr(sys, '_MEIPASS', None)
    if meipass:
        candidate = os.path.join(meipass, 'python.exe')
        if os.path.exists(candidate):
            return candidate
    return sys.executable


def _install_all(target_dir, packages, on_status, on_progress):
    original_executable = sys.executable
    sys.executable = _python_exe()
    try:
        from pip._internal.cli.main import main as pip_main

        total = len(packages)
        for i, (package, _, label, *_rest) in enumerate(packages):
            on_status(f'({i + 1}/{total})  {label}')
            on_progress(i / total)
            exit_code = pip_main([
                'install',
                '--target', target_dir,
                '--quiet',
                # Without these, pip sees a leftover dist-info/RECORD from any
                # earlier partial or manually-cleaned install in target_dir and
                # silently no-ops ("Target directory ... already exists.
                # Specify --upgrade to force replacement.") while still
                # exiting 0 — so a broken PySide6 install looks like success.
                '--upgrade',
                '--force-reinstall',
                package,
            ])
            if exit_code != 0:
                raise RuntimeError(f'pip failed for {package!r} (exit {exit_code})')

        on_status('All components installed successfully.')
        on_progress(1.0)
    finally:
        sys.executable = original_executable


def _build_progress_screen(root, target_dir, packages):
    """Second screen: progress bar shown while packages install."""
    frame = tk.Frame(root, padx=20, pady=16)
    frame.pack(fill='both', expand=True)

    tk.Label(
        frame,
        text='Installing components, please wait…',
        font=('Segoe UI', 10),
        pady=8,
    ).pack()

    bar = ttk.Progressbar(frame, length=380, mode='determinate', maximum=100)
    bar.pack(pady=6)

    lbl_status = tk.Label(frame, text='', pady=4, fg='#444')
    lbl_status.pack()

    result = {'error': None}

    def on_status(msg):
        root.after(0, lbl_status.config, {'text': msg})

    def on_progress(fraction):
        root.after(0, bar.config, {'value': fraction * 100})
        root.after(0, root.update_idletasks)

    def worker():
        try:
            _install_all(target_dir, packages, on_status, on_progress)
        except Exception as exc:
            result['error'] = exc
        finally:
            root.after(600, root.destroy)

    thread = threading.Thread(target=worker, daemon=True)
    thread.start()
    return thread, result


def main():
    if len(sys.argv) < 2:
        print('Usage: dep_installer.exe <target_lib_dir> [--with-mysql]', file=sys.stderr)
        sys.exit(1)

    target_dir = sys.argv[1]
    with_mysql = '--with-mysql' in sys.argv[2:]
    os.makedirs(target_dir, exist_ok=True)

    packages = REQUIRED_PACKAGES + ([MYSQL_PACKAGE] if with_mysql else [])

    root = tk.Tk()
    root.title('Harness Designer — Setup')
    root.geometry('440x160')
    root.resizable(False, False)
    root.protocol('WM_DELETE_WINDOW', lambda: None)

    thread, result = _build_progress_screen(root, target_dir, packages)

    root.mainloop()
    thread.join()

    if result.get('error') is not None:
        raise result['error']


if __name__ == '__main__':
    main()
