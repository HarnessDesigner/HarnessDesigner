from typing import TYPE_CHECKING

import wx

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
    _parent: "_terminal.Terminal" = None
    db_obj: "_pjt_terminal.PJTTerminal"

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

    def get_context_menu(self):
        return TerminalMenu(self.mainframe.editor3d.editor, self)


class TerminalMenu(wx.Menu):

    def __init__(self, canvas, selected):
        wx.Menu.__init__(self)
        self.canvas = canvas
        self.selected = selected

        item = self.Append(wx.ID_ANY, 'Add Wire')
        canvas.Bind(wx.EVT_MENU, self.on_add_wire, id=item.GetId())

        item = self.Append(wx.ID_ANY, 'Add Wire Service Loop')
        canvas.Bind(wx.EVT_MENU, self.on_add_wire_service_loop, id=item.GetId())

        item = self.Append(wx.ID_ANY, 'Add Seal')
        canvas.Bind(wx.EVT_MENU, self.on_add_seal, id=item.GetId())

        self.AppendSeparator()

        rotate_menu = _context_menus.Rotate3DMenu(canvas, selected)
        self.AppendSubMenu(rotate_menu, 'Rotate')

        mirror_menu = _context_menus.Mirror3DMenu(canvas, selected)
        self.AppendSubMenu(mirror_menu, 'Mirror')

        self.AppendSeparator()
        item = self.Append(wx.ID_ANY, 'Trace Circuit')
        canvas.Bind(wx.EVT_MENU, self.on_trace_circuit, id=item.GetId())

        item = self.Append(wx.ID_ANY, 'Select')
        canvas.Bind(wx.EVT_MENU, self.on_select, id=item.GetId())

        item = self.Append(wx.ID_ANY, 'Clone')
        canvas.Bind(wx.EVT_MENU, self.on_clone, id=item.GetId())

        self.AppendSeparator()
        item = self.Append(wx.ID_ANY, 'Delete')
        canvas.Bind(wx.EVT_MENU, self.on_delete, id=item.GetId())

        self.AppendSeparator()
        item = self.Append(wx.ID_ANY, 'Properties')
        canvas.Bind(wx.EVT_MENU, self.on_properties, id=item.GetId())

    def on_add_wire(self, evt: wx.MenuEvent):
        evt.Skip()

    def on_add_wire_service_loop(self, evt: wx.MenuEvent):
        evt.Skip()

    def on_add_seal(self, evt: wx.MenuEvent):
        evt.Skip()

    def on_trace_circuit(self, evt: wx.MenuEvent):
        evt.Skip()

    def on_select(self, evt: wx.MenuEvent):
        evt.Skip()

    def on_clone(self, evt: wx.MenuEvent):
        evt.Skip()

    def on_delete(self, evt: wx.MenuEvent):
        evt.Skip()

    def on_properties(self, evt: wx.MenuEvent):
        evt.Skip()
