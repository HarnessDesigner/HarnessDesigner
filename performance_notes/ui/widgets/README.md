# performance_notes/ui/widgets

Covers `harness_designer/ui/widgets/`.

- [cad_datasheet_ctrl.md](cad_datasheet_ctrl.md) - datasheet preview: paint-time scaling and synchronous PDF render
- [search_db.md](search_db.md) - search result loading on the UI thread (the main concern in this folder)
- [list_ctrl.md](list_ctrl.md) - list value read
- [auto_complete.md](auto_complete.md) - completer model rebuild
- [autocomplete_textctrl.md](autocomplete_textctrl.md) - the multi-line control's key handling and completer model rebuild

## Reviewed for performance
The four files above were read for their hot paths. The remaining widgets (`foldpanelbar.py`, `float_ctrl.py`, `int_ctrl.py`, `text_ctrl.py`, `triple_float_ctrl.py`, `tri_state_checkbox_ctrl.py`, `stipple_ctrl.py`, `editable_tab_ctrl.py`, `combobox_ctrl.py`, `choice_ctrl.py`, `checkbox_ctrl.py`, `color_ctrl.py`, `context_menus.py`, `autocomplete_combobox.py`, `bitmap_autocomplete_combobox.py`) were checked for structure and event handling only. `foldpanelbar.py` is 1,668 lines and was not read line by line, so it has no notes yet.

## Found while reading `autocomplete_combobox.py` (not fixed)
`AppendItems` calls `Append` once per item, and each `Append` rebuilds the completer model from the whole list, so adding n items costs O(n^2) in model construction. `Set`/`SetItems` build the model once. Callers that load a long list should use `SetItems`.
