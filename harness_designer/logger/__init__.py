# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

from . import log_handler as _log_handler


Log = _log_handler.Log
LogHandler = _log_handler.LogHandler
logger: Log = None


del _log_handler
