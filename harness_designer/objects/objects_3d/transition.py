# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

from typing import TYPE_CHECKING

import weakref
import numpy as np
from PySide6.QtWidgets import QMenu
import build123d
import math
from copy import deepcopy

from ...ui.widgets import context_menus as _context_menus
from ...geometry import point as _point
from ...geometry import angle as _angle
from . import base_3d as _base_3d
from . import menu_ops as _menu_ops
from ...shapes import sphere as _sphere
from ...gl import vbo as _vbo
from ...gl import materials as _materials
from ...gl.canvas_base import interaction as _interaction
from ... import config as _config
from ... import utils as _utils
from ... import color as _color
from ... import check_types as _check_types


if TYPE_CHECKING:
    from ...database.global_db import transition as _g_transition
    from ...database.project_db import pjt_transition as _pjt_transition
    from .. import transition as _transition
    from ...database.project_db import pjt_transition_branch as _pjt_transition_branch
    from ... import ui as _ui


Config = _config.Config.editor_3d


# TODO:
#       setting the angles
#       setting position
#       make branches accessable to wires and bundles
#       routing wire through transition
#       snap bundle to branch
#       snap wire to branch
#       changing between transition selection and branch selection
#       setting branch diameter


@_check_types.do
def _build_model(b_data: "_g_transition.Transition", branches: list["Branch"], update_points=False):
    """Build the model.

    UNKNOWN details are inferred from the callable name and signature.

    :param b_data: Value for ``b_data``.
    :type b_data: :class:`_g_transition.Transition`
    :param branches: Value for ``branches``.
    :type branches: list['Branch']
    :param update_points: Value for ``update_points``.
    :type update_points: UNKNOWN
    :returns: Return value. UNKNOWN details.
    :rtype: UNKNOWN
    """
    model = None

    for branch in b_data.branches:
        branch_index = branch.idx
        brnch = branches[branch_index]

        branch_point = brnch.position
        set_dia = brnch.diameter

        if set_dia is None:
            set_dia = branch.min_dia
            brnch.diameter = set_dia

        max_dia = branch.max_dia
        length = branch.length
        bulb_len = branch.bulb_length
        angle = branch.angle
        bulb_offset = branch.bulb_offset
        offset = branch.offset

        if bulb_len:
            if bulb_offset.x or bulb_offset.y:
                pl = build123d.Plane(origin=bulb_offset.as_float, z_dir=(1, 0, 0)).rotated((0, 0, angle))
            else:
                pl = build123d.Plane(origin=offset.as_float, z_dir=(1, 0, 0)).rotated((0, 0, angle))

            bulb = pl * build123d.extrude(build123d.Circle(max_dia / 2.0), bulb_len)

            if model is None:
                model = bulb
            else:
                model += bulb

            if bulb_offset.x or bulb_offset.y:
                pl = build123d.Plane(origin=bulb_offset.as_float, z_dir=(1, 0, 0))

                sphere = pl * build123d.Sphere(max_dia / 2.0)

                model += sphere

                pl = build123d.Plane(origin=(bulb_offset.x - bulb_len, bulb_offset.y, 0),
                                     z_dir=(1, 0, 0))

                sphere = pl * build123d.Sphere(max_dia / 2.0)

                model += sphere
            else:
                r = math.radians(angle)
                pos = _point.Point(bulb_len * math.cos(r), bulb_len * math.sin(r), 0.0) + offset

                pl = build123d.Plane(origin=pos.as_float, z_dir=(1, 0, 0))

                sphere = pl * build123d.Sphere(max_dia / 2.0).rotate(
                    build123d.Axis(origin=(0, 0, 0), direction=(1, 0, 0)), angle)

                model += sphere

        pl = build123d.Plane(origin=offset.as_float, z_dir=(1, 0, 0)).rotated((0, 0, angle))

        brch = pl * build123d.extrude(build123d.Circle(set_dia / 2.0), length)

        if model is None:
            model = brch
        else:
            model += brch

        if branch_point.as_float == (0.0, 0.0, 0.0) or update_points:
            r = math.radians(float(angle))
            with branch_point:
                branch_point.x = length * math.cos(r)
                branch_point.y = length * math.sin(r)
                branch_point.z = 0.0
                branch_point += offset

    return model


