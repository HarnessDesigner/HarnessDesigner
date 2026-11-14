# harness_designer/ui/dialogs/project_model_dialog.py

ProjectModelDialog -- pick/change the project's own 3D model file and color; reached from the 3D empty-space menu's Add/Edit Project Model entry.

Timers / deferred calls: line 110 (singleShot). A periodic timer keeps firing while the widget is alive; make sure it is stopped when the dock is hidden.

Status: static read of the code only. Nothing here has been profiled.
