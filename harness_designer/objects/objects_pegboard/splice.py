# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

from typing import TYPE_CHECKING

import math

from . import base_pegboard as _base_pegboard
from ...geometry import point as _point
from ...geometry import angle as _angle
from ...shapes import cylinder as _cylinder
from ...gl import materials as _materials
from ... import check_types as _check_types
from ... import config as _config


if TYPE_CHECKING:
    from ...database.project_db import pjt_splice as _pjt_splice
    from .. import splice as _splice


Config = _config.Config.editor_pegboard


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
            dia = wire.od_mm
            area = math.pi * ((dia / 2.0) ** 2.0)
            area1.append(area)

        for wire in wires[-1]:
            dia = wire.od_mm
            area = math.pi * ((dia / 2.0) ** 2.0)
            area2.append(area)

        area1 = sum(area1)
        area2 = sum(area2)

        if area1:
            dia1 = 2.0 * math.sqrt(area1 / math.pi)
        else:
            dia1 = 0.0

        if area2:
            dia2 = 2.0 * math.sqrt(area2 / math.pi)
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

            super().__init__(
                parent, db_obj,
                vbo=vbo,
                angle=angle,
                position=self._p1,
                scale=scale,
                material=_materials.Rubber(self._part.color.ui),
            )

        # Identity key for gl.canvas_pegboard's bundle-graph matching --
        # keyed by this splice's own peg-board start point, not its 3D
        # one (see housing.py's own comment on why).
        self.point3d_id = db_obj.start_position_pegboard_id

        if self._model is not None:
            self._model.load(
                self._part.manufacturer.name, self._part.part_number, self._set_model)

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
    def smooth(self, value: bool | None):
        self._smooth = value

        try:
            self.db_obj.smooth = value
        except AttributeError:
            pass
