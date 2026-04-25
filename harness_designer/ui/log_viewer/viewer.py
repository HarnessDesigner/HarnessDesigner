from typing import TYPE_CHECKING, Optional, List
import threading

import wx
import os
import time
import zipfile
import pandas as pd

from wx import aui

from ... import config as _config


if TYPE_CHECKING:
    from ... import logger as _logger
    from .. import mainframe as _mainframe


Config = _config.Config.logging


class LogViewer(aui.AuiPaneInfo):

    def __init__(self, mainframe: "_mainframe.MainFrame"):
        self.viewer = LogViewerPanel(mainframe, mainframe.logger)
        self.mainframe = mainframe
        self.manager = mainframe.manager

        aui.AuiPaneInfo.__init__(self)

        self.Name('log_viewer')
        self.CaptionVisible(True)
        self.Floatable(True)
        self.MinimizeButton(True)
        self.MaximizeButton(True)
        self.Dockable(True)
        self.CloseButton(True)
        self.PaneBorder(True)
        self.Caption('Log Viewer')
        self.DestroyOnClose(False)
        self.Gripper(True)
        self.Left()
        self.Resizable(True)
        self.Window(self.viewer)

        self.manager.AddPane(self.viewer, self)
        aui.AuiPaneInfo.Show(self)
        self.manager.Update()

    def Show(self, show=True):
        aui.AuiPaneInfo.Show(self, show)
        self.manager.Update()

    def Refresh(self, *args, **kwargs):
        self.viewer.Refresh(*args, **kwargs)

    def Destroy(self):
        self.viewer.Destroy()


class VirtualLogListCtrl(wx.ListCtrl):
    """
    Virtual ListCtrl that only loads visible log entries on demand
    This keeps memory usage low and UI responsive
    """

    def __init__(self, parent):
        wx.ListCtrl.__init__(
            self,
            parent,
            style=wx.LC_REPORT | wx.LC_VIRTUAL | wx.LC_SINGLE_SEL
        )

        # Define columns
        self.InsertColumn(0, "Timestamp", 180)
        self.InsertColumn(1, "Level", 100)
        self.InsertColumn(2, "Message", 600)

        # Data storage
        self.data = pd.DataFrame(columns=['timestamp', 'level', 'message'])

        # Set attributes for different log levels
        self.attr_error = wx.ItemAttr()
        self.attr_error.SetTextColour(wx.RED)

        self.attr_warning = wx.ItemAttr()
        self.attr_warning.SetTextColour(wx.Colour(255, 140, 0))  # Orange

        self.attr_notice = wx.ItemAttr()
        self.attr_notice.SetTextColour(wx.Colour(0, 100, 200))  # Blue

        self.attr_debug = wx.ItemAttr()
        self.attr_debug.SetTextColour(wx.Colour(128, 128, 128))  # Gray

        self.attr_info = wx.ItemAttr()
        self.attr_info.SetTextColour(wx.BLACK)
        self._is_destroyed = False

    def Destroy(self):
        self._is_destroyed = True

        wx.ListCtrl.Destroy(self)

    def AppendData(self, data: pd.DataFrame):
        # Convert timestamp to string for the incoming data only

        def _do(new_data):
            if not new_data.empty and 'timestamp' in new_data.columns:
                # if pd.api.types.is_datetime64_any_dtype(new_data['timestamp']):
                #     new_data['timestamp_str'] = (
                #         new_data['timestamp'].dt.strftime('%m.%d.%Y-%H:%M:%S'))
                #
                # else:
                new_data['timestamp_str'] = new_data['timestamp'].astype(str)

            # Now concatenate with the already-formatted existing data
            self.data = pd.concat([self.data, new_data], ignore_index=True)

            if not self._is_destroyed:
                self.SetItemCount(len(self.data))
                self.Refresh(False)

        wx.CallAfter(_do, data)

    def SetData(self, df: pd.DataFrame):
        """
        Set the data to display

        Args:
            df: DataFrame with log entries
        """
        self.data = df.copy() if not df.empty else pd.DataFrame(columns=['timestamp', 'level', 'message'])

        # Convert timestamp to string for display
        if not self.data.empty and 'timestamp' in self.data.columns:
            # if pd.api.types.is_datetime64_any_dtype(self.data['timestamp']):
            #     self.data['timestamp_str'] = self.data['timestamp'].dt.strftime('%m.%d.%Y-%H:%M:%S')
            # else:
            self.data['timestamp_str'] = self.data['timestamp'].astype(str)
        else:
            self.data['timestamp_str'] = []

        # Update the virtual list count
        self.SetItemCount(len(self.data))

        # Refresh display
        self.Refresh(False)

    def OnGetItemText(self, item: int, column: int) -> str:
        """
        Called by the virtual list control to get the text for a specific cell
        Only called for visible items!
        """
        if item >= len(self.data):
            return ""

        row = self.data.iloc[item]

        if column == 0:
            return str(row.get('timestamp_str', ''))
        elif column == 1:
            return str(row.get('level', ''))
        elif column == 2:
            return str(row.get('message', ''))

        return ""

    def OnGetItemAttr(self, item: int) -> Optional[wx.ItemAttr]:
        """
        Called by the virtual list control to get the attributes for a row
        Used to color-code log levels
        """
        if item >= len(self.data):
            return None

        level = str(self.data.iloc[item].get('level', '')).upper()

        if 'ERROR' in level or 'TRACEBACK' in level:
            return self.attr_error
        elif 'WARNING' in level or 'WARN' in level:
            return self.attr_warning
        elif 'NOTICE' in level:
            return self.attr_notice
        elif 'DEBUG' in level:
            return self.attr_debug
        else:
            return self.attr_info


