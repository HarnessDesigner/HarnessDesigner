from typing import TYPE_CHECKING

import wx

from . import mixinbase as _mixinbase
from ...widgets import text_ctrl as _text_ctrl
from ...widgets import combobox_ctrl as _combobox_ctrl


if TYPE_CHECKING:
    from ....database.global_db.mixins import adhesive as _adhesive


class AhesiveMixin(_mixinbase.MixinBase):
    db_obj: "_adhesive.AdhesiveMixin" = None

    def __init__(self, db_obj: "_adhesive.AdhesiveMixin"):
        self.db_obj = db_obj
        _mixinbase.MixinBase.__init__(self)

        fold_panel = self.AddFoldPanel('Ashesive', collapsed=True)

        panel = wx.Panel(fold_panel, wx.ID_ANY, style=wx.BORDER_NONE)
        vsizer = wx.BoxSizer(wx.VERTICAL)

        self._adhesive_panels = []

        for adhesive in db_obj.adhesives:
            sz = wx.StaticBoxSizer(wx.VERTICAL, panel, adhesive.code)
            sb = sz.GetStaticBox()

            '''
            db_obj._table.execute('SELECT id, code, description, accessory_part_nums FROM adhesives;')
            rows = db_obj._table.fetchall()
            self._accessories = sorted([row for row in rows], key=lambda x: x[1])
            '''


            '''
            self.adhesive_code_ctrl = _combobox_ctrl.ComboBoxCtrl(panel, 'Code:', [item[1] for item in self._accessories])
            self.adhesive_description_ctrl = _text_ctrl.TextCtrl(panel, 'Description:', (-1, -1), wx.TE_MULTILINE)
            self.adhesive_accessories_ctrl = _text_ctrl.TextCtrl(panel, 'Accessory Parts:', (-1, -1))
            '''


            # adhesive.code
            accessory_pns = [accessory.part_number for accessory in adhesive.accessories]



#
#
# code
# description
# accessory_part_nums


