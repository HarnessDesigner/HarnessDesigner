# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

from typing import TYPE_CHECKING, Union as _Union


from PySide6 import QtWidgets

from . import base_schematic as _base_schematic
from ...geometry import angle as _angle
from ...geometry import point as _point
from ...gl.canvas_base import interaction as _interaction
from ... import config as _config
from ... import color as _color
from ...gl import materials as _materials
import numpy as np

from ... import utils as _utils
from ...shapes import sphere as _sphere
from ...shapes import taper as _taper
from ...shapes import cylinder as _cylinder
from ...geometry import line as _line
from ... import check_types as _check_types
from ... import bounds as _bounds


if TYPE_CHECKING:
    from ...ui.editor_schematic import editor_schematic as _editor_schematic
    from ...gl import shaders as _shaders
    from .. import ObjectBase as _ObjectBase
    from ...database.project_db import pjt_splice as _pjt_splice
    from .. import splice as _splice
    from .. import wire as _wire_facade
    from ... import ui as _ui


Config = _config.Config.editor_schematic

# A solder sleeve that finishes a cable's shield (the pigtail is the shield's connection) is shown in the schematic the way a shield is drawn on
# a schematic: a DASHED ELLIPSE across the shielded wires, with the shield wire connected to one of its narrow ends (user, 2026-11-12). Nothing
# else of the sleeve is drawn (no dot): the ring's state is stored on the sleeve's row (see ``wire_routing/shield_ring.py``), the connected narrow
# end is the sleeve's own point, and the user changes the ring only by its two narrow ends: dragging the connected one moves the ring (it is then
# hard set there), dragging the other one makes the ring longer or shorter (and wider or narrower, 1:3).
SHIELD_DASHES = 36              # dashes round the ellipse
SHIELD_DASH_FRACTION = 0.55     # how much of each period is drawn
SHIELD_DASH_THICKNESS = _taper.END_RATIO   # a dash's thickness as a part of a wire's (user, 2026-11-12: 0.7 was too thick); the shield wire ends as thin
SHIELD_OVER_GAP = 0.05          # how far (mm) the dashes that go over the wires clear them
HANDLE_FACTOR = 1.5             # how near (in splice diameters) a click has to be to a narrow end to take it


def _rings():
    """The ``wire_routing.shield_ring`` module (imported when used: it imports the router, which imports this view's objects)."""
    from ...wire_routing import shield_ring as _shield_ring

    return _shield_ring


class _RingDrag:
    """The drag of one narrow end of a shield ring: the connected end (``index`` 0) moves the ring, the far end (1) sizes it."""

    def __init__(self, view: "Splice", index: int):
        self._view = view
        self._index = index
        self._project = view.parent.mainframe.project

        # one gesture for the whole drag, as every drag does (WRITE_DESIGN.md section 4.12)
        self._project.begin_gesture()

    def __call__(self, delta: _point.Point, mouse_pos: _point.Point) -> None:  # NOQA
        view = self._view
        editor = view.editor2d.editor
        world = editor.camera.screen_to_world(mouse_pos)
        place = (float(world.x), float(world.z))

        with editor.context:
            if self._index == 0:
                _rings().move_ring(self._project, view.parent, place)
            else:
                _rings().resize_ring(self._project, view.parent, place)

    def delete(self) -> None:
        self._project.end_gesture()


