## FILES

#### __init__.py

Re-exports the module as `_system_menu` only; no public symbols of its own.

#### database.py

`DatabaseMenu(QMenu)` -- Database menu (catalog/global-DB actions, e.g. opening the transition/housing editors).

#### edit.py

`EditMenu(QMenu)` -- Edit menu (undo/redo and selection-level actions).

#### file.py

`FileMenu(QMenu)` -- File menu (new/open/save project, export, etc.).

#### help.py

`HelpMenu(QMenu)` -- Help menu (About dialog, etc.).

#### settings.py

`SettingsMenu(QMenu)` -- Settings menu (app-level preferences/dialogs such as render/debug settings).

#### system_menu.py

`SystemMenu(QMenuBar)` -- assembles the main window's menu bar from the per-menu classes in this directory; one file per top-level menu.

#### view.py

`ViewMenu(QMenu)` -- View menu (dock/toolbar visibility toggles).

#### window.py

`WindowMenu(QMenu)` -- Window menu (dock/window arrangement).
