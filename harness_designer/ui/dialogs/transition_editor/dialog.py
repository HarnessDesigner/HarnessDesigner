# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

"""The transition editor dialog -- authors/corrects a catalog transition's
metadata and per-branch geometry, with a live 3D preview using the real
rendering pipeline (``objects_3d.transition._Body``, see ``preview.py``).
Modeled structurally on ``ui/dialogs/part_orientation.py``
(self-contained ``Canvas3D`` + own ``bounds.Manager``), not on the scratch
tool that validated this design (``scratches/transition_viewer/
transition_editor.py`` -- that tool's job, fixing the 111 existing catalog
rows, is done; its fixes are already merged into the live catalog).

See TRANSITION_EDITOR_DIALOG.md for the full design and decision log.
"""

import uuid
from typing import TYPE_CHECKING, Union as _Union

from PySide6 import QtCore
from PySide6 import QtGui
from PySide6 import QtWidgets

from .. import dialog_base as _dialog_base
from .. import part_search as _part_search
from ...editor_db import transition as _trans_editor_page
from . import preview as _preview
from .... import bounds as _bounds
from .... import config as _config
from ....gl import canvas_3d as _canvas3d
from .... import check_types as _check_types

if TYPE_CHECKING:
    from .... import objects as _objects
    from .... import ui as _ui
    from ....database.global_db import transition as _g_transition
    from ....gl import context as _gl_context
    from ...prop_ctrls import events as _events


#: A brand-new/duplicated row's not-yet-assigned foreign keys -- every
#: lookup table this schema references (manufacturers/families/series/
#: colors/materials/shapes/temperatures/protections) was seeded with a real
#: "Unknown"/"No X" row at exactly this id (see harness_designer_database's
#: builder/id_generator.py NIL_UUID, used to build the live catalog) -- so
#: this is a genuine, already-populated placeholder, not a dangling
#: reference the DB happens to tolerate.
_NIL_ID = b'\x00' * 16


class _Config:
    """Minimal config for this dialog's own canvas -- copied from
    ``part_orientation.py``'s own ``_Config`` (a self-contained scene, not
    a view into the mainframe's live editor3d)."""
    lighting = _config.Config.editor_3d.lighting
    keyboard_settings = _config.Config.editor_3d.keyboard_settings
    input = _config.Config.editor_3d.input
    renderer = _config.Config.editor_3d.renderer

    selected_color = [0.2, 0.6, 0.2, 0.35]
    background_color = [0.13, 0.13, 0.15, 1.0]

    class headlight:
        enable = False
        cutoff = 8.0
        dissipate = 50.0
        color = [0.6, 0.6, 0.4, 0.8]

    class virtual_canvas:
        width = 1920
        height = 1080

    class floor:
        enable = False
        ground_height = 0.0
        size = 2000
        enable_floor_lock = False

        class grid:
            primary_color = [0.3039, 0.3549, 0.3902, 0.0]
            secondary_color = [0.2925, 0.3430, 0.3430, 0.0]
            primary_line_color = [0.87, 0.88, 0.92, 1.0]
            secondary_line_color = [0.57, 0.59, 0.65, 1.0]
            primary_line_width = 0.8
            secondary_line_width = 0.25
            secondary_lines_per_tile = 4
            secondary_line_pattern = 0x0B2664D0
            secondary_line_shift = False
            size = 80
            enable = False

        class reflections:
            enable = False
            strength = 50.0

    class focal_target:
        enable = False
        color = [1.0, 0.4, 0.4, 1.0]
        radius = 0.25

    class axis_overlay:
        is_visible = False
        size = (35, 35)
        position = (0, 0)


