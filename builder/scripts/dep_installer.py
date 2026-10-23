# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

import argparse
import datetime
import os
import shutil
import subprocess
import sys
import threading
import time
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

import license_screen

WINDOW_TITLE = 'PySide6 Installation'

EXIT_OK = 0
EXIT_ERROR = 1
EXIT_CANCELLED = 3   # distinct from argparse's own usage-error exit code (2)


# Required packages — always installed.
# Format: ('pip install name', 'import name', 'friendly label')
#
# apple_smi is excluded from the PyInstaller bundle (see builder/build.py)
# because CI build machines have no GPU driver installed for PyInstaller to
# resolve against, and is installed here instead — on the actual target
# machine — same as PySide6. Version matches the platform marker in
# pyproject.toml. nvapi/pyamd_adl (see harness_designer/gpu/nvidia/backend.py,
# harness_designer/gpu/amd/backend.py) don't have this problem -- they're
# ctypes wrappers that only dlopen the driver on first actual use, not at
# import time -- so they're ordinary bundled pyproject.toml dependencies,
# not installed here.
if sys.platform == 'darwin':
    _GPU_PACKAGES = [
        ('apple_smi==0.1.4', 'apple_smi', 'Apple SMI (GPU/SoC monitoring)'),
    ]
else:
    _GPU_PACKAGES = []

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


def _app_binary_path(app_dir):
    """Path to the main app's own executable inside app_dir, per platform."""
    if sys.platform == 'win32':
        return os.path.join(app_dir, 'HD.exe')
    if sys.platform == 'darwin':
        bundled = os.path.join(app_dir, 'Contents', 'MacOS', 'HD')
        if os.path.exists(bundled):
            return bundled
        return os.path.join(app_dir, 'HD')
    return os.path.join(app_dir, 'HD')


def _is_app_running():
    """Best-effort check for whether the main HD/HD.exe process is running."""
    try:
        if sys.platform == 'win32':
            out = subprocess.run(
                ['tasklist', '/FI', 'IMAGENAME eq HD.exe', '/NH'],
                capture_output=True, text=True, check=False,
            ).stdout
            return 'HD.exe' in out
        out = subprocess.run(
            ['pgrep', '-x', 'HD'], capture_output=True, text=True, check=False,
        )
        return out.returncode == 0
    except OSError:
        return False


def _appdata_dir():
    """Mirror harness_designer/utils/paths.py's get_appdata() without importing
    the harness_designer package (this script stays deliberately standalone).
    """
    home = os.path.expanduser('~')
    if sys.platform == 'win32':
        return os.path.join(home, 'AppData', 'Roaming', 'HarnessDesigner')
    return os.path.join(home, '.HarnessDesigner')


def _backup_user_data(dest_dir):
    """Zip the per-user appdata dir into dest_dir; the original is never touched."""
    import zipfile

    appdata = _appdata_dir()
    if not os.path.isdir(appdata):
        return None

    timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
    zip_path = os.path.join(dest_dir, f'HarnessDesigner_backup_{timestamp}.zip')
    parent = os.path.dirname(appdata)

    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zf:
        for dirpath, _dirs, filenames in os.walk(appdata):
            for fname in filenames:
                fpath = os.path.join(dirpath, fname)
                zf.write(fpath, os.path.relpath(fpath, parent))

    return zip_path


def _remove_old_install(app_dir):
    """Remove a previous installation at app_dir.

    On Windows, prefer the real Inno Setup uninstaller (keeps Add/Remove
    Programs, Start Menu shortcuts, etc. consistent) run with /NODATAPROMPT --
    this never deletes user data, independent of the backup prompt's answer.
    Falls back to a plain directory removal everywhere else (macOS has no
    formal uninstaller, and no user data lives inside the .app bundle anyway).
    """
    uninstaller = os.path.join(app_dir, 'unins000.exe') if sys.platform == 'win32' else None

    if uninstaller and os.path.isfile(uninstaller):
        subprocess.run(
            [uninstaller, '/VERYSILENT', '/SUPPRESSMSGBOXES', '/NODATAPROMPT'],
            check=True,
        )
        # Inno's uninstaller copies itself to a temp location and re-execs so
        # it can delete its own original file, so the subprocess above can
        # return before deletion is actually finished -- poll briefly rather
        # than assuming app_dir is already gone.
        deadline = time.time() + 10
        while os.path.isdir(app_dir) and time.time() < deadline:
            time.sleep(0.5)

    if os.path.isdir(app_dir):
        shutil.rmtree(app_dir, ignore_errors=True)


