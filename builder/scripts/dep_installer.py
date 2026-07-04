# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

import argparse
import contextlib
import io
import os
import queue
import sys
import threading
import tkinter as tk
from tkinter import messagebox, ttk


# Required packages — always installed.
# Format: ('pip install name', 'import name', 'friendly label')
REQUIRED_PACKAGES = [
    ('PySide6', 'PySide6', 'PySide6 (Qt UI framework)'),
]

# Optional packages — presented as checkboxes on the component-selection screen.
# Format: ('pip install name', 'import name', 'friendly label', 'description')
OPTIONAL_PACKAGES = [
    (
        'mysql-connector-python',
        'mysql.connector',
        'MySQL Connector/Python',
        'Required for multi-seat installations using a shared MySQL database.',
    ),
]

PYSIDE6_LICENSE_TEXT = """\
PySide6 — Qt for Python
=======================

OVERVIEW
--------
PySide6 is the official Python module from the Qt for Python project,
which provides access to the complete Qt 6.0+ framework. It is
developed and maintained by The Qt Company.

HOW IT IS INSTALLED
-------------------
Harness Designer does NOT bundle or distribute PySide6. This installer
will download PySide6 directly from the Python Package Index (PyPI)
on your behalf. You are the party downloading and installing PySide6.

LICENSE:  GNU Lesser General Public License v3 (LGPL v3)
Copyright (C) The Qt Company Ltd.
Full text: https://www.gnu.org/licenses/lgpl-3.0.html

SUMMARY OF YOUR RIGHTS UNDER LGPL v3
--------------------------------------
  * You may use PySide6 in commercial and open-source applications.
  * You may modify PySide6's source code for your own use.
  * You must retain all copyright and license notices.
  * You must make the LGPL v3 license text available to end users.
  * You must allow end users to update or replace the PySide6 library.

By checking the box below and clicking Next, you acknowledge that you
are downloading and installing PySide6 under the terms of the LGPL v3.
If you do not accept these terms, click Cancel to abort the installation.
"""

_HEADER_BG = '#0D2137'
_HEADER_FG = '#FFFFFF'
_HEADER_SUB = '#7AACCC'


def _python_exe() -> str:
    meipass = getattr(sys, '_MEIPASS', None)
    if meipass:
        candidate = os.path.join(meipass, 'python.exe')
        if os.path.exists(candidate):
            return candidate

    return sys.executable


# ── Shared layout helpers ─────────────────────────────────────────────────────

def _make_header(parent: tk.Widget, title: str, subtitle: str = '') -> None:
    bar = tk.Frame(parent, bg=_HEADER_BG)
    bar.pack(fill='x', side='top')

    label = tk.Label(bar, text=title, font=('Segoe UI', 12, 'bold'),
                     bg=_HEADER_BG, fg=_HEADER_FG, anchor='w')

    label.pack(fill='x', padx=18, pady=(14, 0 if subtitle else 14))

    if subtitle:
        sub_label = tk.Label(bar, text=subtitle, font=('Segoe UI', 9),
                             bg=_HEADER_BG, fg=_HEADER_SUB, anchor='w')

        sub_label.pack(fill='x', padx=18, pady=(0, 14))

    ttk.Separator(parent, orient='horizontal').pack(fill='x', side='top')


def _make_button_bar(parent: tk.Widget, *buttons) -> dict:
    """
    Build the bottom button row.  Each entry: (label, command, side).
    Returns a dict mapping label → Button widget.
    """

    ttk.Separator(parent, orient='horizontal').pack(fill='x', side='bottom')
    bar = tk.Frame(parent, pady=8)
    bar.pack(fill='x', side='bottom')
    refs = {}
    for label, cmd, side in buttons:
        b = ttk.Button(bar, text=label, command=cmd, width=10)
        b.pack(side=side, padx=6)
        refs[label] = b

    return refs


# ── Installer application ─────────────────────────────────────────────────────

