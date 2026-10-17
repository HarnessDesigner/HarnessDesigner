# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

"""A JSON response as a tree you can click values in.

Select one or more rows (Ctrl/Shift-click), optionally rename the variable
each will be assigned to, and ask for the code. Rows that live inside an
array can be extracted from every element of the array instead of just the
one that was clicked.
"""

from collections.abc import Callable

import json

from PySide6 import QtCore
from PySide6 import QtWidgets

from ...scraping import json_extract as _json_extract
from ...scraping import snippets as _snippets
from ... import check_types as _check_types

Path = _json_extract.Path

# A very large array is shown in part: building 100,000 rows would freeze
# the window for nothing.
_MAX_CHILDREN = 2000
_MAX_VALUE_CHARS = 120

_PATH_ROLE = QtCore.Qt.ItemDataRole.UserRole
_KIND_ROLE = QtCore.Qt.ItemDataRole.UserRole + 1
_PLACEHOLDER = 'placeholder'
_CONTAINER = 'container'
_LEAF = 'leaf'
_NOTICE = 'notice'


@_check_types.do
def _no_names() -> set[str]:
    return set()


class _NameDelegate(QtWidgets.QStyledItemDelegate):
    """Only the variable-name column is editable."""

    def createEditor(self, parent: QtWidgets.QWidget, option: QtWidgets.QStyleOptionViewItem,  # NOQA
                     index: QtCore.QModelIndex) -> QtWidgets.QWidget | None:
        if index.column() != 2:
            return None

        return super().createEditor(parent, option, index)


