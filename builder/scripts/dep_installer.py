# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

import sys
import os
import threading
import tkinter as tk
from tkinter import ttk


# Required packages — always installed.
# Format: ('pip install name', 'import name', 'friendly label')
REQUIRED_PACKAGES = [
    ('PySide6', 'PySide6', 'PySide6 (Qt UI framework)'),
]

# Optional packages — presented as checkboxes before installation begins.
# Format: ('pip install name', 'import name', 'friendly label', 'description')
OPTIONAL_PACKAGES = [
    (
        'mysql-connector-python',
        'mysql.connector',
        'MySQL Connector/Python',
        'Required for multi-seat installations using a shared MySQL database.',
    ),
]


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


def _build_options_screen(root, on_confirm):
    """First screen: optional package checkboxes + Install button."""
    frame = tk.Frame(root, padx=20, pady=16)
    frame.pack(fill='both', expand=True)

    tk.Label(
        frame,
        text='Harness Designer — Component Selection',
        font=('Segoe UI', 11, 'bold'),
    ).pack(anchor='w', pady=(0, 4))

    tk.Label(
        frame,
        text='Required components will always be installed.\n'
             'Select any optional components you need:',
        justify='left',
        fg='#444',
    ).pack(anchor='w', pady=(0, 10))

    check_vars = []
    for pip_name, import_name, label, description in OPTIONAL_PACKAGES:
        var = tk.BooleanVar(value=False)
        check_vars.append((var, pip_name, import_name, label, description))

        cb_frame = tk.Frame(frame)
        cb_frame.pack(anchor='w', pady=2)

        tk.Checkbutton(cb_frame, text=label, variable=var, font=('Segoe UI', 9, 'bold')).pack(anchor='w')
        tk.Label(cb_frame, text=f'    {description}', fg='#666', justify='left').pack(anchor='w')

    btn_frame = tk.Frame(frame)
    btn_frame.pack(anchor='e', pady=(14, 0))

    def on_install():
        selected_optional = [
            (pip_name, import_name, label, description)
            for var, pip_name, import_name, label, description in check_vars
            if var.get()
        ]
        frame.destroy()
        on_confirm(REQUIRED_PACKAGES + selected_optional)

    tk.Button(btn_frame, text='Install', width=12, command=on_install).pack()


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
        print('Usage: installer.exe <target_lib_dir>', file=sys.stderr)
        sys.exit(1)

    target_dir = sys.argv[1]
    os.makedirs(target_dir, exist_ok=True)

    root = tk.Tk()
    root.title('Harness Designer — Setup')
    root.geometry('480x260')
    root.resizable(False, False)
    root.protocol('WM_DELETE_WINDOW', lambda: None)

    thread = None
    result = {}

    def start_install(packages):
        nonlocal thread, result
        root.geometry('440x160')
        thread, result = _build_progress_screen(root, target_dir, packages)

    _build_options_screen(root, on_confirm=start_install)

    root.mainloop()

    if thread is not None:
        thread.join()

    if result.get('error') is not None:
        raise result['error']


if __name__ == '__main__':
    main()
