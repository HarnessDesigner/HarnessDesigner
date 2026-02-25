
import wx.dataview as dv


class ModelBase(dv.DataViewIndexListModel):
    __table_name__ = ''
    column_mapping = {}
    table: "_global_db.TableBase" = None

    def __init__(self, table: "_global_db.TableBase"):
        table.execute(f'SELECT COUNT(*) FROM {self.__table_name__};')
        count = table.fetchall()[0][0]
        self.table = table
        dv.DataViewIndexListModel.__init__(self, count)

    def GetColumnType(self, col):
        return 'string'

    def GetValueByRow(self, row, col):
        self.table.execute(f'SELECT {self.column_mapping.get(col)} FROM {self.__table_name__} ORDER BY id ASC;')
        results = self.table.fetchall()
        return str(results[row][0])

    def SetValueByRow(self, value, row, col):
        self.table.execute(f'SELECT id FROM {self.__table_name__} ORDER BY id ASC;')
        results = self.table.fetchall()
        db_id = results[row][0]
        kwargs = {self.column_mapping.get(col): value}
        self.table.update(db_id, **kwargs)
        return True

    def GetColumnCount(self):
        return len(self.column_mapping)

    def GetCount(self):
        self.table.execute(f'SELECT COUNT(*) FROM {self.__table_name__};')
        count = self.table.fetchall()[0][0]
        return count

    def GetAttrByRow(self, row, col, attr):
        return False

    def Compare(self, item1, item2, col, ascending):
        raise NotImplementedError

    def DeleteRows(self, rows):
        rows = sorted(rows, reverse=True)

        for row in rows:
            db_id = self.GetValueByRow(row, 0)
            self.table.delete(db_id)

            self.RowDeleted(row)

    def AddRow(self, value):
        self.table.insert(*value)
        self.RowAppended()
