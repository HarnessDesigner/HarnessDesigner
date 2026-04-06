from typing import TYPE_CHECKING, Union

import wx
from . import mixinbase as _mixinbase
from ...widgets import text_ctrl as _text_ctrl

from ...dialogs import add_model_db as _add_model_db


if TYPE_CHECKING:
    from ....database.global_db.mixins import model3d as _model3d


class PartMixin(_mixinbase.MixinBase):

    def __init__(self, panel, db_obj: "_model3d.Model3DMixin"):

        self._model3d_obj = db_obj
        _mixinbase.MixinBase.__init__(self)

        vsizer = panel.GetSizer()

        self.model3d = _text_ctrl.TextCtrl(
            panel, '3d Model:', (-1, -1))

        self.model3d.Bind(wx.EVT_BUTTON, self._on_model3d)

        model3d_id = db_obj.model3d_id
        if model3d_id:
            model3d = db_obj.table.db.models3d_table[model3d_id]
            self.model3d.SetValue(model3d.path)

        vsizer.Add(self.model3d, 1, wx.EXPAND)

    def _on_model3d(self, evt):
        path = self.model3d.GetValue().strip()
        if path:
            _add_model3d_db.AddModelDialog(self, )

            model3d = self._model3d_obj.table.db.models3d_table.insert(path)
            self._model3d_obj.model3d_id = model3d.db_id
            evt.Skip()
        else:
            self._model3d_obj.model3d_id = None