class Transition(_base_3d.Base3D):
    """Represent a transition in :mod:`harness_designer.objects.objects_3d.transition`.

    UNKNOWN details are inferred from the class name and surrounding code.
    """
    parent: "_transition.Transition" = None
    db_obj: "_pjt_transition.PJTTransition" = None

    @_check_types.do
    def __init__(self, parent: "_transition.Transition",
                 db_obj: "_pjt_transition.PJTTransition"):
        """Initialise the :class:`Transition` instance.

        UNKNOWN details are inferred from the callable name and signature.

        :param parent: Parent object.
        :type parent: :class:`_transition.Transition`
        :param db_obj: Database-backed object.
        :type db_obj: :class:`_pjt_transition.PJTTransition`
        """

        self._part = db_obj.part
        position = db_obj.position3d
        angle = db_obj.angle3d
        color = self._part.color.ui
        inverse_angle = -angle

        material = _materials.Rubber(color)
        branch_count = self.branch_count = self._part.branch_count

        branch_points = []
        branch_diams = []
        branches = []

        if branch_count >= 1:
            branch = db_obj.branch1

            b_position = branch.position3d
            if b_position.as_float != (0.0, 0.0, 0.0):
                with b_position:
                    b_position -= position
                    b_position @= inverse_angle

            branches.append(Branch(parent, branch, branch.diameter, b_position))

        if branch_count >= 2:
            branch = db_obj.branch2

            b_position = branch.position3d
            if b_position.as_float != (0.0, 0.0, 0.0):
                with b_position:
                    b_position -= position
                    b_position @= inverse_angle

            branches.append(Branch(parent, branch, branch.diameter, b_position))

        if branch_count >= 3:
            branch = db_obj.branch3

            b_position = branch.position3d
            if b_position.as_float != (0.0, 0.0, 0.0):
                with b_position:
                    b_position -= position
                    b_position @= inverse_angle

            branches.append(Branch(parent, branch, branch.diameter, b_position))

        if branch_count >= 4:
            branch = db_obj.branch4

            b_position = branch.position3d
            if b_position.as_float != (0.0, 0.0, 0.0):
                with b_position:
                    b_position -= position
                    b_position @= inverse_angle

            branches.append(Branch(parent, branch, branch.diameter, b_position))

        if branch_count >= 5:
            branch = db_obj.branch5

            b_position = branch.position3d
            if b_position.as_float != (0.0, 0.0, 0.0):
                with b_position:
                    b_position -= position
                    b_position @= inverse_angle

            branches.append(Branch(parent, branch, branch.diameter, b_position))

        if branch_count >= 6:
            branch = db_obj.branch6

            b_position = branch.position3d
            if b_position.as_float != (0.0, 0.0, 0.0):
                with b_position:
                    b_position -= position
                    b_position @= inverse_angle

            branches.append(Branch(parent, branch, branch.diameter, b_position))

        self._model = _build_model(self._part, branches)

        self._vertices, self._faces = _utils.convert_model_to_mesh(self._model)

        for branch in branches:
            with branch.position:
                branch.position @= angle

            branch.position += position

        self._branches = branches
        self._branch_points = branch_points
        self._branch_diams = branch_diams

        scale = _point.Point(1.0, 1.0, 1.0)

        with parent.mainframe.editor3d.context:
            packed, count = _utils.compute_normals(self._vertices, self._faces)
            vbo = _vbo.NonPooledVBOHandler(packed, count)
            super().__init__(parent, db_obj, vbo, angle, 
                             db_obj.position3d, scale, material)

    @property
    @_check_types.do
    def smooth(self) -> bool:
        smooth = self.db_obj.smooth
        if smooth is None:
            smooth = Config.renderer.smooth_transitions

        return smooth

    @smooth.setter
    def smooth(self, value: bool | None):
        self._smooth = value

        try:
            self.db_obj.smooth = value
        except AttributeError:
            pass

    @_check_types.do
    def build(self):
        """Execute the build operation.

        UNKNOWN details are inferred from the callable name and signature.
        """
        inverse_angle = -self._angle

        for branch in self._branches:
            with branch.position:
                branch.position -= self._position
                branch.position @= inverse_angle

        self._model = _build_model(self._part, self._branches, update_points=True)

        for branch in self._branches:
            with branch.position:
                branch.position @= self._angle

            branch.position += self._position

        self._vertices, self._faces = _utils.convert_model_to_mesh(self._model)

        with self.editor3d.context:
            packed, count = _utils.compute_normals(self._vertices, self._faces)
            self._vbo.update(packed, count)
        self.editor3d.update()

    @_check_types.do
    def _update_angle(self, angle: _angle.Angle):
        """Update the angle.

        UNKNOWN details are inferred from the callable name and signature.

        :param angle: Value for ``angle``.
        :type angle: :class:`_angle.Angle`
        """
        delta = angle - self._o_angle
        for branch in self._branches:
            with branch.position:
                branch.position -= self._position
                branch.position @= delta

            branch.position += self._position

        super()._update_angle(angle)

    @_check_types.do
    def _update_position(self, position: _point.Point):
        """Update the position.

        UNKNOWN details are inferred from the callable name and signature.

        :param position: Position value.
        :type position: :class:`_point.Point`
        """
        delta = position - self._o_position

        for branch in self._branches:
            branch.position += delta

        super()._update_position(position)

    @_check_types.do
    def get_branch(self, point: _point.Point) -> int:
        """Return the branch.

        UNKNOWN details are inferred from the callable name and signature.

        :param point: Point value.
        :type point: :class:`_point.Point`
        :returns: Return value. UNKNOWN details.
        :rtype: int
        """
        for branch in self._branches:
            if branch.position.db_id == point.db_id:
                return branch

    @classmethod
    @_check_types.do
    def start_add(
        cls, mainframe: "_ui.MainFrame", part_id: bytes | None = None
    ) -> "_transition.Transition | None":
        """Bundle-snapping transition placement, ported from
        handlers.transition_handler.AddTransitionHandler -- always
        free/interactive (no housing/bundle argument, matching the
        original, which was only ever invoked from the toolbar).
        """
        from ...ui.dialogs import part_search as _part_search
        from ...ui.editor_db import transition as _trans_editor_page
        from ...add_handlers.editor_3d import transition as _add_transition
        from .. import transition as _transition_facade
        from PySide6.QtWidgets import QDialog

        canvas = mainframe.editor3d.editor

        if part_id is None:
            part_id = mainframe.editor_db.editor.transitions.GetSelection()

        if part_id is None:
            dlg = _part_search.SearchDialog(
                mainframe, _trans_editor_page.TransitionsPage, mainframe.global_db.transitions_table,
                'Add Transition')

            if dlg.exec() == QDialog.DialogCode.Accepted:
                part_id = dlg.GetValue()
            else:
                part_id = None

            dlg.deleteLater()

            if part_id is None:
                return None

        ptables = mainframe.project.ptables
        part = ptables.global_db.transitions_table[part_id]

        highlight_material = _materials.Plastic(
            _color.Color(*_config.Config.colors.add_object.bundle_highlight))

        # Preview: all branch points at the origin -- _build_model fires in
        # Transition.__init__ and positions them locally; hover repositions
        # and rebuilds the whole thing once a bundle is snapped.
        center_db = ptables.pjt_points3d_table.insert(0.0, 0.0, 0.0)
        init_angle = _angle.Angle()
        name = f'{part.manufacturer.name} {part.part_number}'

        transition_db = ptables.pjt_transitions_table.insert(
            part_id, name, center_db.db_id, init_angle)

        for branch_id in range(1, part.branch_count + 1):
            g_br = part.branches[branch_id - 1]
            pt_db = ptables.pjt_points3d_table.insert(0.0, 0.0, 0.0)
            ptables.pjt_transition_branches_table.insert(
                g_br.db_id, transition_db.db_id, pt_db.db_id, branch_id, float(g_br.min_dia))

        facade = _transition_facade.Transition(mainframe, transition_db)
        facade.obj3d.is_visible = False

        handler = _add_transition.Transition(canvas, facade, part_id, part, highlight_material)
        facade.obj3d._active_handler = handler  # NOQA
        canvas.active_handler_obj = facade.obj3d

        return facade

    @_check_types.do
    def handle_interaction(
        self, last_pos: _point.Point, current_pos: _point.Point, had_motion: bool,
        interaction_type: "_interaction.MouseInteraction", clicked_object
    ) -> bool:
        """Forwards to an active add-session (see start_add); falls back
        to Base3D's own generic drag/rotation handling otherwise.
        """
        from ...add_handlers.editor_3d import transition as _add_transition  # NOQA -- avoid a cycle at import time

        if isinstance(self._active_handler, _add_transition.Transition):
            handled = self._active_handler(
                last_pos, current_pos, had_motion, interaction_type, clicked_object)

            if self._active_handler.is_finished:
                self._active_handler = None

            return handled

        return super().handle_interaction(
            last_pos, current_pos, had_motion, interaction_type, clicked_object)

    @_check_types.do
    def get_context_menu(self):
        """Return the context menu.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Return value. UNKNOWN details.
        :rtype: UNKNOWN
        """
        return TransitionMenu(self.mainframe.editor3d.editor, self)


