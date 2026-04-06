from typing import TYPE_CHECKING

import wx

from ...ui.widgets import context_menus as _context_menus
from ...geometry import point as _point
from ...geometry import angle as _angle
from ...geometry.decimal import Decimal as _d
from ...ui.dialogs import housing_editor as _housing_editor
from ...ui.dialogs import pjt_add_seal as _pjt_add_seal
from ...ui.dialogs import pjt_add_terminal as _pjt_add_terminal
from ...ui.dialogs import pjt_add_cpa_lock as _pjt_add_cpa_lock
from ...ui.dialogs import pjt_add_tpa_lock as _pjt_add_tpa_lock
from ...ui.dialogs import pjt_add_cover as _pjt_add_cover
from ...ui.dialogs import pjt_add_boot as _pjt_add_boot

from . import base3d as _base3d
from ...shapes import box as _box
from ...gl import vbo as _vbo
from ...gl import materials as _materials
from ... import config as _config
from ... import utils as _utils


if TYPE_CHECKING:
    from ...database.project_db import pjt_housing as _pjt_housing
    from .. import housing as _housing
    from ... import ui as _ui


Config = _config.Config.editor3d


class Housing(_base3d.Base3D):
    parent: "_housing.Housing" = None
    db_obj: "_pjt_housing.PJTHousing" = None

    def __init__(self, parent: "_housing.Housing",
                 db_obj: "_pjt_housing.PJTHousing"):

        self._part = db_obj.part

        angle = db_obj.angle3d
        color = self._part.color.ui
        material = _materials.Plastic(color)

        model = self._part.model3d

        if model is not None:
            uuid = model.uuid
            scale = _point.Point(1.0, 1.0, 1.0)

            if uuid in _vbo.VBOHandler:
                vbo = _vbo.VBOHandler(uuid)
            else:
                vertices, faces = model.load()

                if Config.renderer.smooth_housings:
                    verts, nrmls, faces, count = _utils.compute_vbo_smoothed_vertex_normals(vertices, faces)
                else:
                    verts, nrmls, faces, count = _utils.compute_vbo_vertex_normals(vertices, faces)

                vbo = _vbo.VBOHandler(uuid, verts, nrmls, faces, count)
        else:
            vbo = _box.create_vbo()
            scale = self._part.scale

        _base3d.Base3D.__init__(self, parent, db_obj, vbo, angle, db_obj.position3d, scale, material)

    def get_context_menu(self):
        return HousingMenu(self.mainframe, self)


