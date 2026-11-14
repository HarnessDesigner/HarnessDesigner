# harness_designer/ui/prop_ctrls/path_prop.py

PathProperty -- built on _path_ctrl_base.PathCtrl; a file/path-valued property with a picker dialog.

Timers / deferred calls: line 56 (singleShot). A periodic timer keeps firing while the widget is alive; make sure it is stopped when the dock is hidden.

Status: static read of the code only. Nothing here has been profiled.
