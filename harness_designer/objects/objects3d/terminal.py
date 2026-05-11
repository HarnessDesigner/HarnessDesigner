# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

from typing import TYPE_CHECKING

from PySide6.QtWidgets import QMenu

from ...ui.widgets import context_menus as _context_menus
from ...geometry import point as _point
from ...geometry import angle as _angle
from . import base3d as _base3d
from ...shapes import cylinder as _cylinder
from ...shapes import box as _box
from ...gl import vbo as _vbo
from ...gl import materials as _materials
from ... import config as _config
from ... import utils as _utils


if TYPE_CHECKING:
    from ...database.project_db import pjt_terminal as _pjt_terminal
    from .. import terminal as _terminal


Config = _config.Config.editor3d


class Terminal(_base3d.Base3D):
    parent: "_terminal.Terminal" = None
    db_obj: "_pjt_terminal.PJTTerminal" = None

    def __init__(self, parent: "_terminal.Terminal",
                 db_obj: "_pjt_terminal.PJTTerminal"):

        self._part = db_obj.part

        symbol = self._part.plating.symbol

        if symbol.startswith('Sn'):
            color = 'Tin'
        elif symbol.startswith('Cu'):
            color = 'Copper'
        elif symbol.startswith('Al'):
            color = 'Aluminum'
        elif symbol.startswith('Ti'):
            color = 'Titanium'
        elif symbol.startswith('Zn'):
            color = 'Zinc'
        elif symbol.startswith('Au'):
            color = 'Gold'
        elif symbol.startswith('Ag'):
            color = 'Silver'
        elif symbol.startswith('Ni'):
            color = 'Nickel'
        else:
            color = 'Tin'

        color = db_obj.table.db.global_db.colors_table[color]
        self._color = color.ui
        material = _materials.Polished(color.ui)

        angle = db_obj.angle3d

        model = self._part.model3d
        if model is not None:
            uuid = model.uuid
            scale = _point.Point(1.0, 1.0, 1.0)

            if uuid in _vbo.VBOHandler:
                vbo = _vbo.VBOHandler(uuid)
            else:
                vertices, faces = model.load()

                if Config.renderer.smooth_terminals:
                    verts, nrmls, faces, count = _utils.compute_vbo_smoothed_vertex_normals(vertices, faces)
                else:
                    verts, nrmls, faces, count = _utils.compute_vbo_vertex_normals(vertices, faces)

                vbo = _vbo.VBOHandler(uuid, verts, nrmls, faces, count)
        else:
            is_round = self._part.round_terminal
            scale = self._part.scale

            if is_round:
                vbo = _cylinder.create_vbo()
            else:
                vbo = _box.create_vbo()

        _base3d.Base3D.__init__(self, parent, db_obj, vbo, angle, db_obj.position3d, scale, material)

    def _update_position(self, position: _point.Point):
        seal = self.db_obj.seal
        if seal is not None:
            delta = position - self._o_position
            t_position = seal.position3d
            t_position += delta

        _base3d.Base3D._update_position(self, position)

    def _update_angle(self, angle: _angle.Angle):
        seal = self.db_obj.seal
        if seal is not None:
            delta = angle - self._o_angle
            t_angle = seal.angle3d
            t_angle += delta

        _base3d.Base3D._update_angle(self, angle)

    @property
    def seal_position(self) -> _point.Point:
        return self.wire_position

    @property
    def wire_position(self) -> _point.Point:
        return self.db_obj.wire_position3d

    def get_context_menu(self):
        return TerminalMenu(self.mainframe.editor3d.editor, self)


class TerminalMenu(QMenu):

    def __init__(self, canvas, selected):
        QMenu.__init__(self)
        self.canvas = canvas
        self.selected = selected

        action = self.addAction('Add Wire')
        action.triggered.connect(self.on_add_wire)

        action = self.addAction('Add Wire Service Loop')
        action.triggered.connect(self.on_add_wire_service_loop)

        action = self.addAction('Add Seal')
        action.triggered.connect(self.on_add_seal)

        self.addSeparator()

        rotate_menu = _context_menus.Rotate3DMenu(canvas, selected)
        self.addMenu(rotate_menu)

        mirror_menu = _context_menus.Mirror3DMenu(canvas, selected)
        self.addMenu(mirror_menu)

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

    def on_add_wire(self):
        pass

    def on_add_wire_service_loop(self):
        pass

    def on_add_seal(self):
        pass

    def on_trace_circuit(self):
        pass

    def on_select(self):
        pass

    def on_clone(self):
        pass

    def on_delete(self):
        pass

    def on_properties(self):
        pass
