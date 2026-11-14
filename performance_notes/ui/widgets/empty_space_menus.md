# harness_designer/ui/widgets/empty_space_menus.py

_EmptySpaceMenu(QMenu) base plus EmptySpaceMenu3D, EmptySpaceMenuPegboard, EmptySpaceMenuSchematic -- the right-click menu shown when nothing is under the cursor in each view (3D: wire/terminal/housing/project model; pegboard: wire/terminal/housing; schematic: terminal/housing).

Timers / deferred calls: line 41 (singleShot). A periodic timer keeps firing while the widget is alive; make sure it is stopped when the dock is hidden.

Status: static read of the code only. Nothing here has been profiled.
