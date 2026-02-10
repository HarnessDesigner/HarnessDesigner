from typing import TYPE_CHECKING
import weakref

import wx
import build123d

from ...widgets.context_menus import RotateMenu, MirrorMenu
from ...geometry import point as _point
from ...geometry import angle as _angle
from ...wrappers.decimal import Decimal as _decimal
from . import base3d as _base3d
from .mixins import angle as _angle_mixin
from .mixins import move as _move_mixin
from ... import Config
from ... import gl_materials as _gl_materials


if TYPE_CHECKING:
    from ...database.project_db import pjt_terminal as _pjt_terminal
    from .. import terminal as _terminal


Config = Config.editor3d


def _build_model(length: _decimal, width: _decimal, height: _decimal, blade_size: _decimal, gender: str):
    if gender == 'Female':
        model = build123d.Box(float(length), float(width), float(height))
    else:

        wire_end = length * _decimal(0.66)
        connection_end = length * _decimal(0.33)

        model = build123d.Box(float(wire_end), float(width), float(height))

        blade_height = height * _decimal(0.1)

        x = (width - blade_size) / _decimal(2.0)
        y = (height - blade_height) / _decimal(2.0)
        z = connection_end

        box = build123d.Box(float(connection_end), float(blade_size), float(blade_height))
        box.move(build123d.Location((float(x), float(y), float(z))))
        model += box

    bbox = model.bounding_box()
    corner1 = _point.Point(*(_decimal(float(item)) for item in bbox.min))
    corner2 = _point.Point(*(_decimal(float(item)) for item in bbox.max))

    return model, [corner1, corner2]


class Terminal(_base3d.Base3D, _angle_mixin.AngleMixin, _move_mixin.MoveMixin):
    _parent: "_terminal.Terminal" = None

    def __init__(self, parent: "_terminal.Terminal",
                 db_obj: "_pjt_terminal.PJTTerminal"):

        _base3d.Base3D.__init__(self, parent)
        _angle_mixin.AngleMixin.__init__(self)
        _move_mixin.MoveMixin.__init__(self)
        self._db_obj: "_pjt_terminal.PJTTerminal" = db_obj

        self._part = db_obj.part

        self._position = db_obj.point3d.point
        self._o_position = self._position.copy()
        self._angle = db_obj.angle3d
        self._o_angle = self._angle.copy()

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

        color = self._db_obj.table.db.global_db.colors_table[color]
        self._color = color.ui
        self._material = _gl_materials.Polished(color.ui.rgba_scalar)

        self._position.bind(self._update_position)
        self._angle.bind(self._update_angle)

        model = self._part.model3d

        triangles = []

        if model is None:
            self._model = None
        else:
            self._model = model.model
            for verts, faces in self._model:
                tris, nrmls, count = self._get_triangles(verts, faces)
                tris @= self._angle
                nrmls @= self._angle
                tris += self._position

                p1, p2 = self._compute_rect(tris)
                # self._adjust_hit_points(p1, p2)
                bb = self._compute_bb(p1, p2)

                self._rect.append([p1, p2])
                self._bb.append(bb)
                triangles.append([tris, nrmls, count])

        self._triangles = [_base3d.TriangleRenderer(triangles, self._material)]

    def _get_triangles(self, vertices, faces):
        if Config.modeling.smooth_terminals:
            return self._compute_smoothed_vertex_normals(vertices, faces)
        else:
            return self._compute_vertex_normals(vertices, faces)



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

        rotate_menu = RotateMenu(canvas, selected)

        self.AppendSubMenu(rotate_menu, 'Rotate')

        mirror_menu = MirrorMenu(canvas, selected)
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
