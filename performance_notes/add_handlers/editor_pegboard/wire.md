# harness_designer/add_handlers/editor_pegboard/wire.py

## `hover` - per move
Calls `_pick` (which calls `find_object`), `_set_growing_position`, and `self.mainframe.editor_pegboard.editor.update()`. The `update()` repaints the peg-board view on every move. It is the same candidate as [editor_3d/wire.md](../editor_3d/wire.md): skip it when nothing changed.

## `_attach_end` - once per click
Checks compatibility and attaches each end. Not a concern.
