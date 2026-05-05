import wx


from . import edit_dialog as _edit_dialog


class EditorList(wx.ListCtrl):
    _has_image = True
    _has_model_3d = True
    __table_name__ = ''
    __query__ = ''
    column_mapping = {}

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
        self.table.execute(self.__query__.format(sort_column=self.sort_column, sort_direction=self.sort_direction, row=row + 1))
        rows = self.table.fetchall()
        if rows:
            return rows[0]

    def GetLabel(self):
        return self._label

    def __init__(self, parent, mainframe, label, table):
        self._label = label
        self.table_name = table.__table_name__
        self.table = table
        self.bitmap_indexes = {}
        self.rows = {}
        self.selected = None
        self.mainframe = mainframe
        self.downloading_images = []
        self.sort_column = 'id'
        self.sort_direction = 'ASC'  # DESC

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

        for i in sorted(list(self.column_mapping.keys())):
            label = self.column_mapping[i]
            if i == 0:
                self.InsertColumn(i, '')
                self.SetColumnWidth(i, 72)

            i += 1

            if self._has_model_3d:
                if i == 1:
                    self.InsertColumn(i, '3D Model')
                    self.SetColumnWidth(i, self.GetTextExtent('3D Model')[0] + 15)
                i += 1

            if label == 'DB ID':
                label += ' ▼'

            self.InsertColumn(i, label)

            if label == 'Description':
                offset = 100
            else:
                offset = 25

            self.SetColumnWidth(i, self.GetTextExtent(label)[0] + offset)

        self.SetItemCount(self.record_count)

        self.attr1 = wx.ItemAttr()
        self.attr1.SetBackgroundColour("yellow")

        self.attr2 = wx.ItemAttr()
        self.attr2.SetBackgroundColour("light blue")

        self.Bind(wx.EVT_LIST_ITEM_SELECTED, self.on_item_selected)
        self.Bind(wx.EVT_LIST_ITEM_ACTIVATED, self.on_item_activated)
        self.Bind(wx.EVT_LIST_ITEM_DESELECTED, self.on_item_deselected)

        self.Bind(wx.EVT_LIST_ITEM_RIGHT_CLICK, self.on_right_click)

        self.Bind(wx.EVT_LIST_COL_CLICK, self.on_column_click)

    def on_column_click(self, evt):
        col = evt.GetColumn()
        evt.Skip()

        if col < 1:
            return

        col_item = self.GetColumn(col)

        label = col_item.GetText()
        if label.endswith('▼'):
            label = label.replace('▼', '▲')
            self.sort_direction = 'DESC'
        elif label.endswith('▲'):
            label = label[:-2]
        else:
            label += ' ▼'
            self.sort_direction = 'ASC'

        id_col = None

        for col_id in self.GetColumnCount():
            col_itm = self.GetColumn(col_id)
            text = col_itm.GetText()
            text = text.replace(' ▼', '').replace(' ▲', '')
            col_itm.SetText(text)
            if text == 'DB ID':
                id_col = col_itm

        col_item.SetText(label)

        if not label.endswith('▼') and not label.endswith('▲'):
            text = id_col.GetText()
            text += ' ▼'
            id_col.SetText(text)
            self.sort_column = 'id'
            self.sort_direction = 'ASC'  # DESC

        self.rows.clear()
        self.selected = None
        self.Refresh(False)

    def on_right_click(self, evt):
        evt.Skip()

    def on_item_selected(self, evt):
        self.selected = evt.Index
        evt.Skip()

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

        if row_id not in self.rows:
            row = self.get_row(row_id)
            self.rows[row_id] = row

        row = self.rows[row_id]

        if row is None:
            # self.SetItemCount(self.record_count)
            return ''

        if self._has_model_3d:
            if col_id == 1:
                return str(row[-2] is not None)

            return str(row[col_id - 2])
        else:
            return str(row[col_id - 1])

    def OnGetItemImage(self, row_id):
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