class InstallerApp:
    """
    Three-screen mini-installer: License → Components → Install log.
    """

    def __init__(self, target_dir: str) -> None:
        self.target_dir = target_dir
        self._queue: queue.Queue = queue.Queue()
        self._allow_close = True

        self.root = tk.Tk()
        self.root.title('Harness Designer — Component Setup')
        self.root.geometry('600x460')
        self.root.resizable(False, False)
        self.root.protocol('WM_DELETE_WINDOW', self._on_close_request)

        # Enforce a consistent look on Windows
        style = ttk.Style(self.root)
        try:
            style.theme_use('vista')
        except tk.TclError:
            pass

        self._frame: tk.Frame | None = None
        self._show_license()

    # ── Window lifecycle ──────────────────────────────────────────────────────

    def run(self) -> None:
        self.root.mainloop()

    def _on_close_request(self) -> None:
        if self._allow_close:
            self.root.destroy()

    def _switch(self) -> tk.Frame:
        """
        Destroy the current content frame and return a fresh one.
        """

        if self._frame is not None:
            self._frame.destroy()

        self._frame = tk.Frame(self.root)
        self._frame.pack(fill='both', expand=True)

        return self._frame

    # ── Screen 1: PySide6 license ─────────────────────────────────────────────

    def _show_license(self) -> None:
        self._allow_close = True
        f = self._switch()

        _make_header(f, 'License Agreement',
                     'Please review the PySide6 license before continuing.')

        body = tk.Frame(f, padx=16, pady=8)
        body.pack(fill='both', expand=True)

        # Scrollable licence text
        txt_outer = tk.Frame(body, relief='solid', bd=1)
        txt_outer.pack(fill='both', expand=True)

        txt = tk.Text(txt_outer, wrap='word', font=('Courier New', 8),
                      relief='flat', bg='#F8F8F8', fg='#222')

        sb = ttk.Scrollbar(txt_outer, command=txt.yview)
        txt.configure(yscrollcommand=sb.set)
        sb.pack(side='right', fill='y')
        txt.pack(fill='both', expand=True, padx=2, pady=2)
        txt.insert('1.0', PYSIDE6_LICENSE_TEXT)
        txt.config(state='disabled')

        # Accept checkbox
        self._accept_var = tk.BooleanVar(value=False)

        check_button = ttk.Checkbutton(
            body, variable=self._accept_var,
            text='I accept the terms of the PySide6 LGPL v3 license')

        check_button.pack(anchor='w', pady=(8, 0))

        _make_button_bar(f, ('Cancel', self.root.destroy, 'right'),
                         ('Next >', self._license_next, 'right'))

    def _license_next(self) -> None:
        if not self._accept_var.get():
            messagebox.showerror(
                'License Required',
                'You must accept the PySide6 LGPL v3 license to continue.',
                parent=self.root)

            return

        self._show_packages()

    # ── Screen 2: optional component selection ────────────────────────────────

    def _show_packages(self) -> None:
        self._allow_close = True
        f = self._switch()

        _make_header(
            f, 'Select Components',
            'Choose optional components to install alongside Harness Designer.')

        body = tk.Frame(f, padx=16, pady=12)
        body.pack(fill='both', expand=True)

        label = tk.Label(
            body, font=('Segoe UI', 9), justify='left',
            text='Required components (PySide6) will always be installed.\n'
                 'Select any optional components you need:')

        label.pack(anchor='w', pady=(0, 14))

        self._pkg_vars: list[tuple[tk.BooleanVar, str]] = []

        for pip_name, _, label, description in OPTIONAL_PACKAGES:
            var = tk.BooleanVar(value=False)
            self._pkg_vars.append((var, pip_name))

            row = tk.Frame(body)
            row.pack(anchor='w', pady=4, fill='x')

            ttk.Checkbutton(row, text=label, variable=var).pack(anchor='w')

            label = tk.Label(row, text=f'    {description}',
                             font=('Segoe UI', 8), fg='#666', justify='left')

            label.pack(anchor='w')

        _make_button_bar(f, ('Cancel',  self.root.destroy,    'right'),
                         ('Install', self._begin_install,   'right'),
                         ('< Back',  self._show_license,    'right'))

    def _begin_install(self) -> None:
        packages = list(REQUIRED_PACKAGES)
        for var, pip_name in self._pkg_vars:
            if var.get():
                packages += [p for p in OPTIONAL_PACKAGES if p[0] == pip_name]

        self._packages = packages
        self._show_install()

    # ── Screen 3: installation progress / terminal log ─────────────────────────

    def _show_install(self) -> None:
        self._allow_close = False
        f = self._switch()

        _make_header(f, 'Installing Components',
                     'Downloading and installing required runtime components...')

        body = tk.Frame(f, padx=16, pady=6)
        body.pack(fill='both', expand=True)

        # Status label + progress bar
        self._status_var = tk.StringVar(value='Initialising...')

        tk.Label(body, textvariable=self._status_var, font=('Segoe UI', 9),
                 anchor='w').pack(fill='x')

        self._progress = ttk.Progressbar(body, maximum=100)
        self._progress.pack(fill='x', pady=(4, 8))

        # Terminal log widget
        term_outer = tk.Frame(body, relief='flat', bd=1, bg='#0C0C0C')
        term_outer.pack(fill='both', expand=True)

        self._terminal = tk.Text(term_outer, bg='#0C0C0C', fg='#00CC00',
                                 font=('Courier New', 9), relief='flat', bd=0,
                                 insertbackground='#00CC00', wrap='char')

        t_sb = ttk.Scrollbar(term_outer, command=self._terminal.yview)
        self._terminal.configure(yscrollcommand=t_sb.set)
        t_sb.pack(side='right', fill='y')
        self._terminal.pack(fill='both', expand=True, padx=2, pady=2)
        self._terminal.config(state='disabled')

        btns = _make_button_bar(f, ('Close', self.root.destroy, 'right'))
        self._close_btn = btns['Close']
        self._close_btn.config(state='disabled')

        # Kick off background install thread
        threading.Thread(target=self._install_worker, args=(self._packages,),
                         daemon=True).start()

        self.root.after(50, self._drain_queue)

    def _term_write(self, text: str) -> None:
        self._terminal.config(state='normal')
        self._terminal.insert('end', text)
        self._terminal.see('end')
        self._terminal.config(state='disabled')

    def _drain_queue(self) -> None:
        """Poll the inter-thread queue and update the UI."""
        try:
            while True:
                msg = self._queue.get_nowait()
                if isinstance(msg, str):
                    self._term_write(msg)
                elif isinstance(msg, dict):
                    if 'status' in msg:
                        self._status_var.set(msg['status'])

                    if 'progress' in msg:
                        self._progress.config(value=msg['progress'] * 100)

                    if 'done' in msg:
                        self._allow_close = True
                        self._close_btn.config(state='normal')
                        if msg.get('error'):
                            self._status_var.set(
                                'Installation failed — see log above.')
                            self._term_write(
                                '\nInstallation failed.\n'
                                'You may close this window and re-run setup, '
                                'or install PySide6 manually:\n'
                                '  pip install PySide6\n')
                        else:
                            self._status_var.set('Installation complete.')
                            self._progress.config(value=100)
                        return   # stop polling
        except queue.Empty:
            pass

        self.root.after(50, self._drain_queue)

    def _install_worker(self, packages: list) -> None:
        """Background thread: runs pip and feeds output to the terminal queue."""
        q = self._queue

        class _Writer:
            """
            Redirect sys.stdout / sys.stderr into the terminal queue.
            """

            def write(self, s: str) -> None:  # NOQA
                if s:
                    q.put(s)

            def flush(self) -> None:
                pass

            def isatty(self) -> bool:  # NOQA
                # Prevents pip from emitting ANSI escape codes
                return False

        writer = _Writer()
        original_exe = sys.executable
        sys.executable = _python_exe()

        try:
            from pip._internal.cli.main import main as pip_main  # NOQA

            total = len(packages)
            for i, (pkg, _, label, *_rest) in enumerate(packages):
                q.put({'status': f'Installing {label}...', 'progress': i / total})
                q.put(f'\n[{i + 1}/{total}] Installing {label}...\n')

                exit_code = 0
                try:
                    with (
                        contextlib.redirect_stdout(writer),
                        contextlib.redirect_stderr(writer)
                    ):
                        pip_main(['install', '--target', self.target_dir, pkg])

                except SystemExit as exc:
                    exit_code = int(exc.code) if exc.code is not None else 0

                if exit_code not in (0, None):
                    q.put(f'\nERROR: pip failed for {pkg!r} '
                          f'(exit code {exit_code})\n')

                    q.put({'done': True, 'error': True})

                    return

            q.put('\nAll components installed successfully.\n')
            q.put({'done': True, 'error': False, 'progress': 1.0})

        except Exception as exc:
            q.put(f'\nFATAL ERROR: {exc}\n')
            q.put({'done': True, 'error': True})
        finally:
            sys.executable = original_exe