class Splice(_base_schematic.BaseSchematic):
    """
    2D representation of a splice for schematic view

    Renders as the same shared ``shapes/sphere.py`` mesh -- the
    ``schematic2d`` shader already does the full 3D lighting/transform
    before projecting to 2D, so a real sphere (rather than a flat disc)
    costs nothing extra and shades correctly -- on the VBO/shader
    pipeline (see ``objects_schematic/base_schematic.py``'s ``BaseSchematic``), matching how
    ``Base3D`` subclasses render.
    """
    _parent: "_splice.Splice"
    db_obj: "_pjt_splice.PJTSplice"
    _bounds_tag = _bounds.TAG_OBSTACLE

    @_check_types.do
    def __init__(self, parent: "_splice.Splice",
                 db_obj: "_pjt_splice.PJTSplice"):
        """Initialise the :class:`Splice` instance.

        :param parent: Parent object.
        :type parent: :class:`_splice.Splice`
        :param db_obj: Database-backed object.
        :type db_obj: :class:`_pjt_splice.PJTSplice`
        """
        position = db_obj.position2d

        # PJTSplice has Position2DMixin but no angle2d mixin -- a sphere
        # is rotationally symmetric so the value never matters visually,
        # but BaseVar._compute_obb/_compute_aabb both bail out entirely
        # when self._angle is None, which would leave this splice
        # permanently unpickable. A static, unbound identity Angle (not
        # DB-backed -- there's no column to bind to) gives that math a
        # real rotation to use -- same fix objects_schematic/wire_layout.py's
        # WireLayout already uses for the same reason.
        angle = _angle.Angle.from_euler(0.0, 0.0, 0.0)

        diameter = Config.object_sizes.splice.diameter
        scale = _point.Point(diameter, diameter, diameter)
        material = _materials.Generic(_color.Color(*Config.colors.splice))

        part = db_obj.part
        self._is_shield = part is not None and part.is_solder_sleeve

        # the ring of a shield (see render): its stored state, and the dashes worked out from it
        self._ring = _rings().ring_of(db_obj) if self._is_shield else None
        self._ring_key = None
        self._ring_pieces = []
        self._dash_material = _materials.Generic(_color.Color(*Config.colors.label))

        with parent.mainframe.editor2d.editor.context:
            vbo = _sphere.create_vbo()
            super().__init__(parent, db_obj, vbo, angle, position, scale, material)

    @property
    def is_shield(self) -> bool:
        """Whether this splice is a solder sleeve that finishes a cable's shield (drawn as a dashed ring across the shielded wires)."""
        return self._is_shield

    @_check_types.do
    def reload_ring(self) -> None:
        """Read the ring's stored state again (it was placed, moved or sized) and redo its bounds, which the router reads as an obstacle."""
        self._ring = _rings().ring_of(self.db_obj) if self._is_shield else None
        self._ring_key = None

        self._compute_obb()
        self._compute_aabb()

        self.editor2d.Refresh()

    @_check_types.do
    def _compute_obb(self) -> None:
        """The box of the ring (a thin box over the whole ellipse); the sphere's of an ordinary splice."""
        if self._ring is None:
            super()._compute_obb()
            return

        rect = _rings().ring_rect(self._ring)
        corners = _utils.compute_obb(_point.Point(rect[0], -0.1, rect[1]), _point.Point(rect[2], 0.1, rect[3]))

        if self._obb is None:
            self._obb = self._obb_manager.read(self._obb_index)

        self._obb[:] = corners

    @_check_types.do
    def _compute_aabb(self) -> None:
        """See :meth:`_compute_obb`."""
        if self._ring is None:
            super()._compute_aabb()
            return

        rect = _rings().ring_rect(self._ring)
        self._aabb[0] = (rect[0], -0.1, rect[1])
        self._aabb[1] = (rect[2], 0.1, rect[3])

    @_check_types.do
    def _update_position(self, position: _point.Point) -> None:
        """The sleeve's point is the ring's connected end: the ring moves with it."""
        super()._update_position(position)

        if self._is_shield and self._ring is not None:
            self.reload_ring()

    @_check_types.do
    def _tip_at(self, x: float, z: float) -> int | None:
        """Which narrow end of the ring (0 the connected one, 1 the far one) the schematic point ``(x, z)`` is on; ``None`` for neither."""
        if self._ring is None:
            return None

        radius = HANDLE_FACTOR * float(Config.object_sizes.splice.diameter)

        for index, tip in enumerate((self._ring.tip, self._ring.far)):
            if float(np.hypot(x - tip[0], z - tip[1])) <= radius:
                return index

        return None

    @_check_types.do
    def _ray_hits_tip(self, ray_origin: np.ndarray, ray_direction: np.ndarray) -> bool:
        """Whether a ray from the (top-down) camera reaches the schematic plane (y = 0) on a narrow end of the ring."""
        if abs(float(ray_direction[1])) < 1e-9:
            return False

        t = -float(ray_origin[1]) / float(ray_direction[1])
        x = float(ray_origin[0]) + t * float(ray_direction[0])
        z = float(ray_origin[2]) + t * float(ray_direction[2])

        return self._tip_at(x, z) is not None

    @_check_types.do
    def hit_test_step2(self, ray_origin: np.ndarray, ray_direction: np.ndarray) -> bool:
        """A ring is picked on its narrow ends only (the wires and everything else inside its box are not hidden by it)."""
        if self._ring is None:
            return super().hit_test_step2(ray_origin, ray_direction)

        return self._ray_hits_tip(ray_origin, ray_direction)

    @_check_types.do
    def hit_test_step3(self, ray_origin: np.ndarray, ray_dir: np.ndarray) -> bool:
        """See :meth:`hit_test_step2`."""
        if self._ring is None:
            return super().hit_test_step3(ray_origin, ray_dir)

        return self._ray_hits_tip(ray_origin, ray_dir)

    @_check_types.do
    def _pieces(self) -> list[tuple]:
        """The dashes of the ring, each as ``(start, angle, scale)`` in the world; worked out again only when the ring changed."""
        ring = self._ring
        key = (round(ring.center[0], 3), round(ring.center[1], 3), ring.u, round(ring.a, 3))

        if key == self._ring_key:
            return self._ring_pieces

        cx, cz = ring.center
        ux, uz = ring.u
        vx, vz = -uz, ux
        a, b = ring.a, ring.b
        wire = float(Config.object_sizes.wire.diameter)
        thickness = wire * SHIELD_DASH_THICKNESS
        period = 2.0 * np.pi / SHIELD_DASHES
        pieces = []

        # The ring goes AROUND the wires (user, 2026-11-12): the half of it on the far side of the wires from the housing is over them (raised
        # clear of the wires: drawn on top), the half on the housing's side is under them (on the plane of the wires, which cover it where they cross).
        side = _rings().beyond_sign(self.parent)
        over_y = wire / 2.0 + thickness / 2.0 + SHIELD_OVER_GAP

        def at(angle: float) -> _point.Point:
            return _point.Point(cx + ux * a * np.cos(angle) + vx * b * np.sin(angle), 0.0,
                                cz + uz * a * np.cos(angle) + vz * b * np.sin(angle))

        for index in range(SHIELD_DASHES):
            first = index * period
            flat = at(first)
            line = _line.Line(flat, at(first + period * SHIELD_DASH_FRACTION))
            length = line.length()

            if length > 1e-6:
                over = float(np.sin(first + period * SHIELD_DASH_FRACTION / 2.0)) * side > 0.0
                start = _point.Point(flat.x, over_y if over else 0.0, flat.z)
                pieces.append((start, line.get_angle(flat), _point.Point(thickness, thickness, length)))

        self._ring_pieces = pieces
        self._ring_key = key

        return pieces

    @_check_types.do
    def render(self, shaders: "_shaders.ShaderProgram") -> None:
        """An ordinary splice is its sphere. A solder sleeve is drawn as the dashed ring only (no dot): the shield wire ends on its connected
        narrow end."""
        if not self._is_shield:
            super().render(shaders)
            return

        if not self.is_visible or self._position is None or self._ring is None:
            return

        # the picker only considers what was marked this frame
        self._aabb_manager.mark_visible(self._aabb_index)
        self._obb_manager.mark_visible(self._obb_index)

        real = (self._vbo, self._angle, self._scale, self._position, self._material)
        self._vbo = _cylinder.create_vbo()
        self._material = self._dash_material

        try:
            for start, angle, scale in self._pieces():
                self._angle = angle
                self._scale = scale
                self._position = start
                super().render(shaders)
        finally:
            self._vbo, self._angle, self._scale, self._position, self._material = real

    @property
    @_check_types.do
    def smooth(self) -> bool:
        smooth = self.db_obj.smooth
        if smooth is None:
            smooth = Config.renderer.smooth_splices

        return smooth

    @smooth.setter
    @_check_types.do
    def smooth(self, value: bool | None) -> None:
        self._smooth = value

        try:
            self.db_obj.smooth = value
        except AttributeError:
            pass

    @classmethod
    @_check_types.do
    def start_add(
        cls, mainframe: "_ui.MainFrame", wire: _Union["_wire_facade.Wire", None] = None
    ) -> _Union["_splice.Splice", None]:
        """Wire-snapping splice placement, schematic-native -- see
        add_handlers.editor_schematic.splice's own module docstring for
        how the cut position is derived. Mirrors
        objects_3d.splice.Splice.start_add's own two-entry-mode shape
        (given *wire* locks immediately; otherwise waits for the first
        hover over a compatible wire).
        """
        from ...handlers import splice_handler as _splice_handler
        from ...ui.dialogs import part_search as _part_search
        from ...ui import editor_db as _editor_db
        from ...add_handlers.editor_schematic import splice as _add_splice
        from .. import splice as _splice_facade

        canvas = mainframe.editor2d.editor

        part_id = mainframe.editor_db.editor.splices.GetSelection()

        if part_id is None:
            dlg = _part_search.SearchDialog(
                mainframe, _editor_db.SplicesPage, mainframe.global_db.splices_table,
                'Add Splice')

            if dlg.exec() == QtWidgets.QDialog.DialogCode.Accepted:
                part_id = dlg.GetValue()
            else:
                part_id = None

            dlg.deleteLater()

            if part_id is None:
                return None

        ptables = mainframe.project.ptables
        part = ptables.global_db.splices_table[part_id]

        preview_material = _materials.Generic(
            _color.Color(*_config.Config.colors.add_object.preview_color))
        compat_material = _materials.Generic(
            _color.Color(*_config.Config.colors.add_object.wire_highlight))

        for w in mainframe.project.wires:
            if _splice_handler._wire_fits(part, w):  # NOQA
                w.identify(compat_material)

        half = float(part.length) / 2.0
        start_db = ptables.pjt_points3d_table.insert(0.0, 0.0, -half)
        stop_db = ptables.pjt_points3d_table.insert(0.0, 0.0, half)
        branch_db = ptables.pjt_points3d_table.insert(0.0, 0.0, 0.0)
        point2d_db = ptables.pjt_points2d_table.insert(0.0, 0.0, 0.0)

        name = f'{part.manufacturer.name} {part.part_number}'

        db_obj = ptables.pjt_splices_table.insert(
            part_id, name, start_db.db_id, stop_db.db_id, branch_db.db_id,
            point2d_db.db_id, None)

        facade = _splice_facade.Splice(mainframe, db_obj)
        facade.identify(preview_material)
        facade.objschematic.is_visible = False

        handler = _add_splice.Splice(
            canvas, facade, part_id, part, preview_material, compat_material)

        facade.objschematic._active_handler = handler  # NOQA
        canvas.active_handler_obj = facade.objschematic

        if wire is not None and _splice_handler._wire_fits(part, wire):  # NOQA
            handler._recreate_preview(wire)  # NOQA
            facade = handler.target

        return facade

    @_check_types.do
    def handle_interaction(
        self, last_pos: _point.Point, current_pos: _point.Point, had_motion: bool,
        interaction_type: _interaction.MouseInteraction, clicked_object: _Union["_ObjectBase", None]
    ) -> bool:
        """Forwards to an active add-session (see start_add); falls back
        to BaseSchematic's own generic drag handling otherwise.
        """
        from ...add_handlers.editor_schematic import splice as _add_splice  # NOQA -- avoid a cycle at import time

        if isinstance(self._active_handler, _add_splice.Splice):
            # A local reference, not another read of self._active_handler
            # below -- a CANCEL can delete this object's own facade,
            # whose generic delete() sees self._active_handler is this
            # same handler and clears it right there, before this call
            # even returns (see objects_3d.wire.Wire.handle_interaction).
            handler = self._active_handler
            handled = handler(
                last_pos, current_pos, had_motion, interaction_type, clicked_object)

            if handler.is_finished and self._active_handler is handler:
                self._active_handler = None

            return handled

        # a shield ring: a press on one of its narrow ends (when it is selected) starts the drag of that end
        if (
            self._is_shield and self._ring is not None and self._active_handler is None and
            interaction_type is _interaction.MouseInteraction.LEFT_DOWN and
            clicked_object is self.parent and self.parent.mainframe.get_selected() is self.parent and self.can_drag()
        ):
            world = self.editor2d.editor.camera.screen_to_world(current_pos)
            index = self._tip_at(float(world.x), float(world.z))

            if index is not None:
                self._active_handler = _RingDrag(self, index)
                return True

        return super().handle_interaction(
            last_pos, current_pos, had_motion, interaction_type, clicked_object)


