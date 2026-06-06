# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

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
        """Initialise the :class:`_ItemRow` instance.

        UNKNOWN details are inferred from the callable name and signature.

        :param parent: Parent object.
        :type parent: UNKNOWN
        :param label: Value for ``label``.
        :type label: str
        """
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(2, 2, 2, 2)
        self.st = QLabel(label, self)
        self.ctrl = QCheckBox(self)
        layout.addWidget(self.st, 0)
        layout.addWidget(self.ctrl, 0)

    def GetValue(self) -> bool:
        """Execute the get value operation.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Return value. UNKNOWN details.
        :rtype: bool
        """
        return self.ctrl.isChecked()

    def GetName(self) -> str:
        """Execute the get name operation.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Return value. UNKNOWN details.
        :rtype: str
        """
        return self.st.text()


class _ItemsPanel(QScrollArea):
    """Scrollable list of label + checkbox rows."""

    def __init__(self, parent, choices: list[str]):
        """Initialise the :class:`_ItemsPanel` instance.

        UNKNOWN details are inferred from the callable name and signature.

        :param parent: Parent object.
        :type parent: UNKNOWN
        :param choices: Value for ``choices``.
        :type choices: list[str]
        """
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
        """Execute the reset operation.

        UNKNOWN details are inferred from the callable name and signature.
        """
        for item in self.items:
            item.ctrl.setChecked(False)

    def GetValues(self) -> list[_ItemRow]:
        """Execute the get values operation.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Return value. UNKNOWN details.
        :rtype: list[_ItemRow]
        """
        return [item for item in self.items if item.GetValue()]


class _SearchPanelField(QFrame):
    """A titled, scrollable checkbox list for one search dimension."""

    changed = Signal()

    def __init__(self, parent, label: str, params, types):
        """Initialise the :class:`_SearchPanelField` instance.

        UNKNOWN details are inferred from the callable name and signature.

        :param parent: Parent object.
        :type parent: UNKNOWN
        :param label: Value for ``label``.
        :type label: str
        :param params: Value for ``params``.
        :type params: UNKNOWN
        :param types: Value for ``types``.
        :type types: UNKNOWN
        """
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
        """Handle the reset event.

        UNKNOWN details are inferred from the callable name and signature.
        """
        self.items_panel.Reset()
        self.changed.emit()

    def GetValues(self) -> dict:
        """Execute the get values operation.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Return value. UNKNOWN details.
        :rtype: dict
        """
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
        """Initialise the :class:`_SearchPanel` instance.

        UNKNOWN details are inferred from the callable name and signature.

        :param parent: Parent object.
        :type parent: UNKNOWN
        :param db_table: Value for ``db_table``.
        :type db_table: Union['_global_db.TableBase', '_project_db.PJTTableBase']
        """
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
        """Execute the set search all parts operation.

        UNKNOWN details are inferred from the callable name and signature.

        :param flag: Value for ``flag``.
        :type flag: bool
        """
        self._search_all_parts = flag

    def SetCompatParts(self, *compat_parts):
        """Execute the set compat parts operation.

        UNKNOWN details are inferred from the callable name and signature.

        :param compat_parts: Value for ``compat_parts``.
        :type compat_parts: UNKNOWN
        """
        self._compat_parts = compat_parts

    def load(self):
        """Execute the load operation.

        UNKNOWN details are inferred from the callable name and signature.
        """
        self.on_update()

    def on_update(self):
        """Handle the update event.

        UNKNOWN details are inferred from the callable name and signature.
        """
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
        """Initialise the :class:`_ResultCtrl` instance.

        UNKNOWN details are inferred from the callable name and signature.

        :param parent: Parent object.
        :type parent: UNKNOWN
        :param columns: Value for ``columns``.
        :type columns: list[str]
        """
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
        """Execute the get value operation.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Return value. UNKNOWN details.
        :rtype: UNKNOWN
        """
        return self._selected_db_id

    def _on_selection_changed(self):
        """Handle the selection changed event.

        UNKNOWN details are inferred from the callable name and signature.
        """
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
        """Handle the activated event.

        UNKNOWN details are inferred from the callable name and signature.

        :param item: Item identifier or value.
        :type item: UNKNOWN
        :param _column: Value for ``column``.
        :type _column: UNKNOWN
        """
        row = item.data(0, Qt.UserRole)
        if row is None:
            return
        db_id = row[0]
        self._selected_db_id = db_id
        top = self.window()
        if hasattr(top, 'accept'):
            top.accept()

    def SetValues(self, con, results):
        """Execute the set values operation.

        UNKNOWN details are inferred from the callable name and signature.

        :param con: Value for ``con``.
        :type con: UNKNOWN
        :param results: Value for ``results``.
        :type results: UNKNOWN
        """
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
        """Execute the append row operation.

        UNKNOWN details are inferred from the callable name and signature.

        :param row: Value for ``row``.
        :type row: UNKNOWN
        """
        item = QTreeWidgetItem([str(col) for col in row[1:]])
        item.setData(0, Qt.UserRole, row)
        self.addTopLevelItem(item)
        self._loaded_results.append(row)

    def _load_remaining(self, count: int):
        """Load the remaining.

        UNKNOWN details are inferred from the callable name and signature.

        :param count: Count value.
        :type count: int
        """
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
        """Initialise the :class:`SearchPanel` instance.

        UNKNOWN details are inferred from the callable name and signature.

        :param parent: Parent object.
        :type parent: UNKNOWN
        :param table: Value for ``table``.
        :type table: UNKNOWN
        :param compat_parts: Value for ``compat_parts``.
        :type compat_parts: UNKNOWN
        """
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
        """Handle the search all parts event.

        UNKNOWN details are inferred from the callable name and signature.

        :param state: Value for ``state``.
        :type state: int
        """
        self.search_panel.SetSearchAllParts(bool(state))
        self.search_panel.load()

    def set_image(self, image):
        """Set the image.

        UNKNOWN details are inferred from the callable name and signature.

        :param image: Value for ``image``.
        :type image: UNKNOWN
        """
        if image is None:
            self.image_ctrl.setPixmap(QPixmap())
        else:
            pm = QPixmap(image.data_path)
            self.image_ctrl.setPixmap(
                pm.scaled(self.image_ctrl.size(), Qt.KeepAspectRatio,
                          Qt.SmoothTransformation))

    def SetResults(self, con, results):
        """Execute the set results operation.

        UNKNOWN details are inferred from the callable name and signature.

        :param con: Value for ``con``.
        :type con: UNKNOWN
        :param results: Value for ``results``.
        :type results: UNKNOWN
        """
        self.result_ctrl.SetValues(con, results)

    def GetValue(self):
        """Execute the get value operation.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Return value. UNKNOWN details.
        :rtype: UNKNOWN
        """
        return self.result_ctrl.GetValue()
