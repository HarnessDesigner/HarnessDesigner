from typing import TYPE_CHECKING

import wx
import os
import time
import zipfile

from wx import aui

from ... import config as _config


if TYPE_CHECKING:
    from ... import logger as _logger
    from .. import mainframe as _mainframe


Config = _config.Config.logging


class LogViewer(aui.AuiPaneInfo):

    def __init__(self, mainframe: "_mainframe.MainFrame"):
        self.viewer = LogViewerPanel(mainframe, mainframe.logger)
        print('viewer created')
        self.mainframe = mainframe
        self.manager = mainframe.manager

        aui.AuiPaneInfo.__init__(self)

        self.Name('log_viewer')
        self.CaptionVisible()
        self.Floatable()
        self.MinimizeButton()
        self.MaximizeButton()
        self.Dockable()
        self.CloseButton(True)
        self.PaneBorder()
        self.Caption('Log Viewer')
        self.DestroyOnClose(False)
        self.Gripper()
        self.Left()
        self.Resizable()
        self.Window(self.viewer)

        self.manager.AddPane(self.viewer, self)
        self.manager.Update()

    def Refresh(self, *args, **kwargs):
        self.viewer.Refresh(*args, **kwargs)

    def Destroy(self):
        self.viewer.Destroy()


class LogData:

    def __init__(self):
        self.data = ''

    def append(self, line):
        self.data += line + '\n'


