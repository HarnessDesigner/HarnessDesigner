# performance_notes/ui/system_menu

Covers `harness_designer/ui/system_menu/` (`database.py`, `edit.py`, `file.py`, `help.py`, `settings.py`, `system_menu.py`, `view.py`, `window.py`).

## Reviewed
All modules were scanned for blocking and synchronous work. The menus are thin: each one builds `QAction`s at construction and forwards `triggered` signals to the main frame or to a dialog.

## Notes
- `database.py`, `help.py`, and `settings.py` open modal dialogs with `exec()`. Those block the event loop only while the user has the dialog open, which is the expected behaviour for these dialogs.
- `view.py` (158 lines) is the largest module and builds the view-toggle actions when the menu is constructed. The work is a fixed number of `addAction` calls. It was not profiled.
- No module here queries the database, reads files, or runs a loop over project objects, so none of these modules needs a cache or a worker thread.
