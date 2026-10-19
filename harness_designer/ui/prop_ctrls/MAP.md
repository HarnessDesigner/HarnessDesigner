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

`AutocompleteStringProperty` -- a string property backed by the shared autocomplete engine (`ui/widgets/auto_complete.py`).

#### bitmap_combobox_prop.py

`BitmapComboBoxProperty` -- a combobox property whose entries also carry an icon.

#### bool_prop.py

`BoolProperty` -- a plain checkbox-backed boolean property.

#### category.py

`Category(QtWidgets.QScrollArea)` -- a collapsible group of properties inside the object-editor dock; the property-grid's section header/body shell.

#### choice_prop.py

A fixed-choice property control paired with `ui/widgets/choice_ctrl.py`.

#### color_prop.py

`ColorProperty` -- wraps `ui/widgets/color_ctrl.py`'s swatch-plus-picker; emits a `[name, Color]` pair on `propertyChanged` (see `events.PropertyValue`).

#### combobox_prop.py

`ComboBoxProperty` -- a plain dropdown-backed property control.

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
