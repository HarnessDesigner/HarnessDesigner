# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

from typing import TYPE_CHECKING


if TYPE_CHECKING:
    from . import splash as _splash
    from . import logger as _logger
    from . import ui as _ui


splash: "_splash.Splash" = None
_mainframe: "_ui.MainFrame" = None
_app = None


def __main__(args=None):
    from . import monkey_patch  # no-op stub; import kept for compatibility  # NOQA
    import sys

    from . import app

    import multiprocessing

    if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
        multiprocessing.freeze_support()

    if args is None:
        args = sys.argv[1:]

    global _app

    _app = app.App(args)
    _app.MainLoop()
