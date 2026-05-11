from typing import TYPE_CHECKING, Union

from PySide6.QtWidgets import (
    QWidget, QScrollArea, QVBoxLayout, QHBoxLayout, QLabel,
    QCheckBox, QPushButton, QFrame, QAbstractItemView, QHeaderView,
    QSizePolicy, QTreeWidget, QTreeWidgetItem
)
from PySide6.QtCore import Signal, Qt
from PySide6.QtGui import QPixmap

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


# ---------------------------------------------------------------------------
# Custom signals (replaces newevent.NewEvent / NewCommandEvent)
# ---------------------------------------------------------------------------
# SearchChangedEvent and EVT_SEARCH_CHANGED_EVENT are replaced by the
# SearchPanel.search_changed signal.  Any code that previously posted these
# events should connect to that signal instead.


class _ItemRow(QWidget):
    """A label + checkbox row inside _ItemsPanel."""

    def __init__(self, parent, label: str):
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(2, 2, 2, 2)
        self.st = QLabel(label, self)
        self.ctrl = QCheckBox(self)
        layout.addWidget(self.st, 0)
        layout.addWidget(self.ctrl, 0)

    def GetValue(self) -> bool:
        return self.ctrl.isChecked()

    def GetName(self) -> str:
        return self.st.text()


class _ItemsPanel(QScrollArea):
    """Scrollable list of label + checkbox rows."""

    def __init__(self, parent, choices: list[str]):
        super().__init__(parent)
        self.setFrameShape(QFrame.StyledPanel)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setWidgetResizable(True)

        container = QWidget()
        self._layout = QVBoxLayout(container)
        self._layout.setContentsMargins(4, 4, 4, 4)
        self._layout.setSpacing(2)
        self.setWidget(container)

        self.items: list[_ItemRow] = []
        for choice in choices:
            row = _ItemRow(container, choice)
            self._layout.addWidget(row)
            self.items.append(row)

        self._layout.addStretch()

    def Reset(self):
        for item in self.items:
            item.ctrl.setChecked(False)

    def GetValues(self) -> list[_ItemRow]:
        return [item for item in self.items if item.GetValue()]


class _SearchPanelField(QFrame):
    """A titled, scrollable checkbox list for one search dimension."""

    changed = Signal()

    def __init__(self, parent, label: str, params, types):
        super().__init__(parent)
        self.setFrameShape(QFrame.StyledPanel)
        self.parent_panel = parent
        self.params = params
        self.types = types
        self.values = parent.db_table.get_unique(*params)

        if len(types) == 1:
            choices = [str(value[0]) for value in self.values]
        else:
            choices = [str(value[1]) for value in self.values]

        layout = QVBoxLayout(self)

        st = QLabel(label, self)
        st.setAlignment(Qt.AlignCenter)
        layout.addWidget(st)

        self.items_panel = _ItemsPanel(self, choices)
        layout.addWidget(self.items_panel, 1)

        self.reset_button = QPushButton('Reset', self)
        self.reset_button.clicked.connect(self._on_reset)
        layout.addWidget(self.reset_button, 0, Qt.AlignRight)

        # Forward checkbox changes upward
        for row in self.items_panel.items:
            row.ctrl.stateChanged.connect(lambda _: self.changed.emit())

    def _on_reset(self):
        self.items_panel.Reset()
        self.changed.emit()

    def GetValues(self) -> dict:
        values = self.items_panel.GetValues()
        res = []
        if len(self.types) == 1:
            type_ = self.types[0]
            for value in values:
                res.append(type_(value.GetName()))
        else:
            type_ = self.types[1]
            for value in values:
                v = type_(value.GetName())
                for row in self.values:
                    if row[1] == v:
                        res.append(row[0])
                        break
        if res:
            return {self.params[0]: res}
        return {}


class _SearchPanel(QScrollArea):
    """Horizontal row of _SearchPanelField columns."""

    def __init__(self, parent,
                 db_table: Union['_global_db.TableBase', '_project_db.PJTTableBase']):
        super().__init__(parent)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setWidgetResizable(True)

        self.parent_panel = parent
        self.db_table = db_table
        self.search_items = db_table.search_items

        self.fields: list[_SearchPanelField] = []
        self.columns: list[str] = []
        self._search_all_parts = False
        self._compat_parts = ()

        container = QWidget()
        layout = QHBoxLayout(container)
        layout.setContentsMargins(4, 4, 4, 4)
        self.setWidget(container)

        for key in sorted(self.search_items.keys()):
            value = self.search_items[key]
            self.columns.append(value['label'])
            if 'search_params' in value:
                field = _SearchPanelField(self, value['label'],
                                          value['search_params'], value['type'])
                self.fields.append(field)
                layout.addWidget(field, 1)
                field.changed.connect(self.on_update)

    def SetSearchAllParts(self, flag: bool):
        self._search_all_parts = flag

    def SetCompatParts(self, *compat_parts):
        self._compat_parts = compat_parts

    def load(self):
        self.on_update()

    def on_update(self):
        cmd = {}
        for field in self.fields:
            cmd.update(field.GetValues())

        if self._search_all_parts:
            con, results = self.db_table.search(self.search_items, **cmd)
        else:
            con, results = self.db_table.search(self.search_items,
                                                *self._compat_parts, **cmd)

        self.parent_panel.SetResults(con, results)


