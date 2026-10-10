# harness_designer/ui/widgets/list_ctrl.py

## `ListCtrl.GetValue` - re-validates every item on each read
`GetValue` calls `self._validate(...)` for every item in the list widget, converting each item's text to the item type. A read is linear in the item count and runs each time the value is requested. The list is small (a few array entries per property), so this is not a concern now. Caching the typed values and invalidating on edit would be the change if lists grow.

## `ListCtrl._show_context_menu` - builds the menu on each right-click
Constructed on demand, which is the expected cost for a context menu.
