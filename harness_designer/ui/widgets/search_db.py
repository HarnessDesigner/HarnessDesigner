from typing import TYPE_CHECKING, Union

import wx

from wx.lib import scrolledpanel, newevent
from ... import config as _config
from ...gl import canvas3d
from ...objects.objects3d import base3d as _base3d
from ... import objects as _objects
from ...gl import materials as _materials
from ...geometry import angle as _angle
from ...geometry import point as _point
from ... import utils as _utils

if TYPE_CHECKING:
    from ...database import global_db as _global_db
    from ...database import project_db as _project_db


SearchChangedEvent, EVT_SEARCH_CHANGED_EVENT = newevent.NewEvent()
SearchChangedCommandEvent, EVT_SEARCH_CHANGED_COMMAND_EVENT = newevent.NewCommandEvent()


class _Item(wx.BoxSizer):

    def __init__(self, st, ctrl):
        wx.BoxSizer.__init__(self, wx.HORIZONTAL)

        self.st = st
        self.ctrl = ctrl
        self.Add(st, 0, wx.ALL, 5)
        self.Add(ctrl, 0, wx.ALL, 5)

    def GetValue(self):
        return self.ctrl.GetValue()

    def GetName(self):
        return self.st.GetLabel()


class _ItemsPanel(scrolledpanel.ScrolledPanel):
    def __init__(self, parent, choices):
        scrolledpanel.ScrolledPanel.__init__(self, parent, wx.ID_ANY, style=wx.BORDER_SUNKEN)

        vsizer = wx.BoxSizer(wx.VERTICAL)

        self.items = []

        def _HSizer(label, ctrl):
            st = wx.StaticText(self, wx.ID_ANY, label=label)
            sizer = _Item(st, ctrl)
            self.items.append(sizer)
            return sizer

        for choice in choices:
            checkbox = wx.CheckBox(self, wx.ID_ANY)
            vsizer.Add(_HSizer(choice, checkbox), 1, wx.EXPAND)

        self.SetupScrolling(scroll_x=False)

        hsizer = wx.BoxSizer(wx.HORIZONTAL)
        hsizer.Add(vsizer, 1, wx.EXPAND)
        self.SetSizer(hsizer)

    def Reset(self):
        for item in self.items:
            item.ctrl.SetValue(False)

    def GetValues(self):
        res = []

        for item in self.items:
            if item.GetValue():
                res.append(item)

        return res


class _SearchPanelField(wx.Panel):

    def __init__(self, parent, label, params, types):
        wx.Panel.__init__(self, parent, wx.ID_ANY, style=wx.BORDER_SUNKEN)
        self.parent = parent
        self.params = params
        self.types = types
        self.values = self.parent.db_table.get_unique(*self.params)

        if len(types) == 1:
            choices = [str(value[0]) for value in self.values]
        else:
            choices = [str(value[1]) for value in self.values]

        vsizer = wx.BoxSizer(wx.VERTICAL)

        st = wx.StaticText(self, wx.ID_ANY, label=label)
        vsizer.Add(st, 1, wx.ALL | wx.ALIGN_CENTER, 5)

        self.items_panel = _ItemsPanel(self, choices)
        vsizer.Add(self.items_panel, 1, wx.ALL | wx.EXPAND, 5)

        self.reset_button = wx.Button(self, wx.ID_RESET, size=(40, -1))

        self.reset_button.Bind(wx.EVT_BUTTON, self.on_reset)

        vsizer.Add(self.reset_button, 1, wx.ALL | wx.ALIGN_RIGHT, 10)

        hsizer = wx.BoxSizer(wx.HORIZONTAL)
        hsizer.Add(vsizer, 1, wx.EXPAND)
        self.SetSizer(hsizer)

    def on_reset(self, evt):
        evt.Skip()
        self.items_panel.Reset()

    def GetValues(self):
        values = self.items_panel.GetValues()

        res = []
        if len(self.types) == 1:
            type_ = self.types[0]

            for value in values:
                value = type_(value.GetName())

                res.append(value)
        else:
            type_ = self.types[1]

            for value in values:
                value = type_(value.GetName())
                for row in self.values:
                    if row[1] == value:
                        res.append(row[0])
                        break
        if res:
            return {self.params[0]: res}

        return {}


class _SearchPanel(scrolledpanel.ScrolledPanel):

    def __init__(self, parent, db_table: Union["_global_db.TableBase", "_project_db.PJTTableBase"]):
        scrolledpanel.ScrolledPanel.__init__(self, parent, wx.ID_ANY)
        self.parent = parent
        self.db_table = db_table

        self.SetupScrolling(scroll_y=False)
        self.search_items = self.db_table.search_items

        self.fields = []
        self.columns = []
        self._search_all_parts = False
        self._compat_parts = ()

        hsizer = wx.BoxSizer(wx.HORIZONTAL)

        for key in sorted(list(self.search_items.keys())):
            value = self.search_items[key]

            self.columns.append(value['label'])
            if 'search_params' in value:
                field = _SearchPanelField(self, value['label'], value['search_params'], value['type'])
                self.fields.append(field)

                hsizer.Add(field, 1, wx.EXPAND)

                field.Bind(wx.EVT_CHECKBOX, self.on_update)
                field.Bind(wx.EVT_BUTTON, self.on_update)

        self.SetSizer(hsizer)

    def SetSearchAllParts(self, flag):
        self._search_all_parts = flag

    def SetCompatParts(self, *compat_parts):
        self._compat_parts = compat_parts

    def load(self):
        self.on_update()

    def on_update(self, evt=None):
        if evt is not None:
            evt.Skip()

        cmd = {}
        for field in self.fields:
            cmd.update(field.GetValues())

        if self._search_all_parts:
            con, results = self.db_table.search(self.search_items, **cmd)
        else:
            con, results = self.db_table.search(self.search_items, *self._compat_parts, **cmd)

        self.parent.SetResults(con, results)


