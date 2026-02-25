from typing import TYPE_CHECKING, Union

import wx

from wx.lib import scrolledpanel, newevent


if TYPE_CHECKING:
    from .. import global_db as _global_db
    from .. import project_db as _project_db


SearchChangedEvent, EVT_SEARCH_CHANGED_EVENT = newevent.NewEvent()
SearchChangedCommandEvent, EVT_SEARCH_CHANGED_COMMAND_EVENT = newevent.NewCommandEvent()


class Item(wx.BoxSizer):

    def __init__(self, st, ctrl):
        wx.BoxSizer.__init__(self, wx.HORIZONTAL)

        self.st = st
        self.ctrl = ctrl
        self.Add(st, 0, wx.ALL | wx.ALIGN_RIGHT, 5)
        self.Add(ctrl, 0, wx.ALL, 5)

    def GetValue(self):
        return self.ctrl.GetValue()

    def GetName(self):
        return self.st.GetLabel()


class ItemsPanel(scrolledpanel.ScrolledPanel):
    def __init__(self, parent, choices):
        scrolledpanel.ScrolledPanel.__init__(self, parent, wx.ID_ANY, style=wx.BORDER_SUNKEN)

        v_sizer = wx.BoxSizer(wx.VERTICAL)

        self.items = []

        def _HSizer(label, ctrl):
            st = wx.StaticText(self, wx.ID_ANY, label=label)
            sizer = Item(st, ctrl)
            self.items.append(sizer)
            return sizer

        for choice in choices:
            checkbox = wx.CheckBox(self, wx.ID_ANY)
            v_sizer.Add(_HSizer(choice, checkbox), 0)

        self.SetupScrolling(self, scroll_x=False)
        self.SetSizer(v_sizer)

    def Reset(self):
        for item in self.items:
            item.ctrl.SetValue(False)

    def GetValues(self):
        res = []

        for item in self.items:
            if item.GetValue():
                res.append(item)

        return res


class SearchPanelField(wx.Panel):

    def __init__(self, parent, label, params, types):
        wx.Panel.__init__(self, parent, wx.ID_ANY, style=wx.BORDER_SUNKEN)

        self.params = params
        self.types = types

        self.values = parent.db_table.get_unique(*params)

        if len(types) == 1:
            choices = [str(value[0]) for value in self.values]
        else:
            choices = [str(value[1]) for value in self.values]

        v_sizer = wx.BoxSizer(wx.VERTICAL)

        st = wx.StaticText(self, wx.ID_ANY, label=label)
        v_sizer.Add(st, 0, wx.ALL | wx.ALIGN_CENTER, 5)

        self.items_panel = ItemsPanel(self, choices)
        v_sizer.Add(self.items_panel, 1, wx.ALL | wx.EXPAND, 5)

        self.reset_button = wx.Button(wx.ID_RESET, size=(40, -1))

        self.reset_button.Bind(wx.EVT_BUTTON, self.on_reset)

        v_sizer.Add(self.reset_button, 0, wx.ALL | wx.ALIGN_RIGHT, 10)
        self.SetSizer(v_sizer)

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


class SearchPanel(scrolledpanel.ScrolledPanel):

    def __init__(self, parent, db_table: Union["_global_db.TableBase", "_project_db.PJTTableBase"]):
        scrolledpanel.ScrolledPanel.__init__(self, parent, wx.ID_ANY)
        self.parent = parent
        self.db_table = db_table

        self.SetupScrolling(self, scroll_y=False)
        self.search_items = db_table.search_items

        self.fields = []
        self.columns = []

        for key in sorted(list(self.search_items.keys())):
            value = self.search_items[key]

            self.columns.append(value['label'])
            if 'search_params' in value:
                field = SearchPanelField(self, value['label'], value['search_params'], value['type'])
                self.fields.append(field)

                field.Bind(wx.EVT_CHECKBOX, self.on_update)
                field.Bind(wx.EVT_BUTTON, self.on_update)

    def on_update(self, evt):
        evt.Skip()

        cmd = {}
        for field in self.fields:
            cmd.update(field.GetValues())

        results, count = self.db_table.search(self.search_items, **cmd)
        self.parent.SetResults(results, count)


class SelectPartDialog(wx.Dialog):

    def __init__(self, parent, title, table):
        wx.Dialog.__init__(self, parent, wx.ID_ANY, title=title)

        self.parent = parent
        self.table = table

        self.search_panel = SearchPanel(self, table)
        self.result_ctrl = ResultCtrl(self, self.search_panel.columns)

        vsizer = wx.BoxSizer(wx.VERTICAL)

        top_sizer = wx.BoxSizer(wx.HORIZONTAL)
        top_sizer.Add(self.search_panel, 1, wx.EXPAND)
        vsizer.AddSpacer(1)
        vsizer.Add(top_sizer, 1, wx.EXPAND | wx.ALL, 10)

        bottom_sizer = wx.BoxSizer(wx.HORIZONTAL)
        bottom_sizer.Add(self.result_ctrl, 1, wx.RIGHT, 10)
        bottom_sizer.Add(self.preview_ctrl, 1)
        vsizer.Add(bottom_sizer, 1, wx.EXPAND | wx.ALL, 10)

    def SetResults(self, results, count):
        self.result_ctrl.SetValues(results, count)

    def GetValue(self):
        return self.result_ctrl.GetValue()


class ResultCtrl(wx.ListCtrl):

    def __init__(self, parent, columns):
        wx.ListCtrl.__init__(self, parent, style=wx.LC_REPORT | wx.LC_VIRTUAL | wx.LC_SINGLE_SEL | wx.LC_HRULES)
        self.parent = parent
        self._selected_db_id = None

        self._loaded_results = []
        self.results = None

        for column in columns:
            width = self.GetTextExtent(column)[0]

            self.AppendColumn(column, width=width)

        self.Bind(wx.EVT_LIST_ITEM_SELECTED, self.on_item_selected)
        self.Bind(wx.EVT_LIST_ITEM_ACTIVATED, self.on_item_activated)

    def GetValue(self):
        return self._selected_db_id

    def on_item_selected(self, evt: wx.ListEvent):
        item = evt.GetItem()
        db_id = self.GetItemData(item)
        self._selected_db_id = db_id
        obj = self.parent.db_table[db_id]

        model = obj.model3d

        if model is None:
            self.parent.clear_model_preview()
        else:
            model_data = model.model
            self.parent.load_model_preview(model_data)

        evt.Skip()

    def on_item_activated(self, evt: wx.ListEvent):
        item = evt.GetItem()
        db_id = self.GetItemData(item)
        self._selected_db_id = db_id
        self.parent.exit_modal()

        evt.Skip()

    def SetValues(self, results, count):
        self.DeleteAllItems()
        self._loaded_results = []
        self.results = results
        self.SetItemCount(count)

    def OnGetItemText(self, item, col):
        if len(self._loaded_results) - 1 >= item:
            return self._loaded_results[item][col + 1]

        while len(self._loaded_results) - 1 < item:
            line = self.results.fetchone()
            if line:
                self._loaded_results.append(line[0])
                self.SetItemData(item, line[0][0])
            else:
                break

        if len(self._loaded_results) - 1 >= item:
            return self._loaded_results[item][col + 1]

        raise RuntimeError('sanity check')

GetCountPerPage
GetItemData