def _show_message_dialog(root, message, buttons):
    """Show a modal dialog with the given message and named buttons.

    Returns the clicked button's name, or None if the window was closed.
    """
    result = {'choice': None}

    win = tk.Toplevel(root)
    win.title(WINDOW_TITLE)
    win.resizable(False, False)
    win.transient(root)

    tk.Label(win, text=message, padx=24, pady=18, wraplength=380, justify='left').pack()

    btn_frame = tk.Frame(win, pady=12)
    btn_frame.pack()

    def _choose(name):
        result['choice'] = name
        win.destroy()

    for name in buttons:
        tk.Button(btn_frame, text=name, width=12,
                  command=lambda n=name: _choose(n)).pack(side='right', padx=6)

    win.protocol('WM_DELETE_WINDOW', lambda: _choose(None))
    win.update_idletasks()
    win.grab_set()
    root.wait_window(win)
    return result['choice']


def _run_phase_pre(root, app_dir):
    """Running-check, then already-installed-check + optional backup +
    removal. Returns an exit code.

    The PySide6 license screen is deliberately NOT shown here -- it's
    shown later, in the same window as the actual pip install (--phase
    install), not as a separate dialog ahead of it.
    """
    while _is_app_running():
        choice = _show_message_dialog(
            root,
            'Harness Designer is currently running.\n'
            'Please close it before continuing.',
            ['Retry', 'Cancel'],
        )
        if choice != 'Retry':
            return EXIT_CANCELLED

    binary = _app_binary_path(app_dir)
    if os.path.exists(binary):
        choice = _show_message_dialog(
            root,
            'An existing installation of Harness Designer was found.\n'
            'It needs to be removed before continuing.',
            ['Continue', 'Cancel'],
        )
        if choice != 'Continue':
            return EXIT_CANCELLED

        backup_choice = _show_message_dialog(
            root,
            'Back up your database, parts library and projects first?\n\n'
            'This can be large -- make sure the destination you choose has\n'
            'enough free space.',
            ['Yes', 'No'],
        )
        if backup_choice == 'Yes':
            dest = filedialog.askdirectory(parent=root, title='Choose a backup destination')
            if dest:
                try:
                    _backup_user_data(dest)
                except Exception as exc:  # NOQA
                    messagebox.showerror(WINDOW_TITLE, f'Backup failed:\n{exc}', parent=root)

        try:
            _remove_old_install(app_dir)
        except (OSError, subprocess.CalledProcessError) as exc:
            messagebox.showerror(
                WINDOW_TITLE, f'Could not remove the existing installation:\n{exc}', parent=root)
            return EXIT_ERROR

    return EXIT_OK


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
    parser = argparse.ArgumentParser(
        description='Harness Designer dependency installer.')
    parser.add_argument(
        '--phase', choices=['pre', 'install'], default='install',
        help='"pre": running/already-installed checks only (runs before '
             'any new files are copied). '
             '"install" (default): PySide6 license Accept/Cancel, then '
             '(same window) pip-install the required packages.',
    )
    parser.add_argument('target', help='app_dir (--phase pre) or target_lib_dir (--phase install)')
    parser.add_argument('--with-mysql', action='store_true')
    args = parser.parse_args()

    root = tk.Tk()
    root.title(WINDOW_TITLE)
    root.resizable(False, False)
    root.protocol('WM_DELETE_WINDOW', lambda: None)

    if args.phase == 'pre':
        root.geometry('520x440')
        root.withdraw()
        code = _run_phase_pre(root, args.target)
        try:
            root.destroy()
        except tk.TclError:
            pass
        sys.exit(code)

    target_dir = args.target
    packages = REQUIRED_PACKAGES + ([MYSQL_PACKAGE] if args.with_mysql else [])

    # PySide6 license Accept/Cancel, then (same window) the install progress
    # -- one continuous dialog, not two separate ones.
    root.geometry('520x440')

    accepted = {'value': None}

    def _on_accept():
        accepted['value'] = True
        root.quit()

    def _on_cancel():
        accepted['value'] = False
        root.quit()

    license_screen.build_license_screen(
        root, license_screen.resolve_licenses_dir(), _on_accept, _on_cancel)
    root.mainloop()

    if not accepted['value']:
        root.destroy()
        sys.exit(EXIT_CANCELLED)

    for child in root.winfo_children():
        child.destroy()

    os.makedirs(target_dir, exist_ok=True)
    root.geometry('440x160')

    thread, result = _build_progress_screen(root, target_dir, packages)

    root.mainloop()
    thread.join()

    if result.get('error') is not None:
        raise result['error']


if __name__ == '__main__':
    main()
