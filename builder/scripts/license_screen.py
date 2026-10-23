# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>
#
# Shared PySide6/Qt third-party license Accept/Cancel screen -- used by both
# dep_installer.py (Windows/macOS, run during package installation) and
# bootstrap.py (Linux, run from inside the main app on first launch, since
# Linux has no separate installer process any more).

import os
import sys
import tkinter as tk


_LICENSE_FILENAMES = ('LGPLv3.txt', 'GPLv3.txt', 'Qt-Commercial-Reference.txt')


def resolve_licenses_dir(bundled_subdir=''):
    """Locate this tool's bundled copy of harness_designer/licenses/.

    :param bundled_subdir: path under ``sys._MEIPASS`` to the licenses dir
        when frozen -- `''` for a tool that bundles the `.txt` files
        directly at the MEIPASS root (dep_installer's own `--add-data`), or
        `'harness_designer/licenses'` for a tool built from the full
        harness_designer package (`--collect-all`, e.g. the main app's own
        bootstrap.py).
    """
    meipass = getattr(sys, '_MEIPASS', None)
    if meipass:
        return os.path.join(meipass, bundled_subdir) if bundled_subdir else meipass
    # Unfrozen/dev fallback: this file lives at builder/scripts/license_screen.py
    return os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(
        os.path.abspath(__file__)))), 'harness_designer', 'licenses')


def _read_license_file(licenses_dir, filename):
    try:
        with open(os.path.join(licenses_dir, filename), 'r', encoding='utf-8') as f:
            return f.read()
    except OSError:
        return f'[{filename} not found]'


def license_text(licenses_dir):
    """Combined PySide6/Qt LGPLv3 notice + the LGPLv3/GPLv3/commercial-reference text.

    Mirrors harness_designer/ui/dialogs/about_dialog.py's _qt_license_text(),
    kept independent here since this module must not import the
    harness_designer package.
    """
    sep = '\n\n' + ('=' * 78) + '\n\n'
    notice = (
        'This application uses PySide6, the official Python bindings for the\n'
        'Qt framework, provided by The Qt Company. PySide6 is used here under\n'
        'the GNU Lesser General Public License, Version 3 (LGPLv3), dynamically\n'
        'linked as a separate, independently replaceable component -- it is not\n'
        'compiled into this application\'s own code.\n\n'
        'Copyright (C) The Qt Company Ltd. and contributors.\n\n'
        'The full text of the LGPLv3 and the GPLv3 (which the LGPLv3 '
        'incorporates by\nreference) follows, along with the commercial-license '
        'referral notice\nshipped in PySide6\'s own package metadata.\n'
    )
    return (
        notice
        + sep + _read_license_file(licenses_dir, 'LGPLv3.txt')
        + sep + _read_license_file(licenses_dir, 'GPLv3.txt')
        + sep + 'PySide6\'s own bundled notice:\n\n'
        + _read_license_file(licenses_dir, 'Qt-Commercial-Reference.txt')
    )


def build_license_screen(root, licenses_dir, on_accept, on_cancel):
    """Build the PySide6/Qt license Accept/Cancel screen as a frame inside `root`."""
    frame = tk.Frame(root, padx=16, pady=12)
    frame.pack(fill='both', expand=True)

    tk.Label(
        frame,
        text='This application depends on PySide6/Qt, licensed separately under\n'
             'the terms below. Please review before continuing.',
        font=('Segoe UI', 10), justify='left', anchor='w',
    ).pack(fill='x', pady=(0, 8))

    text_frame = tk.Frame(frame)
    text_frame.pack(fill='both', expand=True)

    scrollbar = tk.Scrollbar(text_frame)
    scrollbar.pack(side='right', fill='y')

    text_widget = tk.Text(
        text_frame, wrap='word', yscrollcommand=scrollbar.set, font=('Consolas', 8),
    )
    text_widget.insert('1.0', license_text(licenses_dir))
    text_widget.config(state='disabled')
    text_widget.pack(side='left', fill='both', expand=True)
    scrollbar.config(command=text_widget.yview)

    button_frame = tk.Frame(frame, pady=10)
    button_frame.pack(fill='x')

    tk.Button(button_frame, text='Cancel', width=12, command=on_cancel).pack(
        side='right', padx=(6, 0))
    tk.Button(button_frame, text='Accept', width=12, command=on_accept).pack(
        side='right')

    return frame