class Branch(_base_3d.Base3D):
    """Represent a branch in :mod:`harness_designer.objects.objects_3d.transition`.

    UNKNOWN details are inferred from the class name and surrounding code.
    """
    _parent: "_transition.Transition" = None
    db_obj: "_pjt_transition_branch.PJTTransitionBranch"

    @_check_types.do
    def __init__(self, parent: "_transition.Transition", db_obj: "_pjt_transition_branch.PJTTransitionBranch",
                 diameter: float, position: _point.Point):
        """Initialise the :class:`Branch` instance.

        UNKNOWN details are inferred from the callable name and signature.

        :param parent: Parent object.
        :type parent: :class:`_transition.Transition`
        :param db_obj: Database-backed object.
        :type db_obj: :class:`_pjt_transition_branch.PJTTransitionBranch`
        :param diameter: Value for ``diameter``.
        :type diameter: float
        :param position: Position value.
        :type position: :class:`_point.Point`
        """

        with parent.mainframe.editor3d.context:
            self._diameter = diameter

            vbo = _sphere.create_vbo()
            scale = _point.Point(diameter, diameter, diameter)
            angle = _angle.Angle()

            color = _color.Color(1.0, 0.3, 0.3, 1.0)
            material = _materials.Rubber(color)

            super().__init__(parent, db_obj, vbo, angle, position, scale, material)

        color = _color.Color(0.3, 1.0, 0.3, 1.0)
        self._selected_material = _materials.Rubber(color)

    @property
    @_check_types.do
    def diameter(self) -> float:
        """Return the diameter.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: float
        """
        return self._diameter

    @diameter.setter
    @_check_types.do
    def diameter(self, value: float):
        """Set the diameter.

        UNKNOWN details are inferred from the callable name and signature.

        :param value: Value to store or process.
        :type value: float
        """
        self._diameter = value
        self.db_obj.diameter = value
        self._parent.obj3d.build()

    @property
    @_check_types.do
    def min_diameter(self) -> float:
        """Return the min diameter.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: float
        """
        branch = self.db_obj.transition.part.branches[self.db_obj.branch_id]
        return branch.min_dia

    @property
    @_check_types.do
    def max_diameter(self) -> float:
        """Return the max diameter.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: float
        """
        branch = self.db_obj.transition.part.branches[self.db_obj.branch_id]
        return branch.max_dia


