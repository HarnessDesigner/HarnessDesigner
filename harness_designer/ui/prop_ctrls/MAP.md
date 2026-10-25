## FILES

#### __init__.py

Imports every property-control module so each registers itself; no public symbols of its own.

#### _array_dialog_base.py

`_ArrayDialog(QDialog)` -- the shared popup for editing a list value, subclassed by each array property type's own dialog below.

#### _image_ctrl_base.py

`ImageCtrl` -- private shared widget base factored out of `image_prop.py` so the picker/preview chrome isn't duplicated per property type.

#### _path_ctrl_base.py

`PathCtrl` -- private shared widget base factored out of `path_prop.py` so the file-picker chrome isn't duplicated per property type.

#### angle_prop.py

`AngleProperty` -- a `QGroupBox` built on `point_prop.PointProperty` for editing a 3-axis angle value.

#### array_float_prop.py

`ArrayFloatDialog`/`ArrayFloatProperty` -- subclasses `_array_dialog_base._ArrayDialog`/the base property for a list of floats.

#### array_int_prop.py

`ArrayIntDialog`/`ArrayIntProperty` -- subclasses `_array_dialog_base._ArrayDialog`/the base property for a list of ints.

#### array_string_prop.py

`ArrayStringDialog`/`ArrayStringProperty` -- subclasses `_array_dialog_base._ArrayDialog`/the base property for a list of strings.

#### autocomplete_string_prop.py

`AutocompleteStringProperty` -- a string property over `AutoCompleteTextCtrl` (single-line, the default) or, with `multiline=True`, `AutoCompleteTextEdit`. Enter rules (user, 2026-10-24): single-line, ONE Enter commits; multi-line, THREE Enters in a row commit and the text keeps a single newline at the end; the committing Enter is never added to the text; NOTHING is stripped (spaces matter to the completer). Tooltips: "Press Enter to save" / "Press Enter 3 times to save". Every Enter that commits sends `propertyChanged` (no same-value check, unlike `StringProperty`). A committed single-line value joins the completion choices (once; the caller's list is copied, not changed); a multi-line text does not, because the completer matches one line at a time. Before 2026-10-24 it only committed when the text ended in two newlines, which a `QLineEdit` cannot hold, so it never committed at all. It has no callers yet.

#### bitmap_combobox_prop.py

`BitmapComboBoxProperty` -- a combobox property whose entries also carry an icon. No callers. Known, not fixed: it commits on every keystroke (`currentTextChanged`), and its `SetItems`/`Clear` use Qt's `clear()`/`addItems()`, so the completer gets no choices and the widget's own `GetItems` disagrees with what was set.

#### bool_prop.py

`BoolProperty` -- a plain checkbox-backed boolean property.

#### category.py

`Category(QtWidgets.QScrollArea)` -- a collapsible group of properties inside the object-editor dock; the property-grid's section header/body shell.

#### choice_prop.py

A fixed-choice property control paired with `ui/widgets/choice_ctrl.py`.

#### color_prop.py

`ColorProperty` -- wraps `ui/widgets/color_ctrl.py`'s swatch-plus-picker; emits a `[name, Color]` pair on `propertyChanged` (see `events.PropertyValue`). No callers. Known, not fixed: it has the same two faults as `BitmapComboBoxProperty` (per-keystroke commit, completer never fed).

#### combobox_prop.py

`ComboBoxProperty` -- an editable autocomplete dropdown (it owns an `AutoCompleteComboBox`) built at 14 places: circuit Name / Circuit Number / Return Path, manufacturer, family, series, plating, temperature, cavity lock, splice and terminal types, and others. **It commits on Enter (`returnPressed`) or on picking a list entry (`textActivated`), NEVER while typing** (fixed 2026-10-24): it used to listen to `currentTextChanged`, which an editable combo fires on every keystroke, and the handlers behind these controls create a row for a value they have not seen, so typing `new` created the circuits `n`, `ne` and `new`. A second fault: its `SetItems`/`Clear` used Qt's `clear()`/`addItems()`, so the completer never got the choices; they now call `AutoCompleteComboBox.SetItems`/`Clear`. The text is sent exactly as typed (never stripped). Enter on an unchanged value sends nothing (`_value` check). With the inline suggestion showing, Enter commits the suggestion (`new` shows `new circuit`); Delete drops it first.

#### datasheet_cad_prop.py

`DatasheetCADProperty` -- shows/edits a part's CAD/datasheet reference, built on `ui/widgets/cad_datasheet_ctrl.py`.

#### enum_prop.py

`EnumProperty` -- a property control for a fixed enum-typed DB column.

#### events.py

`PropertyEvent` -- the event object every control's `propertyChanged` signal carries (name + new value). `PropertyValue` (`TYPE_CHECKING`-only) is the union of every value shape a control can emit, including the color control's `[name, Color]` pair.

#### float_prop.py

`FloatProperty` -- a single-float property control.

#### image_prop.py

`ImageProperty` -- built on `_image_ctrl_base.ImageCtrl`; shows/edits an image-valued property with a preview and file picker.

#### int_prop.py

`IntProperty` -- a single-int property control.

#### long_string_prop.py

`LongStringProperty` plus its own `LongStringDialog` popup editor, for a string too long to edit comfortably inline.

#### model3d_prop.py

`Model3DProperty` -- picks/shows a part's 3D model reference.

#### path_prop.py

`PathProperty` -- built on `_path_ctrl_base.PathCtrl`; a file/path-valued property with a picker dialog.

#### point_prop.py

`PointProperty` -- the shared xyz-axis `QGroupBox` base that `position_prop.PositionProperty`, `scale_prop.ScaleProperty`, and `angle_prop.AngleProperty` all subclass.

#### position_prop.py

`PositionProperty` -- subclasses `point_prop.PointProperty` for a 3-axis position value.

#### prop_base.py

`Property(QtWidgets.QWidget)` -- the common base every control in this directory derives from; owns the shared `propertyChanged` signal that lets the object-editor dock and the catalog's per-table control widgets (see `ui/editor_db`) bind a DB-row attribute to a control generically, without per-type glue code at the call site. Those per-table control widgets built from these property controls (`database/project_db/pjt_*.py`'s `PJT*Table._control`) are **class-level singletons**, not per-instance -- the same `QTabWidget` control instance is reused for the whole app session across every project (re)load. Detaching the control from the object-editor dock is not enough to release the `db_obj` it was last bound to: the widget keeps a strong `self.db_obj` reference until something explicitly calls `control.set_obj(None)`. A past bug (found 2026-07-29) left the outgoing project's last-selected object pinned indefinitely because `EditorObjPanel.set_selected(None)` only hid/reparented the control without clearing its binding; fixed by always calling `control.set_obj(None)` on whatever control is being detached or swapped. Any new code that parks one of these per-table controls elsewhere (e.g. `ui/dialogs/transition_editor/dialog.py` reparenting `TransitionsTable.control` into itself) must restore this same clear-before-release discipline.

#### scale_prop.py

`ScaleProperty` -- subclasses `point_prop.PointProperty` for a 3-axis scale value.

#### string_prop.py

`StringProperty` -- a single-line string property control.

#### tri_state_checkbox_prop.py

`TriStateCheckboxProperty` -- backs onto `ui/widgets/tri_state_checkbox_ctrl.py`'s indeterminate-third-state checkbox.
