## FILES

#### __init__.py

Package init for the 3D editor dock; no content beyond the standard package marker.

#### editor_3d.py

Defines `Editor3D(DockBase)` — the dock wrapper, and `Editor3DPanel(gl.canvas3d.Canvas3D)` — the actual GL canvas widget. `Editor3D` exposes `context`/`camera` (forwarded from the inner canvas, needed by object code that acquires/releases the GL context directly), and `set_selected`/`add_object`/`remove_object`/`set_clone_obj`/`clear`/`bind` — all thin forwards to `Editor3DPanel`, letting `mainframe.py`'s fan-out treat this editor uniformly alongside `editor_schematic`/`editor_pegboard`. `Editor3DPanel.center_on_object(obj)` pans/zooms the camera to frame a given object. This file is the reference implementation that `editor_pegboard.py`'s and `editor_schematic.py`'s own docstrings describe themselves as "structural mirrors" of — when extending one of those two, this is the pattern to match.
