## FILES

#### __init__.py

No imports found -- a plain empty package marker, no re-exports.

#### auto_complete.py

`_AutoCompleter`/`AutoComplete` -- a completion engine and a `QLineEdit` built on it. Only `AutoComplete` (the MySQL login dialog's user name) and `ui/dialogs/part_search.py`'s `SearchTextEdit` use it. `autocomplete_combobox.py`, `autocomplete_textctrl.py` and `bitmap_autocomplete_combobox.py` do NOT: each builds its own `QCompleter` (the same few lines, four times). An older version of this note said they were all built on it.

#### autocomplete_combobox.py

`AutoCompleteComboBox` -- an editable `QComboBox` with its own inline `QCompleter` and a mirrored choice list (`SetItems`/`Append`/`Insert`/`Delete`/`Clear` keep the list and the completer in step; Qt's own `clear()`/`addItems()` do NOT feed the completer). Used by `ui/prop_ctrls/combobox_prop.py`, `color_prop.py`, `ComboBoxCtrl` and `ui/toolbar/snap_angle_button.py`. It has no Enter signal of its own: it passes on Qt's, and `currentTextChanged` fires on EVERY keystroke. A wrapper must commit on `textActivated` (a list pick) and `lineEdit().returnPressed` (Enter), as `ComboBoxProperty` does since 2026-10-24 and `snap_angle_button.py` does with `activated` + `editingFinished`.

#### autocomplete_textctrl.py

`AutoCompleteTextCtrl` -- a single-line `QLineEdit` with its own inline `QCompleter`; Qt's `returnPressed` is its Enter (nothing is added to the text). `AutoCompleteTextEdit` (added 2026-10-24) is the multi-line version, a `QPlainTextEdit` with a popup completer that matches the line being typed. It owns the multi-line Enter rule (user): the first two Enters type newlines, the THIRD Enter in a row (`COMMIT_ENTERS`) emits `returnPressed` and is NOT added to the text, and the newlines at the end are cut down to ONE (the only thing ever removed; spaces and inner newlines stay). While the popup is open Enter/Tab/Escape belong to it. Both controls have the same choice API, `SetValue` and `GetValue`.

#### bitmap_autocomplete_combobox.py

`BitmapAutoCompleteComboBox` -- an autocomplete combo whose entries also carry an icon. Its docstring says `currentTextChanged` fires on selection or Enter only; it fires on every keystroke. Only the unused `BitmapComboBoxProperty` builds it.

#### cad_datasheet_ctrl.py

`CADDatasheetCtrl`/`CADDatasheetPreviewCtrl` plus private helpers `_ImageView` (a `QGraphicsView` image pan/zoom) and `_PDFPanFilter` -- renders a part's CAD/datasheet preview image or PDF page; backs `ui/prop_ctrls/datasheet_cad_prop.py`.

#### checkbox_ctrl.py

`CheckboxCtrl` -- a thin `QWidget` pairing a native Qt checkbox with this app's signal/validation conventions.

#### choice_ctrl.py

`ChoiceCtrl` -- a thin `QWidget` wrapper for a fixed-choice dropdown, backing `ui/prop_ctrls/choice_prop.py`.

#### code_editor_ctrl.py

`CodeEditorCtrl`, a `QPlainTextEdit`-based Python editor (line numbers via `_LineNumberArea`, Pygments syntax highlighting via `_PygmentsHighlighter`, auto-indent) -- the script-editor widget used by the scraper tool, including `ui/scraper_inspector/snippet_pane.py`'s generated-script pane.

#### color_ctrl.py

`ColorCtrl` -- the color-swatch-plus-picker widget used by `ui/prop_ctrls/color_prop.py`.

#### combobox_ctrl.py

`ComboBoxCtrl` -- a label plus `AutoCompleteComboBox`, used by `ui/dialogs/project_dialog.py` and `color_ctrl.py` (NOT by `combobox_prop.py`, which builds its own `AutoCompleteComboBox`; an older note said it backs it). Known, not fixed: its docstring says `currentTextChanged` fires for selections and Enter commits only, but it fires on every keystroke (and Enter adds more), so `ColorCtrl` emits `colorChanged` per keystroke with the previous colour; `process_enter` is stored and never read.

#### context_menus.py

`Rotate2DMenu`, `Mirror2DMenu`, `Rotate3DMenu`, `Mirror3DMenu` -- right-click rotate/mirror submenus for selected objects in the schematic and 3D views.

#### editable_tab_ctrl.py

`EditableTabBar`/`EditableTabCtrl` -- a `QTabWidget` whose tab labels can be renamed in place.

#### empty_space_menus.py

`_EmptySpaceMenu(QMenu)` base plus `EmptySpaceMenu3D`, `EmptySpaceMenuPegboard`, `EmptySpaceMenuSchematic` -- the right-click menu shown when nothing is under the cursor in each view (3D: wire/terminal/housing/project model; pegboard: wire/terminal/housing; schematic: terminal/housing). The click position becomes the new object's placement point via each `start_add`'s `mouse_pos` argument replaying a synthetic MOVE+LEFT_UP through `add_handlers.base.click_at` -- a housing finishes placement immediately, a wire drops its first point and stays armed for the next click. Driven by a new `EVT_GL_EMPTY_RIGHT_CLICK` event fired from `mouse_handler_base.on_right_up` only when nothing at all is under the cursor; mainframe shows the matching per-view menu at the click point. Built 2026-09-25 as part of the free-standing-terminal feature and, as of that date, had **not yet been run in the live GUI** -- treat it as unverified until confirmed working end to end. The companion `handlers/` half of this feature (wiring the menu actions to the add-handlers) is owned separately from this widget. Every new `EVT_GL_*` event name must also exist as a `Signal` on `gl/canvas_base.py` -- an existing, codebase-wide convention that this file's triggering event follows too.

#### float_ctrl.py

`FloatCtrl` -- a thin `QWidget` wrapper pairing a native Qt float spin box with this app's signal/validation conventions; backs `ui/prop_ctrls/float_prop.py`.

#### foldpanelbar.py

`FoldPanelBar` and its supporting classes (`CaptionBarStyle`, `CaptionBar`, `FoldWindowItem`, `FoldPanelItem`) -- a collapsible accordion-panel container.

#### int_ctrl.py

`IntCtrl` -- a thin `QWidget` wrapper pairing a native Qt int spin box with this app's signal/validation conventions; backs `ui/prop_ctrls/int_prop.py`.

#### list_ctrl.py

`ListCtrl` -- a general-purpose list widget wrapper.

#### search_db.py

`SearchPanel` and its private pieces (`_SearchPanel`, `_SearchPanelField`, `_ResultCtrl`, `_ItemsPanel`, `_ItemRow`) -- a reusable filtered-results-list widget used where a lighter-weight DB search than the full `ui/dialogs/part_search.py` dialog is needed.

#### stipple_ctrl.py

`StippleEditor`/`StippleCtrl` -- edits a bit-pattern line-stipple value, used for dashed/dotted line rendering styles.

#### text_ctrl.py

`TextCtrl` -- a thin `QWidget` wrapper pairing a native Qt line edit with this app's signal/validation conventions; backs `ui/prop_ctrls/string_prop.py`.

#### tri_state_checkbox_ctrl.py

`_TriStateCheckBox`/`TriStateCheckboxCtrl` -- a checkbox supporting an indeterminate third state, backing `ui/prop_ctrls/tri_state_checkbox_prop.py`.

#### triple_float_ctrl.py

`TripleFloatCtrl` -- a 3-axis float group used by `ui/prop_ctrls/point_prop.py` (and therefore by `position_prop`/`scale_prop`/`angle_prop` too).

#### wrap_label.py

`WrapLabel(QLabel)` -- caps a label's `sizeHint`/`minimumSizeHint` widths, shows plain text only, and puts any text the caller can't control (a page address, a server/API message, a file path, script output) into the tooltip instead of letting it set layout size. Exists because of a real production bug (2026-10-17): a 1,155-character, no-spaces Google search URL went into the scraper inspector's word-wrapped message label. Qt cannot break an unbroken word, so the label demanded ~5,200px and the app's main window grew to 5,805px wide, outgrowing the screen and locking the browser/inspector splitter -- made permanent because `MainFrame._save_size` writes whatever size the window currently has into `Config` on every resize. `setMinimumWidth(1)` on a plain `QLabel` does **not** fix this: Qt layouts take `max(sizeHint, minimumSizeHint)` of each widget, so both hints must be capped, which is exactly what `WrapLabel` does. Use `WrapLabel`, not `QLabel`, for any label/button/combo that can show a page address, a server/API message, a file path, or script output; messages that embed an address should also cut it with `browser_widget.shorten_url`. Already switched: the scraper inspector's message line and Response header, the snippet pane title, the source status line, and the assistant/console/editor labels.

## FOLDERS

#### resources/

Pure image assets (no Python) used by widgets in this directory -- e.g. the up/down reorder button icons used by list-style controls. See `resources/MAP.md`.
