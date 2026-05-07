import wx
import time

from . import edit_dialog as _edit_dialog
from ... import config as _config


class EditorDBConfig(metaclass=_config.ConfigDB):
    pass


# This class is used to time how fast a suer is scrolling.
# The porpose of this is to set the number of rows to collect when scrilling.
# The number os records that get collected is determine by the number that
# is able to be displayed and the scrolling speed. The faster the scrolling
# speed the more rows that get collected at a time. The row data is cached
# and later pruned down to what the last collected size was. The pruning occurs
# when the UI is idle and it will only occur a single time after a scrolling
# event has finished. This allows any change that might be made at a different
# seat to prropgate out to other clients. There is a small studder when
# scrolling that does occur when viewing the housings and this studder is
# occuring simply because of the complexity of the query that is being made to
# collect the data. The queries are quite involved in order to provide the ability
# to sort the data by column. This is done by clicking on the arrow in the
# column header.
class ScrollTracker:
    min_buffer = 10
    max_buffer = 200

    def __init__(self):
        self.last_row = 0
        self.last_time = time.monotonic_ns()

    def get_buffer_size(self, current_row):
        now = time.monotonic_ns()
        elapsed = (now - self.last_time) * 1e-9

        if elapsed:
            velocity = abs(current_row - self.last_row) / elapsed
        else:
            velocity = 0

        self.last_row = current_row
        self.last_time = now

        # scale buffer between MIN and MAX based on velocity
        # tune the divisor to taste based on your expected scroll speeds
        buffer = int(min(self.max_buffer, max(self.min_buffer, velocity * 1.5)))

        return buffer