class LogViewerPanel(wx.SplitterWindow):

    def __init__(self, parent, logger: "_logger.Log"):
        self.logger = logger

        wx.SplitterWindow.__init__(self, parent, wx.ID_ANY, style=wx.BORDER_NONE | wx.SP_LIVE_UPDATE)

        self.treectrl = wx.TreeCtrl(self, wx.ID_ANY, style=wx.TR_HAS_BUTTONS | wx.TR_LINES_AT_ROOT | wx.TR_SINGLE)
        self.root = self.treectrl.AddRoot('Logs')
        self._curr_log = None
        self._is_destroyed = False
        self.current_data = pd.DataFrame()
        self.expanded_items = set()  # Track which tree items have been expanded

        # Replace TextCtrl with VirtualLogListCtrl
        self.log_list = VirtualLogListCtrl(self)

        self.treectrl.Bind(wx.EVT_TREE_SEL_CHANGED, self.on_tree_selection)
        self.treectrl.Bind(wx.EVT_TREE_ITEM_EXPANDING, self.on_tree_expanding)
        self.treectrl.Bind(wx.EVT_TREE_ITEM_COLLAPSED, self.on_tree_collapsed)

        self.SetMinimumPaneSize(20)
        self.SplitVertically(self.treectrl, self.log_list, 200)

        # Bind to logger for real-time updates
        logger.log_handler.bind(self.new_data)

        def _do():
            wx.BeginBusyCursor()
            self.load()
            # Load current log data
            self._load_current_log_initial()
            wx.EndBusyCursor()

        wx.CallAfter(_do)

    def Destroy(self):
        self._is_destroyed = True
        wx.GetApp().Yield(False)
        self.log_list.Destroy()
        wx.SplitterWindow.Destroy(self)

    def _load_current_log_initial(self):
        """Load the current log file on startup"""
        try:
            current_log_path = self.logger.log_handler.get_current_log_path()
            if current_log_path and os.path.exists(current_log_path):
                df = self._read_log_file(current_log_path)
                self.current_data = df
                self.log_list.SetData(df)
        except Exception as e:
            self.logger.error(f"Failed to load initial log: {e}")

    def new_data(self, data=None):
        """Called when new log data is written"""

        if self._is_destroyed:
            return

        if data is None:
            # Full reload requested
            self.load()
        else:
            # Real-time update - append new data to current view
            # Only update if we're viewing the current log
            if self._curr_log is not None:
                self.log_list.AppendData(data)
                # wx.CallAfter(self._load_current_log_initial)

    def on_tree_selection(self, evt: wx.TreeEvent):
        """Handle tree selection - load log data"""
        item = evt.GetItem()
        data = self.treectrl.GetItemData(item)

        if not data:
            evt.Skip()
            return

        item_type = data.get('type')

        if item_type == 'file':
            # Load entire file
            self._load_log_data(data['path'])
        elif item_type == 'date':
            # Load specific date
            self._load_log_data(data['file'], date_filter=data['date'])
        elif item_type == 'hour':
            # Load specific hour
            self._load_log_data(
                data['file'],
                date_filter=data['date'],
                hour_filter=data['hour']
            )
        elif item_type == 'archive_file':
            # Load file from archive
            self._load_archive_file(data['zipfile'], data['filename'])

        evt.Skip()

    def on_tree_expanding(self, evt: wx.TreeEvent):
        """Handle tree item expansion - load children on demand"""
        item = evt.GetItem()

        # Check if we've already populated this item
        item_hash = item.GetID() if hasattr(item, 'GetID') else int(str(item))

        if item_hash in self.expanded_items:
            evt.Skip()
            return

        data = self.treectrl.GetItemData(item)

        if not data:
            evt.Skip()
            return

        item_type = data.get('type')

        if item_type == 'file':
            # Load dates for this file
            self._load_dates_for_file(item, data['path'], item_hash)
        elif item_type == 'date':
            # Load hours for this date
            self._load_hours_for_date(item, data['file'], data['date'], item_hash)
        elif item_type == 'archive':
            # Load files from archive
            self._load_archive_files(item, data['path'], item_hash)
        elif item_type == 'archive_file':
            # Load dates from archive file
            self._load_dates_for_archive_file(item, data['zipfile'], data['filename'], item_hash)
        elif item_type == 'archive_date':
            # Load hours from archive date
            self._load_hours_for_archive_date(item, data['zipfile'], data['filename'], data['date'], item_hash)

        evt.Skip()

    def _load_dates_for_file(self, file_item, log_path: str, item_hash: int):
        """Load dates for a log file (called when file is expanded)"""
        # Remove dummy child
        self.treectrl.DeleteChildren(file_item)

        # Show loading message
        self.treectrl.AppendItem(file_item, "Loading dates...")

        def load_dates():
            dates = self._get_dates_in_log(log_path)
            wx.CallAfter(self._populate_dates, file_item, log_path, dates, item_hash)

        thread = threading.Thread(target=load_dates, daemon=True)
        thread.start()

    def _populate_dates(self, parent_item, log_path: str, dates: List[str], item_hash: int):
        """Populate dates in the tree (called from main thread)"""
        self.treectrl.DeleteChildren(parent_item)
        self.expanded_items.add(item_hash)

        if not dates:
            self.treectrl.AppendItem(parent_item, "(No dates found)")
            return

        for date_str in dates:
            date_item = self.treectrl.AppendItem(parent_item, date_str)
            self.treectrl.SetItemData(date_item, {
                'type': 'date',
                'file': log_path,
                'date': date_str
            })
            # Add dummy child to make it expandable
            self.treectrl.AppendItem(date_item, "Loading...")

    def _load_hours_for_date(self, date_item, log_path: str, date_str: str, item_hash: int):
        """Load hours for a specific date (called when date is expanded)"""
        self.treectrl.DeleteChildren(date_item)
        self.treectrl.AppendItem(date_item, "Loading hours...")

        def load_hours():
            hours = self._get_hours_in_date(log_path, date_str)
            wx.CallAfter(self._populate_hours, date_item, log_path, date_str, hours, item_hash, False)

        thread = threading.Thread(target=load_hours, daemon=True)
        thread.start()

    def _populate_hours(self, parent_item, log_path: str, date_str: str, hours: List[int],
                        item_hash: int, is_archive: bool, zipfile_obj=None, filename=None):
        """Populate hours in the tree (called from main thread)"""
        self.treectrl.DeleteChildren(parent_item)
        self.expanded_items.add(item_hash)

        if not hours:
            self.treectrl.AppendItem(parent_item, "(No hours found)")
            return

        for hour in hours:
            hour_label = f"{hour:02d}:00 - {hour:02d}:59"
            hour_item = self.treectrl.AppendItem(parent_item, hour_label)

            if is_archive:
                self.treectrl.SetItemData(hour_item, {
                    'type': 'archive_hour',
                    'zipfile': zipfile_obj,
                    'filename': filename,
                    'date': date_str,
                    'hour': hour
                })
            else:
                self.treectrl.SetItemData(hour_item, {
                    'type': 'hour',
                    'file': log_path,
                    'date': date_str,
                    'hour': hour
                })

    def _load_archive_files(self, archive_item, archive_path: str, item_hash: int):
        """Load files from a zip archive"""
        self.treectrl.DeleteChildren(archive_item)

        try:
            zf = zipfile.ZipFile(archive_path, 'r')
            names = zf.namelist()

            self.expanded_items.add(item_hash)

            for name in names:
                if name.endswith('.csv'):
                    child = self.treectrl.AppendItem(archive_item, name)
                    self.treectrl.SetItemData(child, {
                        'type': 'archive_file',
                        'zipfile': zf,
                        'filename': name
                    })
                    # Add dummy child to make it expandable
                    self.treectrl.AppendItem(child, "Loading...")
        except Exception as e:
            self.logger.error(f"Failed to load archive {archive_path}: {e}")
            self.treectrl.AppendItem(archive_item, f"(Error loading archive)")

    def _load_dates_for_archive_file(self, file_item, zipfile_obj, filename: str, item_hash: int):
        """Load dates from an archived log file"""
        self.treectrl.DeleteChildren(file_item)
        self.treectrl.AppendItem(file_item, "Loading dates...")

        def load_dates():
            dates = self._get_dates_in_archive(zipfile_obj, filename)
            wx.CallAfter(self._populate_archive_dates, file_item, zipfile_obj, filename, dates, item_hash)

        thread = threading.Thread(target=load_dates, daemon=True)
        thread.start()

    def _populate_archive_dates(self, parent_item, zipfile_obj, filename: str, dates: List[str], item_hash: int):
        """Populate dates from archive in the tree"""
        self.treectrl.DeleteChildren(parent_item)
        self.expanded_items.add(item_hash)

        if not dates:
            self.treectrl.AppendItem(parent_item, "(No dates found)")
            return

        for date_str in dates:
            date_item = self.treectrl.AppendItem(parent_item, date_str)
            self.treectrl.SetItemData(date_item, {
                'type': 'archive_date',
                'zipfile': zipfile_obj,
                'filename': filename,
                'date': date_str
            })
            self.treectrl.AppendItem(date_item, "Loading...")

    def _load_hours_for_archive_date(self, date_item, zipfile_obj, filename: str, date_str: str, item_hash: int):
        """Load hours for a specific date in an archive"""
        self.treectrl.DeleteChildren(date_item)
        self.treectrl.AppendItem(date_item, "Loading hours...")

        def load_hours():
            hours = self._get_hours_in_archive_date(zipfile_obj, filename, date_str)
            wx.CallAfter(self._populate_hours, date_item, None, date_str, hours, item_hash, True, zipfile_obj, filename)

        thread = threading.Thread(target=load_hours, daemon=True)
        thread.start()

    def _load_log_data(self, log_path: str, date_filter: Optional[str] = None, hour_filter: Optional[int] = None):
        """Load log data in a separate thread"""
        def load_data():
            df = self._read_log_file(log_path)

            # Apply filters if specified
            if date_filter and hour_filter is not None:
                df = self._filter_by_date_and_hour(df, date_filter, hour_filter)
            elif date_filter:
                df = self._filter_by_date(df, date_filter)

            wx.CallAfter(self._display_log_data, df)

        thread = threading.Thread(target=load_data, daemon=True)
        thread.start()

    def _load_archive_file(self, zipfile_obj, filename: str, date_filter: Optional[str] = None,
                           hour_filter: Optional[int] = None):
        """Load log data from archive"""
        def load_data():
            df = self._read_archive_file(zipfile_obj, filename)

            # Apply filters
            if date_filter and hour_filter is not None:
                df = self._filter_by_date_and_hour(df, date_filter, hour_filter)
            elif date_filter:
                df = self._filter_by_date(df, date_filter)

            wx.CallAfter(self._display_log_data, df)

        thread = threading.Thread(target=load_data, daemon=True)
        thread.start()

    def _display_log_data(self, df: pd.DataFrame):
        """Display log data in the virtual list (called from main thread)"""
        self.current_data = df
        self.log_list.SetData(df)

    def _read_log_file(self, log_path: str) -> pd.DataFrame:
        """Read a log file and return as DataFrame"""
        try:
            if not os.path.exists(log_path):
                return pd.DataFrame(columns=['timestamp', 'level', 'message'])

            # Read CSV file
            df = pd.read_csv(log_path)

            # Convert timestamp to datetime
            if 'timestamp' in df.columns:
                df['timestamp'] = pd.to_datetime(df['timestamp'])

            return df
        except Exception as e:
            self.logger.error(f"Failed to read log file {log_path}: {e}")
            return pd.DataFrame(columns=['timestamp', 'level', 'message'])

    def _read_archive_file(self, zipfile_obj, filename: str) -> pd.DataFrame:
        """Read a log file from archive"""
        try:
            import io
            data = zipfile_obj.read(filename)
            df = pd.read_csv(io.BytesIO(data))

            if 'timestamp' in df.columns:
                df['timestamp'] = pd.to_datetime(df['timestamp'])

            return df
        except Exception as e:
            self.logger.error(f"Failed to read archive file {filename}: {e}")
            return pd.DataFrame(columns=['timestamp', 'level', 'message'])

    def _get_dates_in_log(self, log_path: str) -> List[str]:
        """Get unique dates in a log file"""
        df = self._read_log_file(log_path)
        if df.empty or 'timestamp' not in df.columns:
            return []

        dates = df['timestamp'].dt.date.unique()
        return sorted([str(d) for d in dates], reverse=True)

    def _get_dates_in_archive(self, zipfile_obj, filename: str) -> List[str]:
        """Get unique dates in an archived log file"""
        df = self._read_archive_file(zipfile_obj, filename)
        if df.empty or 'timestamp' not in df.columns:
            return []

        dates = df['timestamp'].dt.date.unique()
        return sorted([str(d) for d in dates], reverse=True)

    def _get_hours_in_date(self, log_path: str, date_str: str) -> List[int]:
        """Get unique hours in a specific date"""
        df = self._read_log_file(log_path)
        if df.empty or 'timestamp' not in df.columns:
            return []

        target_date = pd.to_datetime(date_str).date()
        df_date = df[df['timestamp'].dt.date == target_date]

        if df_date.empty:
            return []

        hours = df_date['timestamp'].dt.hour.unique()
        return sorted(hours.tolist())

    def _get_hours_in_archive_date(self, zipfile_obj, filename: str, date_str: str) -> List[int]:
        """Get unique hours in a specific date from archive"""
        df = self._read_archive_file(zipfile_obj, filename)
        if df.empty or 'timestamp' not in df.columns:
            return []

        target_date = pd.to_datetime(date_str).date()
        df_date = df[df['timestamp'].dt.date == target_date]

        if df_date.empty:
            return []

        hours = df_date['timestamp'].dt.hour.unique()
        return sorted(hours.tolist())

    @staticmethod
    def _filter_by_date(df: pd.DataFrame, date_str: str) -> pd.DataFrame:
        """Filter DataFrame by date"""
        if df.empty or 'timestamp' not in df.columns:
            return df

        target_date = pd.to_datetime(date_str).date()
        return df[df['timestamp'].dt.date == target_date].copy()

    @staticmethod
    def _filter_by_date_and_hour(df: pd.DataFrame, date_str: str, hour: int) -> pd.DataFrame:
        """Filter DataFrame by date and hour"""
        if df.empty or 'timestamp' not in df.columns:
            return df

        target_date = pd.to_datetime(date_str).date()
        filtered = df[
            (df['timestamp'].dt.date == target_date) &
            (df['timestamp'].dt.hour == hour)
        ]
        return filtered.copy()

    def on_tree_collapsed(self, evt: wx.TreeEvent):
        """Handle tree collapse - clear children to save memory"""
        treeitem = evt.GetItem()

        if treeitem.IsOk():
            # Get the item hash and remove from expanded set
            item_hash = treeitem.GetID() if hasattr(treeitem, 'GetID') else int(str(treeitem))
            self.expanded_items.discard(item_hash)

            # Delete all children
            self.treectrl.DeleteChildren(treeitem)

            # Add dummy child to make it expandable again
            self.treectrl.AppendItem(treeitem, "Loading...")

        evt.Skip()

    def load(self):
        """Load log files and archives into tree"""
        self.treectrl.DeleteAllItems()
        self.expanded_items.clear()
        self.root = self.treectrl.AddRoot('Logs')

        # Load archives
        archives = self.get_archives()
        for archive_name, timestamp, archive_path in archives:
            child = self.treectrl.AppendItem(self.root, f'{archive_name} ({timestamp})')
            self.treectrl.SetItemData(child, {'type': 'archive', 'path': archive_path})
            self.treectrl.AppendItem(child, "Loading...")

        # Load log files
        logfiles = self.get_logfiles()
        self._curr_log = None

        for log_name, timestamp, log_path in logfiles:
            child = self.treectrl.AppendItem(self.root, f'{log_name} ({timestamp})')
            self.treectrl.SetItemData(child, {'type': 'file', 'path': log_path})
            if self._curr_log is None:
                self._curr_log = child
            self.treectrl.AppendItem(child, "Loading...")

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
            log_path = os.path.join(Config.save_path, log_name + '.csv')
            if not os.path.exists(log_path):
                break

            mod_time = os.path.getmtime(log_path)
            readable_mod_time = time.asctime(time.localtime(mod_time))

            res.append((log_name, readable_mod_time, log_path))

        return res
