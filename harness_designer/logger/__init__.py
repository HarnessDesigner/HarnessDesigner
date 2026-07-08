# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

"""Public logger exports for :mod:`harness_designer.logger`.

Everywhere else in the app does ``from . import logger`` (or ``from ...
import logger``) and then calls ``logger.info(...)``, ``logger.error(...)``,
etc. as if this module were the logger itself. That's implemented here by
constructing the one-and-only :class:`~.log_handler.Log` instance and
binding its methods directly as module-level names - a plain, traceable
alternative to proxying every attribute access through a dynamic lookup.
"""

from . import log_handler as _log_handler

Log = _log_handler.Log
LogHandler = _log_handler.LogHandler

_log = Log()

log_handler: LogHandler = _log.log_handler
startup = _log.startup
flush = _log.flush
print = _log.print  # NOQA - shadows the builtin; matches Log.print's public name
print_block = _log.print_block
info = _log.info
info_block = _log.info_block
debug = _log.debug
debug_block = _log.debug_block
notice = _log.notice
notice_block = _log.notice_block
warning = _log.warning
warning_block = _log.warning_block
error = _log.error
error_block = _log.error_block
traceback = _log.traceback
database = _log.database
database_block = _log.database_block