class SpliceMenu(QtWidgets.QMenu):
    """Represent a splice menu in :mod:`harness_designer.objects.objects_schematic.splice`.

    UNKNOWN details are inferred from the class name and surrounding code.
    """

    @_check_types.do
    def __init__(self, canvas: "_editor_schematic.EditorSchematicPanel", selected: "Splice"):
        """Initialise the :class:`SpliceMenu` instance.

        UNKNOWN details are inferred from the callable name and signature.

        :param canvas: Canvas instance.
        :type canvas: UNKNOWN
        :param selected: Value for ``selected``.
        :type selected: UNKNOWN
        """
        QtWidgets.QMenu.__init__(self)
        self.canvas = canvas
        self.selected = selected

        action = self.addAction('Add Wire')
        action.triggered.connect(self.on_add_wire)

        self.addSeparator()
        action = self.addAction('Trace Circuit')
        action.triggered.connect(self.on_trace_circuit)

        action = self.addAction('Select')
        action.triggered.connect(self.on_select)

        action = self.addAction('Clone')
        action.triggered.connect(self.on_clone)

        self.addSeparator()
        action = self.addAction('Delete')
        action.triggered.connect(self.on_delete)

        self.addSeparator()
        action = self.addAction('Properties')
        action.triggered.connect(self.on_properties)

    @_check_types.do
    def on_add_wire(self) -> None:
        """Handle the add wire event.

        UNKNOWN details are inferred from the callable name and signature.
        """
        pass

    @_check_types.do
    def on_trace_circuit(self) -> None:
        """Handle the trace circuit event.

        UNKNOWN details are inferred from the callable name and signature.
        """
        pass

    @_check_types.do
    def on_select(self) -> None:
        """Handle the select event.

        UNKNOWN details are inferred from the callable name and signature.
        """
        pass

    @_check_types.do
    def on_clone(self) -> None:
        """Handle the clone event.

        UNKNOWN details are inferred from the callable name and signature.
        """
        pass

    @_check_types.do
    def on_delete(self) -> None:
        """Handle the delete event.

        UNKNOWN details are inferred from the callable name and signature.
        """
        pass

    @_check_types.do
    def on_properties(self) -> None:
        """Handle the properties event.

        UNKNOWN details are inferred from the callable name and signature.
        """
        pass
