from typing import TYPE_CHECKING
import weakref

import wx
import build123d

from ...geometry import point as _point
from ...geometry import angle as _angle
from ...ui.widgets import context_menus as _context_menus
from . import base3d as _base3d
from ...gl import materials as _materials
from ... import utils as _utils


if TYPE_CHECKING:
    from ...database.project_db import pjt_note as _pjt_note
    from .. import note as _note


font_style_mapping = {
    'Normal': build123d.FontStyle.REGULAR,
    'Bold': build123d.FontStyle.BOLD,
    'Bold Italic': build123d.FontStyle.BOLDITALIC,
    'Italic': build123d.FontStyle.ITALIC
}

#
# build123d.LEFT
# build123d.CENTER
# build123d.RIGHT
#
# build123d.BOTTOM
# build123d.CENTER
# build123d.TOP
# build123d.TOPFIRSTLINE
#


class Note(_base3d.Base3D):
    _parent: "_note.Note" = None
    db_obj: "_pjt_note.PJTNote"

    def __init__(self, parent: "_note.Note", db_obj: "_pjt_note.PJTNote"):
        self.db_obj = db_obj
        self.angle = db_obj.angle3d
        self.position = db_obj.position3d
        color = db_obj.color.ui
        scale = _point.Point(0.0, 0.0, 0.0)
        data = self._build()

        material = _materials.Plastic(color)
        # db_obj.h_align3d
        # db_obj.v_align3d

        _base3d.Base3D.__init__(self, parent, db_obj, None, self.angle,
                                self.position, scale, material, data)

    def _build(self):
        model = build123d.Text(self.db_obj.note, font_size=self.db_obj.size3d, font_style=self.db_obj.style3d)
        model = build123d.extrude(model, 0.25)
        vertices, faces = _utils.convert_model_to_mesh(model)
        vertices, normals, count = _utils.compute_vertex_normals(vertices, faces)

        vertices @= self.angle
        normals @= self.angle
        vertices += self.position

        return vertices, normals, count

    def get_context_menu(self):
        return NoteMenu(self.mainframe.editor3d.editor, self)


class NoteMenu(wx.Menu):

    def __init__(self, canvas, selected):
        wx.Menu.__init__(self)
        self.canvas = canvas
        self.selected = selected

        rotate_menu = _context_menus.Rotate3DMenu(canvas, selected)
        self.AppendSubMenu(rotate_menu, 'Rotate')

        mirror_menu = _context_menus.Mirror3DMenu(canvas, selected)
        self.AppendSubMenu(mirror_menu, 'Mirror')

        item = self.Append(wx.ID_ANY, 'Set Text')
        canvas.Bind(wx.EVT_MENU, self.on_set_text, id=item.GetId())

        self.AppendSeparator()

        item = self.Append(wx.ID_ANY, 'Clone')
        canvas.Bind(wx.EVT_MENU, self.on_clone, id=item.GetId())

        self.AppendSeparator()
        item = self.Append(wx.ID_ANY, 'Delete')
        canvas.Bind(wx.EVT_MENU, self.on_delete, id=item.GetId())

        self.AppendSeparator()
        item = self.Append(wx.ID_ANY, 'Properties')
        canvas.Bind(wx.EVT_MENU, self.on_properties, id=item.GetId())

    def on_set_text(self, evt: wx.MenuEvent):
        evt.Skip()

    def on_clone(self, evt: wx.MenuEvent):
        evt.Skip()

    def on_delete(self, evt: wx.MenuEvent):
        evt.Skip()

    def on_properties(self, evt: wx.MenuEvent):
        evt.Skip()