class TransitionMenu(QMenu):
    """Represent a transition menu in :mod:`harness_designer.objects.objects_3d.transition`.

    UNKNOWN details are inferred from the class name and surrounding code.
    """

    @_check_types.do
    def __init__(self, canvas, selected):
        """Initialise the :class:`TransitionMenu` instance.

        UNKNOWN details are inferred from the callable name and signature.

        :param canvas: Canvas instance.
        :type canvas: UNKNOWN
        :param selected: Value for ``selected``.
        :type selected: UNKNOWN
        """
        QMenu.__init__(self)
        self.canvas = canvas
        self.selected = selected

        rotate_menu = _context_menus.Rotate3DMenu(canvas, selected.parent)
        self.addMenu(rotate_menu)

        mirror_menu = _context_menus.Mirror3DMenu(canvas, selected.parent)
        self.addMenu(mirror_menu)

        self.addSeparator()
        action = self.addAction('Select')
        action.triggered.connect(self.on_select)

        action = self.addAction('Clone')
        action.triggered.connect(self.on_clone)

        action = self.addAction('Route Wires')
        action.triggered.connect(self.on_route_wires)

        self.addSeparator()
        action = self.addAction('Delete')
        action.triggered.connect(self.on_delete)

        self.addSeparator()
        action = self.addAction('Properties')
        action.triggered.connect(self.on_properties)

    @_check_types.do
    def on_select(self):
        """Make this transition the active selection."""
        _menu_ops.select_object(self.selected)

    @_check_types.do
    def on_clone(self):
        """Arm clone mode using this transition as the template."""
        _menu_ops.clone_object(self.selected)

    @_check_types.do
    def on_delete(self):
        """Delete this transition from the project."""
        _menu_ops.delete_object(self.selected)

    @_check_types.do
    def on_route_wires(self):
        """Open the wire routing dialog to reassign wires between output branches."""
        from ...ui.dialogs import transition_routing as _routing_dlg

        mainframe = self.selected.mainframe
        dlg = _routing_dlg.TransitionRoutingDialog(mainframe, self.selected)
        dlg.exec()
        dlg.deleteLater()

    @_check_types.do
    def on_properties(self):
        """Show this transition's properties in the object editor."""
        _menu_ops.show_properties(self.selected)
