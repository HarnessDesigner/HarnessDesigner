# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

"""Loads modules from ``harness_designer`` under a stub package name so tests
can import them without running ``harness_designer/__init__.py``.

That ``__init__`` opens the live ``Config`` database and starts the log
handler (see MEMORY.md, "Config is a live DB"); a test must never do either.
The stub is a bare module whose ``__path__`` points at the real package
directory, so relative imports inside the real modules (``from .. import
check_types``) resolve exactly as they do in the app.

``ui``, ``ui.widgets`` and ``utils`` are stubbed the same way: their real
``__init__`` files import the main window, every widget, and the numeric
helpers. A test
that needs a widget from them imports that module by name.
"""

import importlib
import pathlib
import sys
import types

_PACKAGE_DIR = pathlib.Path(__file__).resolve().parent.parent / 'harness_designer'
STUB_NAME = 'hd_under_test'

# Packages whose own __init__ is too heavy to run in a test.
_STUBBED = ('', 'ui', 'ui.widgets', 'ui.dialogs', 'utils')


def _install_stubs() -> None:
    for dotted in _STUBBED:
        name = STUB_NAME
        directory = _PACKAGE_DIR
        if dotted:
            name = f'{STUB_NAME}.{dotted}'
            directory = _PACKAGE_DIR.joinpath(*dotted.split('.'))

        if name in sys.modules:
            continue

        stub = types.ModuleType(name)
        stub.__path__ = [str(directory)]
        sys.modules[name] = stub


def load(module: str) -> types.ModuleType:
    """Import ``harness_designer.<module>`` (for example ``scraping.snippets``)."""
    _install_stubs()
    return importlib.import_module(f'{STUB_NAME}.{module}')


def make_app():
    """The one ``QApplication`` for the test process, headless.

    QtWebEngine needs ``AA_ShareOpenGLContexts`` set before any
    ``QApplication`` exists (the real app sets it at import time too), so
    every test module gets its application from here.
    """
    import os

    os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
    os.environ.setdefault('QTWEBENGINE_CHROMIUM_FLAGS', '--disable-gpu --no-sandbox')

    from PySide6 import QtCore, QtWidgets

    app = QtWidgets.QApplication.instance()
    if app is None:
        QtCore.QCoreApplication.setAttribute(QtCore.Qt.ApplicationAttribute.AA_ShareOpenGLContexts)
        app = QtWidgets.QApplication([])

    return app
