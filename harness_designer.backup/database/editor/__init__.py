from typing import TYPE_CHECKING

import wx
from wx import aui

try:
    from . import accessory as _accessory
    from . import boot as _boot
    from . import bundle_cover as _bundle_cover
    from . import cover as _cover
    from . import cpa_lock as _cpa_lock
    from . import housing as _housing
    from . import seal as _seal
    from . import splice as _splice
    from . import terminal as _terminal
    from . import tpa_lock as _tpa_lock
    from . import transition as _transition
    from . import wire as _wire
    from . import wire_marker as _wire_marker

except ImportError:
    import accessory as _accessory
    import boot as _boot
    import bundle_cover as _bundle_cover
    import cover as _cover
    import cpa_lock as _cpa_lock
    import housing as _housing
    import seal as _seal
    import splice as _splice
    import terminal as _terminal
    import tpa_lock as _tpa_lock
    import transition as _transition
    import wire as _wire
    import wire_marker as _wire_marker

if TYPE_CHECKING:
    from .. import global_db as _global_db
    from ... import ui as _ui


class DBEditorPanel(aui.AuiNotebook):

    def __init__(self, parent: "_ui.MainFrame"):
        self.g_db: "_global_db.GLBTables" = None

        aui.AuiNotebook.__init__(self, parent, wx.ID_ANY,
                                 style=(aui.AUI_NB_TOP | aui.AUI_NB_TAB_SPLIT |
                                        aui.AUI_NB_TAB_MOVE | aui.AUI_NB_SCROLL_BUTTONS))

        self.accessories: _accessory.AccessoriesPanel = None
        self.boots: _boot.BootsPanel = None
        self.bundle_covers: _bundle_cover.BundleCoversPanel = None
        self.covers: _cover.CoversPanel = None
        self.cpa_locks: _cpa_lock.CPALocksPanel = None
        self.housings: _housing.HousingsPanel = None
        self.seals: _seal.SealsPanel = None
        self.splices: _splice.SplicesPanel = None
        self.terminals: _terminal.TerminalsPanel = None
        self.tpa_locks: _tpa_lock.TPALocksPanel = None
        self.transitions: _transition.TransitionsPanel = None
        self.wires: _wire.WiresPanel = None
        self.wire_markers: _wire_marker.WireMarkerPanel = None

    def load_db(self, g_db: "_global_db.GLBTables"):
        self.g_db = g_db

        self.accessories = _accessory.AccessoriesPanel(self, g_db.accessories_table)
        self.AddPage(self.accessories, 'Accessories')

        self.boots = _boot.BootsPanel(self, g_db.boots_table)
        self.AddPage(self.boots, 'Boots')

        self.bundle_covers = _bundle_cover.BundleCoversPanel(self, g_db.bundle_covers_table)
        self.AddPage(self.bundle_covers, 'Bundle Covers')

        self.covers = _cover.CoversPanel(self, g_db.covers_table)
        self.AddPage(self.covers, 'Covers')

        self.cpa_locks = _cpa_lock.CPALocksPanel(self, g_db.cpa_locks_table)
        self.AddPage(self.cpa_locks, 'CPA Locks')

        self.housings = _housing.HousingsPanel(self, g_db.housings_table)
        self.AddPage(self.housings, 'Housings')

        self.seals = _seal.SealsPanel(self, g_db.seals_table)
        self.AddPage(self.seals, 'Seals')

        self.splices = _splice.SplicesPanel(self, g_db.splices_table)
        self.AddPage(self.splices, 'Splices')

        self.terminals = _terminal.TerminalsPanel(self, g_db.terminals_table)
        self.AddPage(self.terminals, 'Terminals')

        self.tpa_locks = _tpa_lock.TPALocksPanel(self, g_db.tpa_locks_table)
        self.AddPage(self.tpa_locks, 'TPA Locks')

        self.transitions = _transition.TransitionsPanel(self, g_db.transitions_table)
        self.AddPage(self.transitions, 'Transitions')

        self.wires = _wire.WiresPanel(self, g_db.wires_table)
        self.AddPage(self.wires, 'Wires')

        self.wire_markers = _wire_marker.WireMarkerPanel(self, g_db.wire_markers_table)
        self.AddPage(self.wire_markers, 'Wire Markers')