class TransitionEditorDialog(_dialog_base.BaseDialog):
    """Pick an existing transition, start a new one, or load an existing
    one as a template (a copy saved under a new part number) -- then edit
    every column (reusing the catalog's own ``TransitionControl``/
    ``TransitionBranchControl`` widgets, see TRANSITION_EDITOR_DIALOG.md
    section 2) with a live 3D preview alongside.
    """
    config = _Config

    @_check_types.do
    def __init__(self, parent: "_ui.MainFrame") -> None:
        _dialog_base.BaseDialog.__init__(
            self, parent, 'Transition Editor', size=(1500, 900),
            button_ids=QtWidgets.QDialogButtonBox.StandardButton.Close)

        self._mainframe = parent
        self._transition: _Union["_g_transition.Transition", None] = None
        self._preview: _preview.PreviewTransition | None = None

        # Self-contained scene, exactly like part_orientation.py's own --
        # must not share the real mainframe's pooled AABB/OBB arrays.
        self._bounds_manager = _bounds.Manager()

        self.canvas = _canvas3d.Canvas3D(self, _Config, size=(1500, 900))

        mode_row = QtWidgets.QHBoxLayout()
        self._existing_btn = QtWidgets.QPushButton('Select Existing...')
        self._new_btn = QtWidgets.QPushButton('New')
        self._template_btn = QtWidgets.QPushButton('Load As Template...')
        mode_row.addWidget(self._existing_btn)
        mode_row.addWidget(self._new_btn)
        mode_row.addWidget(self._template_btn)

        self._existing_btn.clicked.connect(self._on_select_existing)
        self._new_btn.clicked.connect(self._on_new)
        self._template_btn.clicked.connect(self._on_load_template)

        self.status = QtWidgets.QLabel('Pick an existing transition, start a new one, or load one as a template.')
        self.status.setWordWrap(True)

        # The catalog's own shared TransitionControl -- reparented into
        # this dialog for as long as it's open, exactly the way
        # TransitionControl.set_obj already reparents its own branch-tab
        # widgets between "in use" and "parked on the mainframe, hidden".
        self._control = parent.global_db.transitions_table.control
        self._control.setParent(self.panel)
        self._control.show()

        side = QtWidgets.QWidget(self.panel)
        side_layout = QtWidgets.QVBoxLayout(side)
        side_layout.addLayout(mode_row)
        side_layout.addWidget(self.status)
        side_layout.addWidget(self._control, 1)

        h_layout = QtWidgets.QHBoxLayout(self.panel)
        h_layout.addWidget(self.canvas, 3)
        h_layout.addWidget(side, 2)
        self.setLayout(h_layout)

        # Debounces the live preview the same way the scratch tool's own
        # editor did -- typing/dragging a spin box can fire many
        # propertyChanged signals in a burst; only the last one within
        # ~150ms actually triggers a rebuild.
        self._preview_timer = QtCore.QTimer(self)
        self._preview_timer.setSingleShot(True)
        self._preview_timer.setInterval(150)
        self._preview_timer.timeout.connect(self._rebuild_preview)

        # Tracks which branch tab was active so switching to a different
        # transition can restore it (clamped to the new part's branch
        # count) instead of always resetting to tab 0 -- see
        # TRANSITION_EDITOR_DIALOG.md section 3's tab-persistence note.
        self._last_branch_tab_index = 0

        self._control.branch_page.currentChanged.connect(self._on_branch_tab_changed)
        self._control.branch_count_ctrl.propertyChanged.connect(self._on_branch_count_changed)

    # -- mode picker --------------------------------------------------

    @_check_types.do
    def _on_select_existing(self) -> None:
        part_id = self._pick_part('Select Transition')
        if part_id is None:
            return

        self._load(self._mainframe.global_db.transitions_table[part_id])

    @_check_types.do
    def _on_new(self) -> None:
        placeholder = f'NEW-{uuid.uuid4().hex[:8].upper()}'

        transition = self._mainframe.global_db.transitions_table.insert(
            part_number=placeholder, mfg_id=_NIL_ID, description='', family_id=_NIL_ID,
            series_id=_NIL_ID, color_id=_NIL_ID, material_id=_NIL_ID, branch_count=0,
            shape_id=_NIL_ID, protection_ids=[], adhesive_ids=[], cad_id=None,
            datasheet_id=None, image_id=None, min_temp_id=_NIL_ID, max_temp_id=_NIL_ID,
            weight=0.0)

        self.status.setText(
            f'New transition created as {placeholder!r} -- set a real part number and add branches below.')
        self._load(transition)

    @_check_types.do
    def _on_load_template(self) -> None:
        part_id = self._pick_part('Load Transition As Template')
        if part_id is None:
            return

        source = self._mainframe.global_db.transitions_table[part_id]
        clone = self._clone_transition(source)
        self.status.setText(
            f'Loaded {source.part_number!r} as a template -- saved as a new part '
            f'({clone.part_number!r}); change the part number below before saving further edits.')
        self._load(clone)

    @_check_types.do
    def _pick_part(self, title: str) -> bytes | None:
        dlg = _part_search.SearchDialog(
            self._mainframe, _trans_editor_page.TransitionsPage,
            self._mainframe.global_db.transitions_table, title)

        part_id = None
        if dlg.exec() == QtWidgets.QDialog.DialogCode.Accepted:
            part_id = dlg.GetValue()

        dlg.deleteLater()
        return part_id

    @_check_types.do
    def _clone_transition(self, source: "_g_transition.Transition") -> "_g_transition.Transition":
        """Insert a new ``transitions`` row (and a copy of every one of
        *source*'s branches) with all the same field values, under a
        fresh, guaranteed-unique part number -- "load as template" is just
        this plus loading the result instead of *source* itself, so the
        user edits an independent copy from the very first keystroke, per
        TRANSITION_EDITOR_DIALOG.md section 3.
        """
        table = self._mainframe.global_db.transitions_table
        new_part_number = f'{source.part_number}-COPY-{uuid.uuid4().hex[:6].upper()}'

        protection_ids = [] if source.protection_id == _NIL_ID else [source.protection_id]

        clone = table.insert(
            part_number=new_part_number, mfg_id=source.mfg_id, description=source.description,
            family_id=source.family_id, series_id=source.series_id, color_id=source.color_id,
            material_id=source.material_id, branch_count=0, shape_id=source.shape_id,
            protection_ids=protection_ids, adhesive_ids=list(source.adhesive_ids),
            cad_id=source.cad_id, datasheet_id=source.datasheet_id, image_id=source.image_id,
            min_temp_id=source.min_temp_id, max_temp_id=source.max_temp_id, weight=source.weight)

        branches_table = table.db.transition_branches_table
        for idx, branch in enumerate(source.branches, start=1):
            if branch is None:
                continue

            branches_table.insert(
                transition_id=clone.db_id, idx=idx, name=branch.name,
                bulb_offset=None if branch.bulb_offset.as_float == (0.0, 0.0, 0.0) else branch.bulb_offset,
                bulb_length=branch.bulb_length or None, min_dia=branch.min_dia, max_dia=branch.max_dia,
                length=branch.length, angle=branch.angle, offset=branch.offset,
                flange_height=branch.flange_height, flange_width=branch.flange_width)

        clone.branch_count = len(source.branches)
        clone.invalidate_branches()

        return clone

    # -- loading/rebuilding --------------------------------------------

    @_check_types.do
    def _load(self, transition: "_g_transition.Transition") -> None:
        previous_tab = self._control.branch_page.currentIndex()
        if previous_tab >= 0:
            self._last_branch_tab_index = previous_tab

        self._transition = transition
        self._control.set_obj(transition)

        branch_page = self._control.branch_page
        if branch_page.count():
            restore_to = min(self._last_branch_tab_index, branch_page.count() - 1)
            branch_page.setCurrentIndex(max(restore_to, 0))

        if self._preview is not None:
            self.canvas.remove_object(self._preview)

        with self.canvas.context:
            self._preview = _preview.PreviewTransition(self, transition)

        self.canvas.Refresh()

    @_check_types.do
    def _on_branch_tab_changed(self, index: int) -> None:
        if index >= 0:
            self._last_branch_tab_index = index

    @_check_types.do
    def _on_branch_count_changed(self, _evt: "_events.PropertyEvent") -> None:
        self._preview_timer.start()

    @_check_types.do
    def _rebuild_preview(self) -> None:
        if self._transition is None or self._preview is None:
            return

        self._transition.invalidate_branches()
        self._preview.obj3d.rebuild(self._transition)

        # Belt-and-suspenders alongside build()'s own self.editor3d.update()
        # call (which reaches this dialog's own QWidget.update(), not
        # necessarily the GL canvas specifically) -- part_orientation.py's
        # own SetValue() does the same explicit canvas refresh rather than
        # relying on generic propagation.
        self.canvas.Refresh()

    # -- BaseDialog/canvas plumbing (mirrors part_orientation.py exactly) --

    @_check_types.do
    def add_object(self, obj: "_objects.ObjectBase") -> None:
        self.canvas.add_object(obj)

    @_check_types.do
    def remove_object(self, obj: "_objects.ObjectBase") -> None:
        self.canvas.remove_object(obj)

    @property
    @_check_types.do
    def editor2d(self) -> None:
        return None

    @property
    @_check_types.do
    def editor3d(self) -> "TransitionEditorDialog":
        return self

    @property
    @_check_types.do
    def editor_pegboard(self) -> None:
        return None

    @property
    @_check_types.do
    def bounds_manager(self) -> _bounds.Manager:
        return self._bounds_manager

    @_check_types.do
    def _set_selected(self, obj: _Union["_objects.ObjectBase", None]) -> None:
        pass

    @_check_types.do
    def set_selected(self, obj: _Union["_objects.ObjectBase", None]) -> None:
        pass

    @_check_types.do
    def get_selected(self) -> None:
        return None

    @_check_types.do
    def Refresh(self, *_, **__) -> None:
        self.canvas.Refresh()

    @property
    @_check_types.do
    def context(self) -> "_gl_context.GLContext":
        return self.canvas.context

    @_check_types.do
    def _release_control(self) -> None:
        """Reparent the shared TransitionControl back onto the mainframe
        and hide it -- exactly the state ``TransitionsTable.control``
        leaves it in when nothing has requested it yet, so the next thing
        that asks for it (this dialog again, or whatever else in the app
        eventually shows it) gets it back in the same condition.
        """
        self._control.branch_page.currentChanged.disconnect(self._on_branch_tab_changed)
        self._control.branch_count_ctrl.propertyChanged.disconnect(self._on_branch_count_changed)
        self._control.set_obj(None)
        self._control.hide()
        self._control.setParent(self._mainframe)

    @_check_types.do
    def accept(self) -> None:
        self._release_control()
        self.canvas.cleanup()
        super().accept()

    @_check_types.do
    def reject(self) -> None:
        self._release_control()
        self.canvas.cleanup()
        super().reject()

    @_check_types.do
    def closeEvent(self, event: "QtGui.QCloseEvent") -> None:
        self._release_control()
        self.canvas.cleanup()
        super().closeEvent(event)