class JsonTree(QtWidgets.QTreeWidget):
    """:ivar snippetReady: Code was produced (``Snippet``); if the script
        has no ``data`` variable yet the snippet that loads it is emitted
        first.
    :ivar messageRaised: Something the user should be told (``str``).
    """

    snippetReady = QtCore.Signal(object)
    messageRaised = QtCore.Signal(str)

    @_check_types.do
    def __init__(self, parent: QtWidgets.QWidget | None = None) -> None:
        super().__init__(parent)
        self._value: object = None
        self._root_name = 'data'
        self._taken_provider: Callable[[], set[str]] = _no_names
        self._preamble: Callable[[set[str]], _snippets.Snippet | None] | None = None

        self.setColumnCount(3)
        self.setHeaderLabels(['Key', 'Value', 'Variable name'])
        self.setSelectionMode(QtWidgets.QAbstractItemView.SelectionMode.ExtendedSelection)
        self.setAlternatingRowColors(True)
        self.setUniformRowHeights(True)
        self.setItemDelegate(_NameDelegate(self))
        self.setEditTriggers(QtWidgets.QAbstractItemView.EditTrigger.DoubleClicked)
        self.setContextMenuPolicy(QtCore.Qt.ContextMenuPolicy.CustomContextMenu)

        self.itemExpanded.connect(self._populate)
        self.customContextMenuRequested.connect(self._show_menu)

    # -- public ------------------------------------------------------------

    @_check_types.do
    def set_taken_provider(self, provider: Callable[[], set[str]]) -> None:
        self._taken_provider = provider

    @_check_types.do
    def set_preamble(self, preamble: Callable[[set[str]], _snippets.Snippet | None] | None) -> None:
        """A function making the snippet that defines the JSON variable,
        used when the script does not have it yet."""
        self._preamble = preamble

    @_check_types.do
    def set_value(self, value: object, root_name: str = 'data') -> None:
        self.clear()
        self._value = value
        self._root_name = root_name

        root = self._make_item(root_name, (), value)
        self.addTopLevelItem(root)
        root.setExpanded(True)

    @_check_types.do
    def selected_paths(self) -> list[Path]:
        """Paths of the selected rows, root row excluded, in tree order."""
        paths: list[Path] = []
        for item in self.selectedItems():
            kind = item.data(0, _KIND_ROLE)
            path = self._path_of(item)
            if kind in (_LEAF, _CONTAINER) and path:
                paths.append(path)

        paths.sort(key=lambda path: self._order_key(path))
        return paths

    @_check_types.do
    def extract_selected(self, every_item: bool = False) -> bool:
        """Emit extraction code for the selected rows. Returns whether any
        code was produced."""
        items = self._selected_items()
        if not items:
            self.messageRaised.emit('Select one or more values first (Ctrl-click to select several).')
            return False

        taken = self._taken_provider()
        if self._root_name not in taken and self._preamble is not None:
            preamble = self._preamble(taken)
            if preamble is not None:
                self.snippetReady.emit(preamble)
                taken = self._taken_provider()

        names = _snippets.Names(taken)
        paths_with_names: list[tuple[Path, str]] = []
        for item in items:
            wanted = item.text(2).strip() or _json_extract.suggest_name(self._path_of(item))
            paths_with_names.append((self._path_of(item), names.new(wanted)))

        try:
            snippet = _json_extract.snippet_for(paths_with_names, self._root_name, every_item)
        except ValueError as error:
            self.messageRaised.emit(str(error))
            return False

        self.snippetReady.emit(snippet)
        return True

    @_check_types.do
    def can_extract_every_item(self) -> bool:
        """Whether the selection sits in one array (so "every item" works)."""
        paths = self.selected_paths()
        if not paths:
            return False

        try:
            _json_extract.generate_extraction_code([(path, 'x') for path in paths], self._root_name, True)
        except ValueError:
            return False

        return True

    # -- tree --------------------------------------------------------------

    @_check_types.do
    def _make_item(self, key: str, path: Path, value: object) -> QtWidgets.QTreeWidgetItem:
        item = QtWidgets.QTreeWidgetItem([key, self._summary(value), ''])
        item.setData(0, _PATH_ROLE, list(path))

        if isinstance(value, (dict, list)) and value:
            item.setData(0, _KIND_ROLE, _CONTAINER)
            placeholder = QtWidgets.QTreeWidgetItem(['', '', ''])
            placeholder.setData(0, _KIND_ROLE, _PLACEHOLDER)
            item.addChild(placeholder)
        else:
            item.setData(0, _KIND_ROLE, _LEAF)

        if path:
            item.setText(2, _json_extract.suggest_name(path))
            item.setFlags(item.flags() | QtCore.Qt.ItemFlag.ItemIsEditable)

        return item

    @_check_types.do
    def _populate(self, item: QtWidgets.QTreeWidgetItem) -> None:
        if item.childCount() != 1 or item.child(0).data(0, _KIND_ROLE) != _PLACEHOLDER:
            return

        item.takeChild(0)
        path = self._path_of(item)
        value = self._value_at(path)

        if isinstance(value, dict):
            entries = [(str(key), key, child) for key, child in value.items()]
        else:
            entries = [(f'[{index}]', index, child) for index, child in enumerate(value)]

        for label, step, child in entries[:_MAX_CHILDREN]:
            item.addChild(self._make_item(label, path + (step,), child))

        if len(entries) > _MAX_CHILDREN:
            notice = QtWidgets.QTreeWidgetItem(['', f'... {len(entries) - _MAX_CHILDREN} more not shown', ''])
            notice.setData(0, _KIND_ROLE, _NOTICE)
            notice.setFlags(QtCore.Qt.ItemFlag.ItemIsEnabled)
            item.addChild(notice)

    @_check_types.do
    def _path_of(self, item: QtWidgets.QTreeWidgetItem) -> Path:
        return tuple(item.data(0, _PATH_ROLE) or ())

    @_check_types.do
    def _value_at(self, path: Path) -> object:
        value = self._value
        for step in path:
            value = value[step]

        return value

    @_check_types.do
    def _selected_items(self) -> list[QtWidgets.QTreeWidgetItem]:
        items = [item for item in self.selectedItems()
                 if item.data(0, _KIND_ROLE) in (_LEAF, _CONTAINER) and self._path_of(item)]
        items.sort(key=lambda item: self._order_key(self._path_of(item)))
        return items

    @_check_types.do
    def _order_key(self, path: Path) -> tuple[tuple[int, str | int], ...]:
        """Sort key giving document order (indices numerically, keys in
        the order the object lists them)."""
        key: list[tuple[int, str | int]] = []
        value = self._value
        for step in path:
            if isinstance(value, dict):
                key.append((0, list(value.keys()).index(step)))
            else:
                key.append((0, step))

            value = value[step]

        return tuple(key)

    @_check_types.do
    def _summary(self, value: object) -> str:
        if isinstance(value, dict):
            return f'{{{len(value)} key(s)}}'

        if isinstance(value, list):
            return f'[{len(value)} item(s)]'

        text = json.dumps(value, ensure_ascii=False)
        if len(text) > _MAX_VALUE_CHARS:
            text = text[:_MAX_VALUE_CHARS] + '...'

        return text

    # -- menu --------------------------------------------------------------

    @_check_types.do
    def _show_menu(self, position: QtCore.QPoint) -> None:
        item = self.itemAt(position)
        if item is not None and not item.isSelected():
            self.clearSelection()
            item.setSelected(True)

        paths = self.selected_paths()
        menu = QtWidgets.QMenu(self)

        if not paths:
            hint = menu.addAction('Select a value first')
            hint.setEnabled(False)
            menu.exec(self.viewport().mapToGlobal(position))
            return

        count = len(paths)
        extract = menu.addAction(f'Extract {count} selected value(s) into variables')
        extract.triggered.connect(lambda: self.extract_selected(False))

        every = menu.addAction('Extract from every item of the array')
        every.setEnabled(self.can_extract_every_item())
        every.triggered.connect(lambda: self.extract_selected(True))

        menu.addSeparator()
        copy_value = menu.addAction('Copy value')
        copy_value.triggered.connect(lambda: self._copy_value(paths[0]))
        copy_path = menu.addAction('Copy path as Python')
        copy_path.triggered.connect(lambda: self._copy_path(paths[0]))

        menu.exec(self.viewport().mapToGlobal(position))

    @_check_types.do
    def _copy_value(self, path: Path) -> None:
        value = self._value_at(path)
        if isinstance(value, str):
            text = value
        else:
            text = json.dumps(value, ensure_ascii=False, indent=2)

        QtWidgets.QApplication.clipboard().setText(text)

    @_check_types.do
    def _copy_path(self, path: Path) -> None:
        QtWidgets.QApplication.clipboard().setText(_json_extract.format_path_access(path, self._root_name))