class _ResultCtrl(QTreeWidget):
    """Virtual list control for lazily-fetched search results."""

    def __init__(self, parent, columns: list[str]):
        super().__init__(parent)
        self.parent_panel = parent
        self._selected_db_id = None
        self._loaded_results: list = []
        self.results = None
        self.con = None

        self.setRootIsDecorated(False)
        self.setAlternatingRowColors(True)
        self.setSelectionMode(QAbstractItemView.SingleSelection)

        self.setColumnCount(len(columns))
        self.setHeaderLabels(columns)
        self.header().setSectionResizeMode(QHeaderView.ResizeToContents)

        self.itemSelectionChanged.connect(self._on_selection_changed)
        self.itemActivated.connect(self._on_activated)

    def GetValue(self):
        return self._selected_db_id

    def _on_selection_changed(self):
        items = self.selectedItems()
        if not items:
            return
        item = items[0]
        row = item.data(0, Qt.UserRole)
        if row is None:
            return
        db_id = row[0]
        self._selected_db_id = db_id
        obj = self.parent_panel.table[db_id]
        self.parent_panel.set_image(obj.image)

    def _on_activated(self, item, _column):
        row = item.data(0, Qt.UserRole)
        if row is None:
            return
        db_id = row[0]
        self._selected_db_id = db_id
        top = self.window()
        if hasattr(top, 'accept'):
            top.accept()

    def SetValues(self, con, results):
        self.clear()
        self._loaded_results = []
        self.con = con

        count = results[0]
        first_row = results[1:]
        if first_row and first_row[0] is not None:
            self._append_row(first_row)

        # Lazily load remaining rows when the user scrolls
        # (Qt's QTreeWidget is not truly virtual; load all rows eagerly for
        # correctness — the DB cursor is held open and consumed on demand)
        self._load_remaining(count)

    def _append_row(self, row):
        item = QTreeWidgetItem([str(col) for col in row[1:]])
        item.setData(0, Qt.UserRole, row)
        self.addTopLevelItem(item)
        self._loaded_results.append(row)

    def _load_remaining(self, count: int):
        if self.con is None:
            return
        while len(self._loaded_results) < count:
            line = self.con.fetchone()
            if line is None:
                break
            self._append_row(line)


class SearchPanel(QWidget):
    """Top-level composite search widget.

    Emits search_changed() whenever the result selection changes.
    """

    search_changed = Signal()

    def __init__(self, parent=None, table=None, *compat_parts):
        super().__init__(parent)

        self.parent_panel = parent
        self.table = table
        self._object = None

        self.search_panel = _SearchPanel(self, table)
        self.result_ctrl = _ResultCtrl(self, self.search_panel.columns)
        self.image_ctrl = QLabel(self)
        self.image_ctrl.setFixedSize(600, 480)
        self.image_ctrl.setAlignment(Qt.AlignCenter)

        self._search_all_parts = QCheckBox('Search All Parts', self)
        self._search_all_parts.stateChanged.connect(self._on_search_all_parts)

        if not compat_parts:
            self._search_all_parts.setChecked(True)
            self._search_all_parts.setEnabled(False)
            self.search_panel.SetSearchAllParts(True)
        else:
            self.search_panel.SetCompatParts(*compat_parts)
            self.search_panel.SetSearchAllParts(False)

        left = QVBoxLayout()
        left.addWidget(self.search_panel)
        left.addWidget(self._search_all_parts)
        left.addWidget(self.result_ctrl)

        right = QVBoxLayout()
        right.addWidget(self.image_ctrl)

        main = QHBoxLayout(self)
        main.addLayout(left, 1)
        main.addLayout(right, 1)

        self.search_panel.load()

    def _on_search_all_parts(self, state: int):
        self.search_panel.SetSearchAllParts(bool(state))
        self.search_panel.load()

    def set_image(self, image):
        if image is None:
            self.image_ctrl.setPixmap(QPixmap())
        else:
            pm = QPixmap(image.data_path)
            self.image_ctrl.setPixmap(
                pm.scaled(self.image_ctrl.size(), Qt.KeepAspectRatio,
                          Qt.SmoothTransformation))

    def SetResults(self, con, results):
        self.result_ctrl.SetValues(con, results)

    def GetValue(self):
        return self.result_ctrl.GetValue()
