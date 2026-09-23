# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

"""Top-level package state and entry point for :mod:`harness_designer`."""

from typing import TYPE_CHECKING, Union as _Union

import multiprocessing
import sys

from . import check_types as _check_types
# we are going to set up the logging before anything else gets done.
from . import logger as _logger


if TYPE_CHECKING:
    from . import splash as _splash
    from . import ui as _ui


splash: _Union["_splash.Splash", None] = None
_mainframe: _Union["_ui.MainFrame", None] = None
_app = None


@_check_types.do
def __main__(args=None):
    """Start the application and enter the main event loop.

    :param args: Optional command-line arguments excluding the executable name.
    :type args: list[str] | None
    """
    from . import app

    if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
        multiprocessing.freeze_support()

    if args is None:
        args = sys.argv[1:]

    global _app

    _app = app.App(args)
    _app.MainLoop()
