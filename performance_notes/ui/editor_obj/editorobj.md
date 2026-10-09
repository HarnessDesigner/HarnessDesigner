# harness_designer/ui/editor_obj/editorobj.py

## `EditorObjPanel.set_selected` - control swap on every selection
Each selection change sets a wait cursor, detaches the previous table control (`set_obj(None)`, `hide`, `setParent`), then attaches the new one (`set_obj(obj.db_obj)`, `setParent`). The controls are per-table singletons that are reused for the life of the app, so the swap does not construct widgets. Each `set_obj` call loads that object's properties, which is the real cost; it is one query set per selection, which is what a property editor needs.

The swap also calls `set_obj(None)` on the outgoing control. That is deliberate: it releases the outgoing object from the reused widget so it can be collected (see the comment in the code). No change.

## `table.control` lookup - now a plain attribute read
Before this pass the lookup was `getattr(obj.db_obj.table, 'control', None)`. `TableBase` and `PJTTableBase` now define `control` as a property that returns `None`, and the 31 tables that have an editor override it. The lookup is now one attribute read. There is no per-selection cost change.
