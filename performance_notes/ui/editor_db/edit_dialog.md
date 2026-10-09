# harness_designer/ui/editor_db/edit_dialog.py

## `EditDialog.__init__` / `Destroy` - the editor control is re-parented on each open and close
Each open reparents the table's shared `control` widget into a new dialog panel, then `Destroy` reparents it back to the main frame and hides it. The widget is reused rather than rebuilt, so opening an edit dialog costs one `set_obj` and layout pass, not a widget construction. No change is needed.