if __name__ == '__main__':

    class DBEntry:

        def __init__(self, table, db_id):
            self.table = table
            self.db_id = db_id

        @property
        def name(self):
            return self.table.select('name', db_id=self.db_id)[0][0]

        @property
        def description(self):
            return self.table.select('description', db_id=self.db_id)[0][0]

    class DBTable:

        def __init__(self, db, table_name):
            self.__table_name__ = table_name
            self.db = db
            self._con = db.con
            self._cur = db.cur

        def __getitem__(self, item):
            self._cur.execute(f'SELECT * FROM {self.__table_name__} WHERE id = {item};')

            for line in self._cur.fetchall():
                return DBEntry(self, line[0])

        def __iter__(self):
            self._cur.execute(f'SELECT id FROM {self.__table_name__};')

            for line in self._cur.fetchall():
                yield line[0]

        @property
        def table_name(self) -> str:
            return self.__table_name__

        def __contains__(self, db_id: int) -> bool:
            self._cur.execute(
                f'SELECT id FROM {self.__table_name__} WHERE id = {db_id};'
                )

            if self._cur.fetchall():
                return True

            return False

        def insert(self, *_, **kwargs) -> int:
            fields = []
            values = []
            args = []

            for key, value in kwargs.items():
                fields.append(key)
                args.append(value)
                values.append('?')

            fields = ', '.join(fields)
            values = ', '.join(values)
            self._cur.execute(
                f'INSERT INTO {self.__table_name__} ({fields}) VALUES ({values});',
                args
                )
            self._con.commit()
            return self._cur.lastrowid

        def select(self, *args, **kwargs):
            args = ', '.join(args)

            if kwargs:
                values = []
                for key, value in kwargs.items():
                    if isinstance(value, (str, float)):
                        value = f'"{value}"'
                    elif value is None:
                        value = 'NULL'

                    values.append(f'{key} = {value}')

                values = ' AND '.join(values)

                where = f' WHERE {values}'
            else:
                where = ''

            self._cur.execute(
                f'SELECT {args} FROM {self.__table_name__}{where};')
            res = self._cur.fetchall()
            return res

        def delete(self, db_id: int) -> None:
            self._cur.execute(
                f'DELETE FROM {self.__table_name__} WHERE id = {db_id};'
                )
            self._con.commit()

        def update(self, db_id: int, **kwargs):
            fields = []
            values = []

            for key, value in kwargs.items():
                fields.append(f'{key} = ?')
                values.append(value)

            fields = ', '.join(fields)
            self._cur.execute(
                f'UPDATE {self.__table_name__} SET {fields} WHERE id = {db_id};',
                values
                )
            self._con.commit()

        def execute(self, cmd, params=None):
            if params is None:
                return self._cur.execute(cmd)
            else:
                return self._con.execute(cmd, params)

        def fetchall(self):
            return self._cur.fetchall()


    class GlobalDB:

        def __init__(self):
            import sqlite3

            self.con = sqlite3.connect('../setup_db/test.db')
            self.cur = self.con.cursor()

        def __getattr__(self, item):

            if item in self.__dict__:
                return self.__dict__[item]

            if item.endswith('_table'):
                table = item[:-6]
                return DBTable(self, table)

    class Frame(wx.Frame):

        def __init__(self):
            wx.Frame.__init__(self, None, wx.ID_ANY, size=(1280, 1024))

            self.manager = aui.AuiManager(self)

            panel = DBEditorPanel(self, GlobalDB())

            self.Bind(wx.EVT_ERASE_BACKGROUND, self.on_erase_background)

            notebook_pane = (aui.AuiPaneInfo().CenterPane().PaneBorder(True)
                             .Name('db_editor').Caption('DB Editor').CloseButton(False)
                             .MaximizeButton(True).MinimizeButton(True).Dockable(True)
                             .Floatable(True).Show(True).CaptionVisible(True))

            self.manager.AddPane(panel, notebook_pane)
            self.manager.Update()

        def on_erase_background(self, _):
            pass

    app = wx.App()

    frame = Frame()
    frame.Show()
    app.MainLoop()