class HousingMenu(wx.Menu):

    def __init__(self, mainframe: "_ui.MainFrame", obj: Housing):
        wx.Menu.__init__(self)
        self.mainframe = mainframe
        self.canvas = mainframe.editor3d.editor
        self.obj = obj

        item = self.Append(wx.ID_ANY, 'Add Seal')
        self.canvas.Bind(wx.EVT_MENU, self.on_add_seal, id=item.GetId())

        item = self.Append(wx.ID_ANY, 'Add Terminal')
        self.canvas.Bind(wx.EVT_MENU, self.on_add_terminal, id=item.GetId())

        item = self.Append(wx.ID_ANY, 'Add CPA Lock')
        self.canvas.Bind(wx.EVT_MENU, self.on_add_cpa_lock, id=item.GetId())

        item = self.Append(wx.ID_ANY, 'Add TPA Lock')
        self.canvas.Bind(wx.EVT_MENU, self.on_add_tpa_lock, id=item.GetId())

        item = self.Append(wx.ID_ANY, 'Add Cover')
        self.canvas.Bind(wx.EVT_MENU, self.on_add_cover, id=item.GetId())

        item = self.Append(wx.ID_ANY, 'Add Boot')
        self.canvas.Bind(wx.EVT_MENU, self.on_add_boot, id=item.GetId())

        self.AppendSeparator()

        rotate_menu = _context_menus.Rotate3DMenu(self.canvas, obj)
        self.AppendSubMenu(rotate_menu, 'Rotate')

        mirror_menu = _context_menus.Mirror3DMenu(self.canvas, obj)
        self.AppendSubMenu(mirror_menu, 'Mirror')

        self.AppendSeparator()
        item = self.Append(wx.ID_ANY, 'Select')
        self.canvas.Bind(wx.EVT_MENU, self.on_select, id=item.GetId())

        item = self.Append(wx.ID_ANY, 'Clone')
        self.canvas.Bind(wx.EVT_MENU, self.on_clone, id=item.GetId())

        self.AppendSeparator()
        item = self.Append(wx.ID_ANY, 'Delete')
        self.canvas.Bind(wx.EVT_MENU, self.on_delete, id=item.GetId())

        self.AppendSeparator()
        item = self.Append(wx.ID_ANY, 'Properties')
        self.canvas.Bind(wx.EVT_MENU, self.on_properties, id=item.GetId())

        item = self.Append(wx.ID_ANY, 'Housing Editor')
        self.canvas.Bind(wx.EVT_MENU, self.on_housing_editor, id=item.GetId())

    def on_housing_editor(self, evt: wx.MenuEvent):

        def _do(housing):
            dlg = _housing_editor.HousingEditorDialog(self.mainframe, housing)
            dlg.ShowModal()
            dlg.Destroy()

        wx.CallAfter(_do, self.selected.db_obj.part)

        evt.Skip()

    def on_add_seal(self, evt: wx.MenuEvent):

        def _do(housing: "_pjt_housing.PJTHousing"):
            dlg = _pjt_add_seal.AddSealDialog(self.mainframe, housing)
            if dlg.ShowModal() == wx.ID_OK:
                part_id, db_id = dlg.GetValue()
                obj_type = dlg.GetObjectType()

                if obj_type == _pjt_add_seal.CAVITY:
                    self.mainframe.project.add_seal(part_id, cavity_id=db_id)
                elif obj_type == _pjt_add_seal.TERMINAL:
                    self.mainframe.project.add_seal(part_id, terminal_id=db_id)
                elif obj_type == _pjt_add_seal.HOUSING:
                    self.mainframe.project.add_seal(part_id, housing_id=db_id)
                else:
                    raise RuntimeError('sanity check')

            dlg.Destroy()

        wx.CallAfter(_do, self.obj.db_obj)
        evt.Skip()

    def on_add_terminal(self, evt: wx.MenuEvent):
        def _do(housing: "_pjt_housing.PJTHousing"):
            dlg = _pjt_add_terminal.AddTerminalDialog(self.mainframe, housing)

            if dlg.ShowModal() == wx.ID_OK:
                part_id, db_id = dlg.GetValue()
                self.mainframe.project.add_terminal(part_id, cavity_id=db_id)

            dlg.Destroy()

        wx.CallAfter(_do, self.obj.db_obj)
        evt.Skip()

    def on_add_cpa_lock(self, evt: wx.MenuEvent):

        def _do(housing: "_pjt_housing.PJTHousing"):
            dlg = _pjt_add_cpa_lock.AddCPALockDialog(self.mainframe, housing)

            if dlg.ShowModal() == wx.ID_OK:
                part_id = dlg.GetValue()
                self.mainframe.project.add_cpa_lock(part_id, housing_id=housing.db_id)

            dlg.Destroy()

        wx.CallAfter(_do, self.obj.db_obj)
        evt.Skip()

    def on_add_tpa_lock(self, evt: wx.MenuEvent):
        def _do(housing: "_pjt_housing.PJTHousing"):
            dlg = _pjt_add_tpa_lock.AddTPALockDialog(self.mainframe, housing)

            if dlg.ShowModal() == wx.ID_OK:
                part_id, idx = dlg.GetValue()
                self.mainframe.project.add_tpa_lock(part_id, idx=idx, housing_id=housing.db_id)

            dlg.Destroy()

        wx.CallAfter(_do, self.obj.db_obj)
        evt.Skip()

    def on_add_cover(self, evt: wx.MenuEvent):
        def _do(housing: "_pjt_housing.PJTHousing"):
            dlg = _pjt_add_cover.AddCoverDialog(self.mainframe, housing)

            if dlg.ShowModal() == wx.ID_OK:
                part_id = dlg.GetValue()
                self.mainframe.project.add_cover(part_id, housing_id=housing.db_id)

            dlg.Destroy()

        wx.CallAfter(_do, self.obj.db_obj)
        evt.Skip()

    def on_add_boot(self, evt: wx.MenuEvent):
        def _do(housing: "_pjt_housing.PJTHousing"):
            dlg = _pjt_add_boot.AddBootDialog(self.mainframe, housing)

            if dlg.ShowModal() == wx.ID_OK:
                part_id = dlg.GetValue()
                self.mainframe.project.add_boot(part_id, housing_id=housing.db_id)

            dlg.Destroy()

        wx.CallAfter(_do, self.obj.db_obj)
        evt.Skip()

    def on_select(self, evt: wx.MenuEvent):
        selected = self.mainframe.get_selected()

        if selected is not None:
            selected.set_selected(False)

        self.obj.set_selected(True)

        evt.Skip()

    def on_clone(self, evt: wx.MenuEvent):
        self.mainframe.editor3d.SetCursor(wx.CURSOR_BULLSEYE)
        self.mainframe.set_clone_obj(self.obj.parent)

        evt.Skip()

    def on_delete(self, evt: wx.MenuEvent):
        self.obj.delete()

        evt.Skip()

    def on_properties(self, evt: wx.MenuEvent):
        evt.Skip()
