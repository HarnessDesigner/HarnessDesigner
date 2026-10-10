# harness_designer/add_handlers/editor_3d/wire_service_loop.py

## `hover` - per move
`_closest_point_on_line` projects onto a fixed line (cheap), and `_update_preview` moves the start point inside `with self.mainframe.editor3d.context:`. That is a context switch and a 3D update per move, the same candidate as [bundle.md](bundle.md).

## `split_wire_for_loop` and `restore_wire_from_split` - once per session
These cut and rejoin the wire. Not a concern.
