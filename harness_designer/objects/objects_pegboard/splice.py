# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

from typing import TYPE_CHECKING

import math

from OpenGL import GL

from . import base_pegboard as _base_pegboard
from ..objects_3d import splice as _splice_3d
from ...shapes import sleeve as _sleeve
from ...geometry import point as _point
from ...geometry import angle as _angle
from ...shapes import cylinder as _cylinder
from ...gl import materials as _materials
from ... import color as _color
from ... import check_types as _check_types
from ... import config as _config
from ...crash_dump import Attr, capturable


if TYPE_CHECKING:
    from ...database.project_db import pjt_splice as _pjt_splice
    from ...gl import shaders as _shaders
    from .. import splice as _splice


Config = _config.Config.editor_pegboard


@capturable()
class Splice(_base_pegboard.BasePegboard):
    """
    Peg Board Editor representation of a splice -- mirrors
    ``objects_3d.splice.Splice`` exactly: one fixed-length cylinder
    (``part.length``, from the catalog part, never derived from the
    distance between the two points below) whose position/angle are
    computed once from its own two independent, draggable peg-board
    points (``start_position_pegboard``/``stop_position_pegboard`` --
    the peg-board mirrors of ``start_position3d``/``stop_position3d``),
    with diameter derived live from whichever wires are actually
    attached at each end (``db_obj.wires``), same as 3D.

    Previously rendered as a single freely-rotatable anchor at
    ``start_position_pegboard`` alone (TODO from 2026-09-02) --
    ``stop_position_pegboard``/``branch_position_pegboard`` are real
    columns (``StartStopPositionPegboardMixin``/``branch_position_pegboard``
    on ``PJTSplice``) that were never read or seeded anywhere. This wires
    them up the same way the 3D view already uses
    ``start_position3d``/``stop_position3d``/``branch_position3d``.
    """

    __dump_schema__ = (
        Attr('_part', severity=2),
        Attr('_model', severity=2),
        Attr('_p2', severity=2),
    )

    db_obj: "_pjt_splice.PJTSplice"

    @_check_types.do
    def __init__(self, parent: "_splice.Splice",
                 db_obj: "_pjt_splice.PJTSplice"):
        """Initialise the :class:`Splice` instance.

        :param parent: Parent object.
        :type parent: :class:`_splice.Splice`
        :param db_obj: Database-backed object.
        :type db_obj: :class:`_pjt_splice.PJTSplice`
        """
        self._part = db_obj.part
        self._model = self._part.model3d

        self._p1 = db_obj.start_position_pegboard
        self._p2 = db_obj.stop_position_pegboard

        # Seed both peg-board endpoints from their 3D counterparts' own
        # X/Z -- only the very first time ever (identity/(0.0, 0.0) is
        # the fresh-row default), same sentinel convention housing.py/
        # terminal.py use. From then on these are normal user-adjustable
        # peg-board points, independent of position3d.
        if self._p1.x == 0.0 and self._p1.z == 0.0:
            pos3d = db_obj.start_position3d
            self._p1.x = float(pos3d.x)
            self._p1.z = float(pos3d.z)

        if self._p2.x == 0.0 and self._p2.z == 0.0:
            pos3d = db_obj.stop_position3d
            self._p2.x = float(pos3d.x)
            self._p2.z = float(pos3d.z)

        angle = _angle.Angle.from_points(self._p1, self._p2)

        length = self._part.length
        wires = db_obj.wires

        area1 = [0.0]
        area2 = [0.0]

        for wire in wires[0]:
            dia = float(wire.part.od_mm or 0.0)
            area = math.pi * ((dia / 2.0) ** 2.0)
            area1.append(area)

        for wire in wires[-1]:
            dia = float(wire.part.od_mm or 0.0)
            area = math.pi * ((dia / 2.0) ** 2.0)
            area2.append(area)

        area1_total = sum(area1)
        area2_total = sum(area2)

        if area1_total:
            dia1 = 2.0 * math.sqrt(area1_total / math.pi)
        else:
            dia1 = 0.0

        if area2_total:
            dia2 = 2.0 * math.sqrt(area2_total / math.pi)
        else:
            dia2 = 0.0

        if dia2 > dia1:
            dia = dia2
        else:
            dia = dia1

        scale = _point.Point(dia, dia, length)

        # Placeholder-then-real-model lifecycle, same as Base3D itself
        # (objects.objects_3d.splice.Splice.__init__): a unit cylinder,
        # scaled to the splice's own real diameter/length -- never
        # vbo=None (see housing.py's own comment on this).
        with parent.mainframe.editor_pegboard.context:
            vbo = _cylinder.create_vbo()
            material = _materials.Rubber(self._part.color.ui)

            # A solder sleeve (SHIELD_SLEEVE_DESIGN.md) is the hollow, translucent tube of ``shapes/sleeve.py`` with the solder ring
            # inside its wall, scaled by the diameter of the cable it is on, as in the 3D view; the wires on it (a pigtail) are not
            # what gives it its size (user, 2026-11-12: the sleeve was not drawn on the board at all).
            self._ring_vbo = None
            self._ring_material = None
            self._ring_shape = None
            self._ring_key = None
            self._ring_position = _point.Point(0.0, 0.0, 0.0)

            if self._part.is_solder_sleeve:
                on_cable = db_obj.shield_cable
                cable_od = on_cable[0].part.od_mm if on_cable is not None else 0.0

                self._ring_shape = shape = _sleeve.sizes(cable_od, self._part.min_dia, self._part.max_dia, self._part.length)
                scale = _point.Point(shape['diameter'], shape['diameter'], shape['length'])
                vbo = _sleeve.create_vbo()
                material = _splice_3d.sleeve_tube_material(self._part)

                self._ring_vbo = _cylinder.create_vbo()
                self._ring_material = _materials.Metallic(_color.Color(*_splice_3d._RING_COLOR))  # NOQA

            super().__init__(
                parent, db_obj,
                vbo=vbo,
                angle=angle,
                position=self._p1,
                scale=scale,
                material=material,
            )

        # Identity key for gl.canvas_pegboard's bundle-graph matching --
        # keyed by this splice's own peg-board start point, not its 3D
        # one (see housing.py's own comment on why).
        self.point3d_id = db_obj.start_position_pegboard_id

        if self._model is not None:
            self._model.load(
                self._part.manufacturer.name, self._part.part_number, self._set_model)

    @_check_types.do
    def reload_pose(self) -> None:
        """Turn the splice to lie from its start point to its stop point again. The angle is worked out once, when the view is made; a
        solder sleeve whose cable moved on the board has its points moved (``Cable._sync_board_sleeve``) and turns here."""
        angle = _angle.Angle.from_points(self._p1, self._p2)

        # in place: the view is bound to this angle object (its bound callback turns the boxes); the difference is added so the
        # rotation is exactly the one from_points gives (setting the x / y / z of an angle made from points does not)
        self._angle += angle - self._angle

        self._ring_key = None

    @_check_types.do
    def render(self, shaders: "_shaders.ShaderProgram") -> None:
        """Draw the splice. A solder sleeve is drawn as in the 3D view (``objects_3d.splice.Splice.render``): its solder ring first, then
        the translucent tube over it without writing depth.

        :param shaders: The canvas's shader programs.
        """
        if self._ring_vbo is None or not self.is_visible or self._vbo is not _sleeve.create_vbo():
            super().render(shaders)
            return

        self._render_ring(shaders)

        if self.is_selected:
            super().render(shaders)
            return

        GL.glDepthMask(GL.GL_FALSE)

        try:
            super().render(shaders)
        finally:
            GL.glDepthMask(GL.GL_TRUE)

    @_check_types.do
    def _render_ring(self, shaders: "_shaders.ShaderProgram") -> None:
        """Draw the solder ring of a sleeve, inside the wall of the tube, centred on it along its axis."""
        start = self._p1.as_numpy
        stop = self._p2.as_numpy
        key = (tuple(start), tuple(stop))

        if key != self._ring_key:
            axis = stop - start
            norm = float(math.sqrt(float((axis * axis).sum())))

            if norm < 1e-9:
                return

            at = start + axis / norm * self._ring_shape['ring_offset']
            self._ring_position = _point.Point(float(at[0]), float(at[1]), float(at[2]))
            self._ring_key = key

        shape = self._ring_shape
        ring_scale = _point.Point(shape['ring_diameter'], shape['ring_diameter'], shape['ring_length'])
        angle = self._ring_vbo.render_angle(self._angle)

        with shaders.faces:
            self._ring_material.set(shaders.faces)
            self._ring_vbo.render(shaders.faces, self._ring_position, angle, ring_scale, self.smooth)

    @property
    @_check_types.do
    def start_position(self) -> _point.Point:
        """Wire start position (peg-board mirror of ``start_position3d``)."""
        return self._p1

    @property
    @_check_types.do
    def stop_position(self) -> _point.Point:
        """Wire stop position (peg-board mirror of ``stop_position3d``)."""
        return self._p2

    @property
    @_check_types.do
    def wire_position(self) -> _point.Point:
        """Branch/third-wire attach point -- peg-board mirror of
        ``objects_3d.splice.Splice.wire_position``.
        """
        return self.branch_position

    @property
    @_check_types.do
    def branch_position(self) -> _point.Point:
        """Branch/third-wire attach point (peg-board mirror of
        ``branch_position3d``).
        """
        return self.db_obj.branch_position_pegboard

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
