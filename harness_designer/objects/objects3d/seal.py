from typing import TYPE_CHECKING

import wx
import build123d

from ...ui.widgets import context_menus as _context_menus
from ...geometry import point as _point
from . import base3d as _base3d
from ...shapes import cylinder as _cylinder
from ...shapes import box as _box
from ...gl import vbo as _vbo
from ...gl import materials as _materials
from ... import config as _config
from ... import utils as _utils


if TYPE_CHECKING:
    from ...database.project_db import pjt_seal as _pjt_seal
    from .. import seal as _seal


Config = _config.Config.editor3d


def _build_sws(length, o_dia, i_dia):
    o_radius = round(o_dia / 2.0, 6)
    i_radius = round(i_dia / 2.0, 6)
    i_length = round(length * 1.10, 6)
    move_dist = round((i_length - length) / 2.0, 6)

    model = build123d.Cylinder(o_radius, length)
    hole = build123d.Cylinder(i_radius, i_length)
    hole = hole.move(build123d.Location())
    hole.position -= (0.0, 0.0, -move_dist)
    model -= hole

    vertices, faces = _utils.convert_model_to_mesh(model)
    return vertices, faces


class Seal(_base3d.Base3D):
    _parent: "_seal.Seal" = None
    db_obj: "_pjt_seal.PJTSeal"

    def __init__(self, parent: "_seal.Seal", db_obj: "_pjt_seal.PJTSeal"):
        self._part = db_obj.part

        color = self._part.color.ui
        material = _materials.Rubber(color)
        angle = db_obj.angle3d

        model = self._part.model3d
        if model is not None:
            uuid = model.uuid
            scale = _point.Point(1.0, 1.0, 1.0)

            if uuid in _vbo.VBOHandler:
                vbo = _vbo.VBOHandler(uuid)
            else:
                vertices, faces = model.load()

                if Config.renderer.smooth_covers:
                    verts, nrmls, faces, count = _utils.compute_vbo_smoothed_vertex_normals(vertices, faces)
                else:
                    verts, nrmls, faces, count = _utils.compute_vbo_vertex_normals(vertices, faces)

                vbo = _vbo.VBOHandler(uuid, verts, nrmls, faces, count)
        else:
            type_ = self._part.type
            scale = self._part.scale

            if type_.lower() in ('sws', 'single wire seal'):
                vbo_id = self._part.manufacturer.name
                vbo_id += ':' + self._part.part_number

                if vbo_id in _vbo.VBOHandler:
                    vbo = _vbo.VBOHandler(vbo_id)
                else:
                    length = self._part.length
                    o_dia = self._part.o_dia
                    i_dia = self._part.i_dia
                    vertices, faces = _build_sws(length, o_dia, i_dia)

                    if Config.renderer.smooth_seals:
                        vertices, normals, faces, count = _utils.compute_vbo_smoothed_vertex_normals(vertices, faces)
                    else:
                        vertices, normals, faces, count = _utils.compute_vbo_vertex_normals(vertices, faces)

                    vbo = _vbo.VBOHandler(vbo_id, vertices, normals, faces, count)
            elif type_.lower() == 'plug':
                vbo = _cylinder.create_vbo
            else:
                vbo = _box.create_vbo()

        _base3d.Base3D.__init__(self, parent, db_obj, vbo, angle, db_obj.position3d, scale, material)

    def get_context_menu(self):
        return SealMenu(self.mainframe.editor3d.editor, self)


class SealMenu(wx.Menu):

    def __init__(self, canvas, selected):
        wx.Menu.__init__(self)
        self.canvas = canvas
        self.selected = selected

        rotate_menu = _context_menus.Rotate3DMenu(canvas, selected)
        self.AppendSubMenu(rotate_menu, 'Rotate')

        mirror_menu = _context_menus.Mirror3DMenu(canvas, selected)
        self.AppendSubMenu(mirror_menu, 'Mirror')

        self.AppendSeparator()
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

    def on_select(self, evt: wx.MenuEvent):
        evt.Skip()

    def on_clone(self, evt: wx.MenuEvent):
        evt.Skip()

    def on_delete(self, evt: wx.MenuEvent):
        evt.Skip()

    def on_properties(self, evt: wx.MenuEvent):
        evt.Skip()
