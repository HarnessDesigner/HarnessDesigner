# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

from typing import TYPE_CHECKING
from collections.abc import Callable

from PySide6 import QtCore
from PySide6 import QtWidgets

from . import editor_pages as _editor_pages
from . import general_pages as _general_pages
from . import input_pages as _input_pages
from . import page_base as _page_base
from .. import dialog_base as _dialog_base
from .... import check_types as _check_types


if TYPE_CHECKING:
    from .... import ui as _ui


_PanelFactory = Callable[[QtWidgets.QWidget | None, "_ui.MainFrame"], QtWidgets.QWidget]

# The panel a tree item shows, by key. Several tree items can share one
# panel (the three children of Mouse all show the Mouse notebook).
_FACTORIES: dict[str, _PanelFactory] = {
    'appearance': _general_pages.AppearancePage,
    'pointer': _general_pages.PointerPage,
    'project': _general_pages.project_page,
    'logging': _general_pages.logging_page,
    'resources': _general_pages.resources_page,
    'database': _general_pages.database_page,
    'graphics': _general_pages.GraphicsPage,
    'mouse': _input_pages.build_mouse_panel,
    'keyboard': _input_pages.build_keyboard_panel,
    'editor_3d': _editor_pages.editor_3d_page,
    'editor_pegboard': _editor_pages.editor_pegboard_page,
    'editor_schematic': _editor_pages.editor_schematic_page,
    'placement_colors': _general_pages.placement_colors_page,
    'bundles': _general_pages.bundles_page,
    'ray_tracing': _general_pages.RayTracingPage
}


class _Node:
    """One tree item: its title, the panel it shows (``None`` for a heading
    that only groups its children), the notebook tab to bring forward in
    that panel, and its children."""

    @_check_types.do
    def __init__(self, title: str, key: str | None = None, tab: int | None = None,
                 children: list["_Node"] | None = None):
        self.title = title
        self.key = key
        self.tab = tab

        if children is None:
            children = []

        self.children = children


@_check_types.do
def _editor_tabs(key: str) -> list[_Node]:
    """One child per editor tab, in the order the notebook's tabs are."""
    return [_Node(title, key, index)
            for index, (_, title) in enumerate(_input_pages.EDITORS)]


_TREE: list[_Node] = [
    _Node('General', children=[
        _Node('Appearance', 'appearance'),
        _Node('Pointer and Touch', 'pointer'),
        _Node('Project', 'project'),
        _Node('Logging', 'logging'),
        _Node('Models and Resources', 'resources'),
        _Node('Database', 'database')
    ]),
    _Node('Graphics', 'graphics'),
    _Node('Mouse', 'mouse', children=_editor_tabs('mouse')),
    _Node('Keyboard', 'keyboard', children=_editor_tabs('keyboard')),
    _Node('Editors', children=[
        _Node('3D Editor', 'editor_3d'),
        _Node('Pegboard Editor', 'editor_pegboard'),
        _Node('Schematic Editor', 'editor_schematic')
    ]),
    _Node('Placement Colors', 'placement_colors'),
    _Node('Bundles', 'bundles'),
    _Node('Ray Tracing', 'ray_tracing')
]


class PreferencesDialog(_dialog_base.BaseDialog):
    """The application's preferences: a tree of topics on the left and the
    settings of the selected topic on the right.

    A panel is built the first time its topic is selected, in full: the
    Mouse and Keyboard notebooks have all their tabs from the start, whichever
    of their tree items opened them, and the tab matching the item that was
    clicked is brought forward. Nothing is written to ``Config`` until
    :meth:`SetValues` (OK or Apply); only the panels that were opened are
    written.
    """

    @_check_types.do
    def __init__(self, parent: "_ui.MainFrame"):
        buttons = (QtWidgets.QDialogButtonBox.StandardButton.Ok |
                   QtWidgets.QDialogButtonBox.StandardButton.Cancel |
                   QtWidgets.QDialogButtonBox.StandardButton.Apply)

        super().__init__(parent, 'Preferences', size=(1000, 720), button_ids=buttons)

        self._panels: dict[str, QtWidgets.QWidget] = {}

        self.tree = QtWidgets.QTreeWidget(self.panel)
        self.tree.setHeaderHidden(True)
        self.tree.setMinimumWidth(200)

        self.stack = QtWidgets.QStackedWidget(self.panel)

        splitter = QtWidgets.QSplitter(QtCore.Qt.Orientation.Horizontal, self.panel)
        splitter.addWidget(self.tree)
        splitter.addWidget(self.stack)
        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)
        splitter.setSizes([230, 770])

        layout = QtWidgets.QVBoxLayout(self.panel)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(splitter)

        self._add_nodes(self.tree.invisibleRootItem(), _TREE)

        self.tree.currentItemChanged.connect(self._on_item_changed)
        self.button_box.button(
            QtWidgets.QDialogButtonBox.StandardButton.Apply).clicked.connect(
            self.SetValues)

        # Start on the first topic.
        general = self.tree.topLevelItem(0)
        general.setExpanded(True)
        self.tree.setCurrentItem(general.child(0))

    @_check_types.do
    def _add_nodes(self, parent_item: QtWidgets.QTreeWidgetItem, nodes: list[_Node]) -> None:
        for node in nodes:
            item = QtWidgets.QTreeWidgetItem(parent_item, [node.title])
            item.setData(0, QtCore.Qt.ItemDataRole.UserRole, (node.key, node.tab))

            self._add_nodes(item, node.children)

    @_check_types.do
    def _panel(self, key: str) -> QtWidgets.QWidget:
        """The panel for *key*, built (in full) the first time it is asked for."""
        panel = self._panels.get(key)

        if panel is None:
            panel = _FACTORIES[key](self.stack, self.mainframe)
            self._panels[key] = panel
            self.stack.addWidget(panel)

        return panel

    @_check_types.do
    def _on_item_changed(self, current: QtWidgets.QTreeWidgetItem | None,
                         previous: QtWidgets.QTreeWidgetItem | None) -> None:
        if current is None:
            return

        key, tab = current.data(0, QtCore.Qt.ItemDataRole.UserRole)

        # A heading with no panel of its own: open it and show its first topic.
        if key is None:
            current.setExpanded(True)
            self.tree.setCurrentItem(current.child(0))
            return

        panel = self._panel(key)
        self.stack.setCurrentWidget(panel)

        if tab is not None and isinstance(panel, _page_base.TabbedPanel):
            panel.set_tab(tab)

    @_check_types.do
    def SetValues(self) -> None:
        """Write every changed setting of the panels that were opened to
        ``Config``, then say which of them need a restart."""
        restart: list[str] = []

        for panel in self._panels.values():
            restart.extend(panel.apply())  # NOQA

        if not restart:
            return

        names = '\n'.join(f'    {name}' for name in dict.fromkeys(restart))

        QtWidgets.QMessageBox.information(
            self.mainframe, 'Restart needed',
            'These settings take effect after Harness Designer is '
            f'restarted:\n\n{names}')