class LogViewerPanel(wx.Panel):

    def __init__(self, parent, logger: "_logger.Log"):

        print('binding log handler')
        logger.log_handler.bind(self.new_data)
        self.logger = logger

        wx.Panel.__init__(self, parent, wx.ID_ANY, style=wx.BORDER_NONE)

        self.treectrl = wx.TreeCtrl(self, wx.ID_ANY, style=wx.TR_HAS_BUTTONS | wx.TR_LINES_AT_ROOT | wx.TR_SINGLE)
        self.root = self.treectrl.AddRoot('Logs')
        self._curr_log = None
        self._visible = None

        self.textctrl = wx.TextCtrl(self, wx.ID_ANY, value='\n' * 200, style=wx.TE_MULTILINE | wx.TE_READONLY)

        self.treectrl.Bind(wx.EVT_TREE_ITEM_ACTIVATED, self.on_tree_activated)
        self.treectrl.Bind(wx.EVT_TREE_ITEM_EXPANDING, self.on_tree_expanding)
        self.treectrl.Bind(wx.EVT_TREE_ITEM_COLLAPSED, self.on_tree_collapsed)

        def _do():
            self.load()
            self.textctrl.ChangeValue(self.logger.log_handler.log_data)

        wx.CallAfter(_do)

    def new_data(self, data=None):
        if data is None:
            self.load()
        else:
            if self._visible is not None:
                log_data = self.logger.log_handler.log_data
                log_data = log_data.rsplit(data, 1)[0]

                if self._visible == log_data:
                    self._visible += data
                    self.textctrl.AppendText(data)

    def on_tree_activated(self, evt: wx.TreeEvent):
        treeitem = evt.GetItem()

        if treeitem.IsOk():
            if not self.treectrl.ItemHasChildren(treeitem):
                data = self.treectrl.GetItemData(treeitem)
                self.textctrl.ChangeValue(data)
                self._visible = data

        evt.Skip()

    def on_tree_expanding(self, evt: wx.TreeEvent):
        treeitem = evt.GetItem()

        if treeitem.IsOk():
            data = self.treectrl.GetItemData(treeitem)

            if data is None:
                log_data = self.logger.log_handler.log_data
                log_data = log_data.split('\n')
                date_data = LogData()

                last_date = log_data[0].split('-', 1)[0]

                for line in log_data:
                    if line.startswith(last_date):
                        date_data.append(line)
                    else:
                        child = self.treectrl.AppendItem(treeitem, last_date[1:])
                        self.treectrl.SetItemData(child, date_data)

                        date_data = LogData()
                        last_date = line.split('-', 1)[0]

                if date_data.data:
                    child = self.treectrl.AppendItem(treeitem, last_date[1:])
                    self.treectrl.SetItemData(child, date_data)

                child = self.treectrl.AppendItem(treeitem, 'Whole File')
                self.treectrl.SetItemData(child, log_data)

            elif isinstance(data, str):
                if data.endswith('.zip'):
                    zf = zipfile.ZipFile(data)
                    names = zf.namelist()

                    for name in names:
                        child = self.treectrl.AppendItem(treeitem, name)
                        self.treectrl.SetItemHasChildren(child, True)
                        self.treectrl.SetItemData(child, zf)
                else:
                    with open(data, 'r') as f:
                        log_data = f.read()

                    log_data = log_data.split('\n')
                    date_data = LogData()

                    last_date = log_data[0].split('-', 1)[0]

                    for line in log_data:
                        if line.startswith(last_date):
                            date_data.append(line)
                        else:
                            child = self.treectrl.AppendItem(treeitem, last_date[1:])
                            self.treectrl.SetItemData(child, date_data)

                            date_data = LogData()
                            last_date = line.split('-', 1)[0]

                    if date_data.data:
                        child = self.treectrl.AppendItem(treeitem, last_date[1:])
                        self.treectrl.SetItemData(child, date_data)

                    child = self.treectrl.AppendItem(treeitem, 'Whole File')
                    self.treectrl.SetItemData(child, log_data)

            elif isinstance(data, zipfile.ZipFile):
                filename = self.treectrl.GetItemText(treeitem)
                zf = data
                log_data = zf.read(filename).decode('utf-8')

                log_data = log_data.split('\n')
                date_data = LogData()

                last_date = log_data[0].split('-', 1)[0]

                for line in log_data:
                    if line.startswith(last_date):
                        date_data.append(line)
                    else:
                        child = self.treectrl.AppendItem(treeitem, last_date[1:])
                        self.treectrl.SetItemData(child, date_data)

                        date_data = LogData()
                        last_date = line.split('-', 1)[0]

                if date_data.data:
                    child = self.treectrl.AppendItem(treeitem, last_date[1:])
                    self.treectrl.SetItemData(child, date_data)

                child = self.treectrl.AppendItem(treeitem, 'Whole File')
                self.treectrl.SetItemData(child, log_data)

        evt.Skip()

    def _iter_delete(self, parent):

        child, cookie = self.treectrl.GetFirstChild(parent)
        while child.IsOk():
            if self.treectrl.ItemHasChildren(child):
                self._iter_delete(child)
            self.treectrl.Delete(child)

    def on_tree_collapsed(self, evt: wx.TreeEvent):
        treeitem = evt.GetItem()

        if treeitem.IsOk():
            self._iter_delete(treeitem)
            self.treectrl.SetItemHasChildren(treeitem, True)

        evt.Skip()

    def load(self):
        self.treectrl.DeleteAllItems()
        self.root = self.treectrl.AddRoot('Logs')
        archives = self.get_archives()

        for archive_name, timestamp, archive_path in archives:
            child = self.treectrl.AppendItem(self.root, f'{archive_name} ({timestamp})')
            self.treectrl.SetItemHasChildren(child, True)
            self.treectrl.SetItemData(child, archive_path)

        logfiles = self.get_logfiles()

        self._curr_log = None

        for log_name, timestamp, log_path in logfiles:


            child = self.treectrl.AppendItem(self.root, f'{log_name} ({timestamp})')
            self.treectrl.SetItemHasChildren(child, True)
            if self._curr_log is None:
                self._curr_log = child
            else:
                self.treectrl.SetItemData(child, log_path)

    @staticmethod
    def get_archives():
        res = []
        for i in range(Config.num_archives):
            archive_name = f'log_archive-{i + 1}'
            archive_path = os.path.join(Config.save_path, archive_name + '.zip')
            if not os.path.exists(archive_path):
                break

            creation_time = os.path.getctime(archive_path)
            readable_creation_time = time.asctime(time.localtime(creation_time))

            res.append((archive_name, readable_creation_time, archive_path))

        return res

    @staticmethod
    def get_logfiles():
        res = []
        for i in range(Config.num_logfiles):
            log_name = f'log-{i + 1}'
            log_path = os.path.join(Config.save_path, log_name + '.log')
            if not os.path.exists(log_path):
                break

            mod_time = os.path.getmtime(log_path)
            readable_mod_time = time.asctime(time.localtime(mod_time))

            res.append((log_name, readable_mod_time, log_path))

        return res