class EditorList(wx.ListCtrl):
    _has_image = True
    _has_model_3d = True
    __table_name__ = ''
    __query__ = ''
    column_mapping = {}
    resize_registered = False

    @property
    def record_count(self):
        self.table.execute(f'SELECT COUNT(*) FROM {self.table_name};')
        return self.table.fetchall()[0][0]

    def get_obj_id(self, row):
        self.table.execute(self.__query__.format(sort_column=self.sort_column, sort_direction=self.sort_direction, row=row + 1))
        rows = self.table.fetchall()
        if rows:
            return rows[0][0]

    def get_row(self, row):
        if row not in self.rows:
            self.buffer_size = self.scroll_tracker.get_buffer_size(row)
            start_row = max(1, row - self.buffer_size // 2)
            end_row = start_row + self.buffer_size
            self.get_rows(start_row, end_row)
            self.current_row = row
            self.needs_pruning = True

        return self.rows.get(row, None)

    def get_rows(self, start, stop):
        self.table.execute(self.__query__.format(
            sort_column=self.sort_column, sort_direction=self.sort_direction,
            start_row=start, end_row=stop))

        rows = self.table.fetchall()
        if rows:
            rows = {i + start: rows[i] for i in range(len(rows))}
            self.rows.update(rows)

    def GetLabel(self):
        return self._label

    def __init__(self, parent, mainframe, label, table):
        self._label = label
        self.table_name = table.__table_name__
        self.table = table
        self.visible_row = 0
        self.scroll_tracker = ScrollTracker()
        self.bitmap_indexes = {}
        self.set_buffer_size = True
        self.rows = {}
        self.selected = None
        self.mainframe = mainframe
        self.downloading_images = []
        self.sort_column = 'id'
        self.sort_direction = 'ASC'  # DESC

        # if not hasattr(EditorDBConfig, self.__table_name__):
        #     cls = _config.ConfigDB(self.__table_name__, (), {})
        #     setattr(EditorDBConfig, self.__table_name__, cls)
        #
        # self.config = getattr(EditorDBConfig, self.__table_name__)
        self.needs_pruning = False
        self.current_row = 0

        wx.ListCtrl.__init__(self, parent, wx.ID_ANY,
                             style=wx.LC_REPORT | wx.LC_VIRTUAL | wx.LC_HRULES | wx.LC_VRULES | wx.LC_SINGLE_SEL)

        self.images = wx.ImageList(64, 64)
        self.blank_bitmap = wx.Bitmap(64, 64, 32)
        dc = wx.MemoryDC(self.blank_bitmap)
        dc.SetBackground(wx.Brush((0, 0, 0, 0)))
        dc.Clear()
        del dc

        self.blank_id = self.images.Add(self.blank_bitmap)
        self.blank_bitmap.SetMaskColour((0, 0, 0))
        self.SetImageList(self.images, wx.IMAGE_LIST_SMALL)
        self.column_lookup = {}

        for i in sorted(list(self.column_mapping.keys())):
            label, column_name = self.column_mapping[i]
            if i == 0:
                self.AppendColumn('')
                self.SetColumnWidth(i, 72)

            i += 1
            if column_name == 'model3d_id':
                align = wx.LIST_FORMAT_CENTER
            else:
                align = wx.LIST_FORMAT_LEFT

            self.AppendColumn(label, format=align)
            self.column_lookup[i] = column_name

            if label == 'DB ID':
                # ascending indicator is backwards
                self.ShowSortIndicator(i, ascending=False)

            if label == 'Description':
                offset = 100
            else:
                offset = 25

            self.max_column_count = i

            # if not hasattr(self.config, column_name):
            #     width = self.GetTextExtent(label)[0] + offset
            #     setattr(self.config, column_name, width)
            #
            # getattr(self.config, column_name)

            width = self.GetTextExtent(label)[0] + offset
            self.SetColumnWidth(i, width)

        self.SetItemCount(self.record_count)

        self.Bind(wx.EVT_LIST_ITEM_SELECTED, self.on_item_selected)
        self.Bind(wx.EVT_LIST_ITEM_ACTIVATED, self.on_item_activated)
        self.Bind(wx.EVT_LIST_ITEM_DESELECTED, self.on_item_deselected)

        self.Bind(wx.EVT_LIST_ITEM_RIGHT_CLICK, self.on_right_click)

        self.Bind(wx.EVT_LIST_COL_CLICK, self.on_column_click)

        self.Bind(wx.EVT_IDLE, self.on_idle)
        # self.Bind(wx.EVT_WINDOW_DESTROY, self.on_destroy)
        # self.Bind(wx.EVT_CLOSE, self.on_close)

        if not EditorList.resize_registered:
            self.Bind(wx.EVT_SIZE, self.on_size)
            EditorList.resize_registered = True

        self.buffer_size = self.GetCountPerPage()

    def _save_column_widths(self):
        for i in range(1, self.GetColumnCount(), 1):
            width = self.GetColumnWidth(i)
            column_name = self.column_lookup[i]

            setattr(self.config, column_name, width)

    def on_close(self, evt):
        evt.Skip()
        self._save_column_widths()

    def on_destroy(self, evt):
        evt.Skip()
        self._save_column_widths()

    def on_size(self, evt):
        evt.Skip()

        def _do():
            count = self.GetCountPerPage()

            if count > 0:
                ScrollTracker.min_buffer = (count + 1) * 2
                ScrollTracker.max_buffer = (count + 1) * 2 * 20

            print(ScrollTracker.min_buffer, ScrollTracker.max_buffer)

        wx.CallAfter(_do)

    def on_column_click(self, evt):
        col = evt.GetColumn()
        evt.Skip()

        if col not in self.column_lookup:
            return

        sort_column = self.column_lookup[col]

        if sort_column == self.sort_column:
            if self.sort_direction == 'ASC':
                self.sort_direction = 'DESC'

                # ascending indicator is backwards
                self.ShowSortIndicator(col, ascending=True)
            else:
                self.sort_direction = 'ASC'

                # ascending indicator is backwards
                self.ShowSortIndicator(col, ascending=False)

        else:
            self.sort_direction = 'ASC'

            # ascending indicator is backwards
            self.ShowSortIndicator(col, ascending=False)

        self.sort_column = sort_column

        self.rows.clear()
        self.selected = None
        self.Refresh(False)

    def on_right_click(self, evt):
        evt.Skip()

    def on_item_selected(self, evt):
        self.selected = evt.Index
        evt.Skip()

    def prune_cache(self, current_row, buffer_size):
        keep_range = buffer_size * 2
        min_row = current_row - keep_range
        max_row = current_row + keep_range
        self.rows = {k: v for k, v in self.rows.items() if min_row <= k <= max_row}

    def on_idle(self, _):
        if self.needs_pruning:
            self.prune_cache(self.current_row, self.buffer_size)
            self.needs_pruning = False

    def on_item_activated(self, evt):
        self.selected = evt.Index
        db_id = self.get_obj_id(self.selected)
        obj = self.table[db_id]

        dlg = _edit_dialog.EditDialog(self.mainframe, 'Edit ' + self._label, obj)
        dlg.ShowModal()
        del self.rows[self.selected]
        self.Refresh(False)
        evt.Skip()

    def on_item_deselected(self, evt):
        self.selected = None
        evt.Skip()

    def OnGetItemText(self, row_id, col_id):
        if col_id == 0:
            return ''

        if row_id <= 0:
            return ''

        row = self.get_row(row_id)

        if row is None:
            # self.SetItemCount(self.record_count)
            return ''

        if self._has_model_3d:
            col = self.column_lookup.get(col_id, '')
            if col == 'model3d_id':
                if row[-2] is not None:
                    return '✔'
                else:
                    return ''  # '✘'

        return str(row[col_id - 1])

    def OnGetItemImage(self, row_id):
        if row_id <= 0:
            return -1

        row = self.get_row(row_id)

        if row is None:
            return -1  # self.blank_id

        db_id = row[0]

        if db_id not in self.bitmap_indexes:
            if self._has_image:
                image_id = row[-1]
                if image_id is None:
                    self.bitmap_indexes[db_id] = -1  # self.blank_id
                    return -1  # self.blank_id
                else:
                    image = self.table.db.images_table[image_id]
                    if image.uuid is None:
                        if image_id not in self.downloading_images:
                            self.mainframe.db_connector.update_monitor.get_image(image_id)
                            self.downloading_images.append(image_id)

                        return -1  # self.blank_id
                    else:
                        if image_id in self.downloading_images:
                            self.downloading_images.remove(image_id)

                        image = image.data_path
                        if image is None:
                            self.bitmap_indexes[db_id] = -1  # self.blank_id
                            return -1  # self.blank_id
                        else:
                            image = wx.Image(image)
                            image = image.Rescale(64, 64)
                            bmp = image.ConvertToBitmap()
            else:
                self.bitmap_indexes[db_id] = -1  # self.blank_id
                return -1  # self.blank_id

            bmp_id = self.images.Add(bmp)
            self.bitmap_indexes[db_id] = bmp_id

        return self.bitmap_indexes[db_id]

    def OnGetItemAttr(self, item):
        return None

    def GetSelection(self):
        if self.selected is None:
            return None

        return self.selected