class SearchPanel(wx.Panel):

    def __init__(self, parent, table, *compat_parts):
        wx.Panel.__init__(self, parent, wx.ID_ANY, style=wx.BORDER_NONE)

        self.parent = parent
        self.table = table
        self._object = None
        self.search_panel = _SearchPanel(self, table)
        self.result_ctrl = _ResultCtrl(self, self.search_panel.columns)
        self.image_ctrl = wx.StaticBitmap(self, wx.ID_ANY, size=(600, 480))
        self._search_all_parts = wx.CheckBox(self, wx.ID_ANY, label='Search All Parts')
        self._search_all_parts.Bind(wx.EVT_CHECKBOX, self._on_search_all_parts)

        if not compat_parts:
            self._search_all_parts.SetValue(True)
            self._search_all_parts.Enable(False)

            self.search_panel.SetSearchAllParts(True)
        else:
            self.search_panel.SetCompatParts(*compat_parts)
            self.search_panel.SetSearchAllParts(False)

        hsizer = wx.BoxSizer(wx.HORIZONTAL)
        vsizer = wx.BoxSizer(wx.VERTICAL)

        vsizer.Add(self.search_panel, 1, wx.EXPAND | wx.ALL, 10)
        vsizer.Add(self._search_all_parts, 1, wx.EXPAND | wx.LEFT | wx.RIGHT, 10)
        vsizer.Add(self.result_ctrl, 1, wx.EXPAND | wx.ALL, 10)

        hsizer.Add(vsizer, 1, wx.EXPAND)

        vsizer = wx.BoxSizer(wx.VERTICAL)
        vsizer.Add(self.image_ctrl, 1, wx.EXPAND | wx.ALL, 10)
        hsizer.Add(vsizer, 1, wx.EXPAND)

        self.SetSizer(hsizer)
        self.search_panel.load()

    def _on_search_all_parts(self, evt):
        self.search_panel.SetSearchAllParts(self._search_all_parts.GetValue())
        self.search_panel.load()
        evt.Skip()

    def set_image(self, image):
        if image is None:
            image = wx.Bitmap(250, 250)
        else:
            image = wx.Bitmap(image.data_path)

        self.image_ctrl.SetBitmap(image)

    def SetResults(self, con, results):
        self.result_ctrl.SetValues(con, results)

    def GetValue(self):
        return self.result_ctrl.GetValue()


class _ResultCtrl(wx.ListCtrl):

    def __init__(self, parent, columns):
        wx.ListCtrl.__init__(self, parent, style=wx.LC_REPORT | wx.LC_VIRTUAL | wx.LC_SINGLE_SEL | wx.LC_HRULES)
        self.parent = parent
        self._selected_db_id = None

        self._loaded_results = []
        self.results = None
        self.con = None

        for column in columns:
            width = self.GetTextExtent(column)[0]

            self.AppendColumn(column, width=width)

        self.Bind(wx.EVT_LIST_ITEM_SELECTED, self.on_item_selected)
        self.Bind(wx.EVT_LIST_ITEM_ACTIVATED, self.on_item_activated)

    def GetValue(self):
        return self._selected_db_id

    def on_item_selected(self, evt: wx.ListEvent):
        item = evt.GetItem()
        item_id = item.GetId()
        db_id = self._loaded_results[item_id][0]

        self._selected_db_id = db_id
        obj = self.parent.table[db_id]

        image = obj.image
        self.parent.set_image(image)

        evt.Skip()

    def on_item_activated(self, evt: wx.ListEvent):
        item = evt.GetItem()
        item_id = item.GetId()
        db_id = self._loaded_results[item_id][0]
        self._selected_db_id = db_id

        parent = self.GetParent().GetTopLevelParent()
        parent.EndModal(wx.ID_OK)

        evt.Skip()

    def SetValues(self, con, results):
        count = results[0]
        self.con = con
        self.DeleteAllItems()
        self._loaded_results = [results[1:]]
        self.SetItemCount(count)

    def OnGetItemText(self, item, col):
        if len(self._loaded_results) > item:
            return str(self._loaded_results[item][col + 1])

        while len(self._loaded_results) <= item:
            line = self.con.fetchone()

            if line:
                self._loaded_results.append(line[1:])
                self.SetItemData(item, line[1])
            else:
                break

        if len(self._loaded_results) > item:
            return str(self._loaded_results[item][col + 1])

        return ''

# GetCountPerPage
# GetItemData
