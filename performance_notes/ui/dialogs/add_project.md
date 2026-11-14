# harness_designer/ui/dialogs/add_project.py

AddProjectDialog -- new-project creation (name, location, color).

Timers / deferred calls: line 148 (singleShot), line 178 (singleShot). A periodic timer keeps firing while the widget is alive; make sure it is stopped when the dock is hidden.

Status: static read of the code only. Nothing here has been profiled.
