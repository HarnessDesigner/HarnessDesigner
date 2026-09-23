# harness_designer/app.py

## Line 46-50 — `_qt_message_handler` captures a full stack trace on every Qt message
`_traceback.format_stack()` runs unconditionally for every Qt-native message,
including routine `QtWarningMsg`/`QtInfoMsg`/`QtDebugMsg` severities that only
get `logger.warning`'d, not just the `QtCriticalMsg`/`QtFatalMsg` case that
actually needs the call stack for diagnosis. If Qt emits warnings/info messages
at any meaningful frequency (e.g. during GL surface setup, resizes), this adds
stack-walk cost on a path that runs on whatever thread triggered the Qt call.
Investigate whether `format_stack()` should be gated to only the
critical/fatal branch, or whether warning-level messages are rare enough in
practice that this is a non-issue.
