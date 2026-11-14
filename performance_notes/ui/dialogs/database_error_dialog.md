# harness_designer/ui/dialogs/database_error_dialog.py

DatabaseErrorDialog -- shows a database error with its full context (table, row id, SQL and params) and traceback. OK is the only way out (no Escape, no native close, per the dialog design convention described under dialog_base.py below); the caller logs the error, this dialog only displays it.

Event / model handlers that Qt calls repeatedly (per paint, per mouse move, per cell, per keystroke):
- `DatabaseErrorDialog.keyPressEvent` (line 60-70): no loops or allocations found.
None of them allocates or loops in a way the AST pass flags, so they are cheap per call.

Status: static read of the code only. Nothing here has been profiled.
