from . import log_handler as _log_handler

Log = _log_handler.Log
LogHandler = _log_handler.LogHandler

logger: Log = None

del _log_handler
