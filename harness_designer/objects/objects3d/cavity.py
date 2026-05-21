# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

from typing import TYPE_CHECKING

from PySide6.QtWidgets import QMenu

from . import base3d as _base3d
from ...ui.widgets import context_menus as _context_menus
from ...shapes import cylinder as _cylinder
from ...shapes import box as _box
from ...gl import materials as _materials
from ...geometry import point as _point
from ...geometry import angle as _angle
from ... import color as _color


if TYPE_CHECKING:
    from ...database.project_db import pjt_cavity as _pjt_cavity
    from .. import cavity as _cavity


class Cavity(_base3d.Base3D):
    parent: "_cavity.Cavity" = None
    db_obj: "_pjt_cavity.PJTCavity" = None

    def get_context_menu(self):
        return CavityMenu(self.mainframe.editor3d.editor, self)

    def __init__(self, parent: "_cavity.Cavity",
                 db_obj: "_pjt_cavity.PJTCavity"):

        parent.mainframe.editor3d.context.acquire()
        self._part = db_obj.part
        scale = db_obj.part.scale
        angle = db_obj.part.angle3d
        position = db_obj.position3d
        material = _materials.Metallic(_color.Color(200, 200, 200, 75))

        if db_obj.part.round_terminal:
            vbo = _cylinder.create_vbo()
        else:
            vbo = _box.create_vbo()

        vbo.acquire()
        _base3d.Base3D.__init__(self, parent, db_obj, vbo, angle, position, scale, material)
        parent.mainframe.editor3d.context.release()

    def _update_position(self, position: _point.Point):
        terminal = self.db_obj.terminal
        if terminal is not None:
            delta = position - self._o_position
            t_position = terminal.position3d
            t_position += delta

        _base3d.Base3D._update_position(self, position)

    def _update_angle(self, angle: _angle.Angle):
        terminal = self.db_obj.terminal
        if terminal is not None:
            delta = angle - self._o_angle
            t_angle = terminal.angle3d
            t_angle += delta

        _base3d.Base3D._update_angle(self, angle)

    @property
    def seal_position(self) -> _point.Point:
        return self.db_obj.position3d


class CavityMenu(QMenu):
    def __init__(self, editor, obj):
        QMenu.__init__(self)

        pass
