## FILES

#### __init__.py

Package init for the assembly editor dock; no content beyond the standard package marker.

#### editor_assembly.py

Defines `EditorAssembly(DockBase)` — the dock wrapper (just constructs an `EditorAssemblyPanel` and exposes it via `.editor`), and `EditorAssemblyPanel(QtWidgets.QWidget)` — an empty panel shell. This dock is currently a minimal/near-empty placeholder: unlike `editor_3d`/`editor_schematic`/`editor_pegboard`, there is no `set_selected`/`add_object`/`remove_object`/`set_clone_obj` forwarding here at all, no canvas, and no object fan-out of its own — it is not yet part of `mainframe.py`'s object fan-out, so don't assume feature parity with the other editor docks without checking.