# ── Headless mode (called by automation / CI, not by InnoSetup) ───────────────

def _run_headless(target_dir: str, log_file: str, mysql: bool = False) -> None:
    packages = list(REQUIRED_PACKAGES)
    if mysql:
        packages += [p for p in OPTIONAL_PACKAGES if p[0] == 'mysql-connector-python']

    def log(msg: str) -> None:
        with open(log_file, 'a', encoding='utf-8') as file:
            file.write(msg + '\n')
            file.flush()

    original_exe = sys.executable
    sys.executable = _python_exe()
    try:
        from pip._internal.cli.main import main as pip_main  # NOQA

        total = len(packages)
        for i, (pkg, _, label, *_rest) in enumerate(packages):
            log(f'[{i + 1}/{total}] Installing {label}...')
            buf = io.StringIO()
            exit_code = 0
            try:
                with (
                    contextlib.redirect_stdout(buf),
                    contextlib.redirect_stderr(buf)
                ):
                    pip_main(['install', '--target', target_dir, pkg])
            except SystemExit as exc:
                exit_code = int(exc.code) if exc.code is not None else 0

            for line in buf.getvalue().splitlines():
                if line.strip():
                    log(f'    {line}')

            if exit_code not in (0, None):
                log(f'ERROR: pip failed for {pkg!r} (exit {exit_code})')
                sys.exit(1)

        log('All components installed successfully.')

    except Exception as exc:
        log(f'ERROR: {exc}')
        sys.exit(1)
    finally:
        sys.executable = original_exe
        with open(log_file, 'a', encoding='utf-8') as _f:
            _f.write('__DONE__\n')
            _f.flush()


# ── Entry point ───────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(prog='installer')
    parser.add_argument('target_dir', help='Directory to install packages into')
    parser.add_argument('--headless', action='store_true',
                        help='Run without UI (CI / scripted use)')
    parser.add_argument('--log', metavar='FILE',
                        help='Log file path for headless mode')
    parser.add_argument('--mysql', action='store_true',
                        help='Also install MySQL Connector/Python')
    args = parser.parse_args()

    os.makedirs(args.target_dir, exist_ok=True)

    if args.headless:
        log_path = args.log or os.path.join(args.target_dir, 'install.log')
        _run_headless(args.target_dir, log_path, mysql=args.mysql)
        return

    app = InstallerApp(args.target_dir)
    app.run()


if __name__ == '__main__':
    main()
