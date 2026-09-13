# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

from typing import TYPE_CHECKING

from PySide6 import QtCore
from PySide6 import QtWidgets

import re
import weakref

from ...objects import boot as _boot
from ...objects import bundle as _bundle
from ...objects import cavity as _cavity
from ...objects import circuit as _circuit
from ...objects import cover as _cover
from ...objects import cpa_lock as _cpa_lock
from ...objects import housing as _housing
from ...objects import note as _note
from ...objects import seal as _seal
from ...objects import splice as _splice
from ...objects import terminal as _terminal
from ...objects import tpa_lock as _tpa_lock
from ...objects import transition as _transition
from ...objects import wire as _wire
from ...objects import wire_marker as _wire_marker
from ...objects import wire_service_loop as _wire_service_loop

from .. import dock_base as _dock_base
from ... import check_types as _check_types

if TYPE_CHECKING:
    from .. import mainframe as _mainframe
    from ...objects import object_base as _object_base


# Matches a ':' or '.' used as a search path level marker -- only when it
# has no adjacent whitespace, which is what distinguishes a marker from a
# literal character in a name (e.g. "Housing 1.5"). See
# ObjectBrowserPanel._split_path_query.
_PATH_SEPARATOR_RE = re.compile(r'(?<=\S)[:.](?=\S)')


class ObjectBrowser(_dock_base.DockBase):
    """
    Represent an object browser in :mod:`harness_designer.ui.object_browser.objectbrowser`.
    """

    @_check_types.do
    def __init__(self, mainframe: "_mainframe.MainFrame"):
        """
        Initialise the :class:`ObjectBrowser` instance.

        :param mainframe: Main application frame.
        :type mainframe: :class:`_mainframe.MainFrame`
        """

        self._ui_obj = ObjectBrowserPanel(mainframe)
        super().__init__(mainframe, 'Object Browser', 'object_browser',
                         QtCore.Qt.DockWidgetArea.LeftDockWidgetArea)

    @_check_types.do
    def add_boot(self, obj: _boot.Boot):
        """
        Add a boot.

        :param obj: Object instance to operate on.
        :type obj: :class:`_boot.Boot`
        """

        self._ui_obj.add_boot(obj)

    @_check_types.do
    def add_bundle(self, obj: _bundle.Bundle):
        """
        Add a bundle.

        :param obj: Object instance to operate on.
        :type obj: :class:`_bundle.Bundle`
        """

        self._ui_obj.add_bundle(obj)

    @_check_types.do
    def add_cavity(self, obj: _cavity.Cavity):
        """
        Add a cavity.

        :param obj: Object instance to operate on.
        :type obj: :class:`_cavity.Cavity`
        """

        self._ui_obj.add_cavity(obj)

    @_check_types.do
    def add_circuit(self, obj: _circuit.Circuit):
        """
        Add a circuit.

        :param obj: Object instance to operate on.
        :type obj: :class:`_circuit.Circuit`
        """

        self._ui_obj.add_circuit(obj)

    @_check_types.do
    def add_cover(self, obj: _cover.Cover):
        """
        Add a cover.

        :param obj: Object instance to operate on.
        :type obj: :class:`_cover.Cover`
        """

        self._ui_obj.add_cover(obj)

    @_check_types.do
    def add_cpa_lock(self, obj: _cpa_lock.CPALock):
        """
        Add a CPA lock.

        :param obj: Object instance to operate on.
        :type obj: :class:`_cpa_lock.CPALock`
        """

        self._ui_obj.add_cpa_lock(obj)

    @_check_types.do
    def add_housing(self, obj: _housing.Housing):
        """
        Add a housing.

        :param obj: Object instance to operate on.
        :type obj: :class:`_housing.Housing`
        """

        self._ui_obj.add_housing(obj)

    @_check_types.do
    def add_note(self, obj: _note.Note):
        """
        Add a note.

        :param obj: Object instance to operate on.
        :type obj: :class:`_note.Note`
        """

        self._ui_obj.add_note(obj)

    @_check_types.do
    def add_seal(self, obj: _seal.Seal):
        """
        Add a seal.

        :param obj: Object instance to operate on.
        :type obj: :class:`_seal.Seal`
        """

        self._ui_obj.add_seal(obj)

    @_check_types.do
    def add_splice(self, obj: _splice.Splice):
        """
        Add a splice.

        :param obj: Object instance to operate on.
        :type obj: :class:`_splice.Splice`
        """

        self._ui_obj.add_splice(obj)

    @_check_types.do
    def add_terminal(self, obj: _terminal.Terminal):
        """
        Add a terminal.

        :param obj: Object instance to operate on.
        :type obj: :class:`_terminal.Terminal`
        """

        self._ui_obj.add_terminal(obj)

    @_check_types.do
    def add_tpa_lock(self, obj: _tpa_lock.TPALock):
        """
        Add a TPA lock.

        :param obj: Object instance to operate on.
        :type obj: :class:`_tpa_lock.TPALock`
        """

        self._ui_obj.add_tpa_lock(obj)

    @_check_types.do
    def add_transition(self, obj: _transition.Transition):
        """
        Add a transition.

        :param obj: Object instance to operate on.
        :type obj: :class:`_transition.Transition`
        """

        self._ui_obj.add_transition(obj)

    @_check_types.do
    def add_wire(self, obj: _wire.Wire):
        """
        Add a wire.

        :param obj: Object instance to operate on.
        :type obj: :class:`_wire.Wire`
        """

        self._ui_obj.add_wire(obj)

    @_check_types.do
    def add_wire_marker(self, obj: _wire_marker.WireMarker):
        """
        Add a wire marker.

        :param obj: Object instance to operate on.
        :type obj: :class:`_wire_marker.WireMarker`
        """

        self._ui_obj.add_wire_marker(obj)

    @_check_types.do
    def add_wire_service_loop(self, obj: _wire_service_loop.WireServiceLoop):
        """
        Add a wire service loop.

        :param obj: Object instance to operate on.
        :type obj: :class:`_wire_service_loop.WireServiceLoop`
        """

        self._ui_obj.add_wire_service_loop(obj)

    @_check_types.do
    def reset(self):
        """
        Execute the reset operation.
        """

        self._ui_obj.reset()

    @_check_types.do
    def set_selected(self, obj):
        """
        Set the selected.

        :param obj: Object instance to operate on.
        :type obj: UNKNOWN
        """

        self._ui_obj.set_selected(obj)

    @_check_types.do
    def add_object(self, obj):
        """
        Add an object.

        :param obj: Object instance to operate on.
        :type obj: UNKNOWN
        """

        self._ui_obj.add_object(obj)

    @_check_types.do
    def remove_object(self, obj):
        """
        Remove the object.

        :param obj: Object instance to operate on.
        :type obj: UNKNOWN
        """

        self._ui_obj.remove_object(obj)

    @property
    @_check_types.do
    def editor(self) -> "ObjectBrowserPanel":
        return self._ui_obj


class _BrowserTree(QtWidgets.QTreeWidget):
    """
    Tree widget backing :class:`ObjectBrowserPanel`.

    Moving to a different item -- by clicking it *or* by arrow-key
    navigation, Qt fires the same :attr:`currentItemChanged` signal either
    way -- selects that item's object in every editor, but only after a
    short delay. This does double duty:

    * A double click is delivered by Qt as a normal press first (see the
      identical problem/solution in :class:`~..editor_db.base.EditorList`),
      so without the delay a double click would select the object (swapping
      whatever is shown in the object editor dock) an instant before opening
      the properties dialog for it -- exactly the interaction Kevin wants
      kept apart. The wait reuses :attr:`EditorDBConfig.double_click_average`,
      the same learned double-click speed :class:`EditorList` maintains, so
      the feel is consistent app-wide instead of a second hand-picked
      constant.
    * Holding an arrow key re-fires ``currentItemChanged`` for every row
      passed over; restarting the same timer on each one means only the row
      the user actually stops on ends up selected/re-centered, instead of
      every transient row along the way.
    """

    _SELECT_MARGIN = 1.5
    _SELECT_MIN_MS = 150

    @_check_types.do
    def __init__(self, panel: "ObjectBrowserPanel"):
        """
        Initialise the :class:`_BrowserTree` instance.

        :param panel: Owning panel, used to resolve tree items to objects.
        :type panel: :class:`ObjectBrowserPanel`
        """

        super().__init__(panel)
        self._panel = panel
        self._pending_ref = None
        self._suspend_current_changed = False

        self._select_timer = QtCore.QTimer(self)
        self._select_timer.setSingleShot(True)
        self._select_timer.timeout.connect(self._fire_pending_select)  # NOQA

        self.currentItemChanged.connect(self._on_current_item_changed)  # NOQA

    @_check_types.do
    def set_current_item_silently(self, item) -> None:
        """
        Move the tree's current item without arming the deferred
        cross-editor select. Qt's ``currentItemChanged`` fires for a
        programmatic ``setCurrentItem`` exactly the same as for a real
        click or arrow-key press -- there is no way to tell them apart
        from inside the signal itself. Used by ``ObjectBrowserPanel.
        _focus_item`` (driven by ``set_selected``, reflecting a selection
        that already happened elsewhere, not a fresh click of the user's
        own) so that focusing an item programmatically never re-triggers
        :meth:`_on_current_item_changed`'s own timer -- without this, a
        selection already in progress would re-arm itself and fire
        :meth:`_fire_pending_select` again once the wait window passed,
        re-running ``select_object`` for whatever item happened to end up
        current and re-showing the object editor's wait cursor for no
        reason -- confirmed 2026-09-07 (Kevin) as the cause of the busy
        cursor flickering on repeat during a single selection.

        :param item: Item to make current.
        :type item: :class:`QtWidgets.QTreeWidgetItem`
        """

        self._suspend_current_changed = True
        try:
            self.setCurrentItem(item)
        finally:
            self._suspend_current_changed = False

    @_check_types.do
    def _on_current_item_changed(self, current, _previous):
        """
        Schedule (or cancel) the deferred cross-editor select whenever the
        current item changes, from a click or from keyboard navigation.

        :param current: Newly current item, or ``None``.
        :type current: :class:`QtWidgets.QTreeWidgetItem` | None
        :param _previous: Previously current item (unused).
        :type _previous: :class:`QtWidgets.QTreeWidgetItem` | None
        """

        if self._suspend_current_changed:
            return

        self._select_timer.stop()
        self._pending_ref = None

        if current is None:
            return

        ref = current.data(0, QtCore.Qt.ItemDataRole.UserRole)
        if ref is None or ref() is None:
            return

        self._pending_ref = ref
        self._select_timer.start(self._select_wait_ms())

    @_check_types.do
    def mouseDoubleClickEvent(self, event):
        """
        Handle double clicks: cancel the pending select and open the
        properties dialog for the double-clicked object instead.

        :param event: Mouse event.
        :type event: :class:`QtGui.QMouseEvent`
        """

        self._select_timer.stop()
        pending_ref = self._pending_ref
        self._pending_ref = None

        super().mouseDoubleClickEvent(event)

        if (
            event.button() != QtCore.Qt.MouseButton.LeftButton or
            pending_ref is None
        ):
            return

        obj = pending_ref()
        if obj is not None:
            self._panel.open_properties(obj)

    @_check_types.do
    def _fire_pending_select(self):
        """
        Run the deferred select once the double-click window has passed.
        """

        ref = self._pending_ref
        self._pending_ref = None
        if ref is None:
            return

        obj = ref()
        if obj is not None:
            self._panel.select_object(obj)
            self._panel.mainframe.editor2d.Refresh()
            self._panel.mainframe.editor3d.Refresh()
            self._panel.mainframe.editor_pegboard.Refresh()

    @_check_types.do
    def _select_wait_ms(self) -> int:
        """
        Return how long to wait for a possible second click before
        propagating the selection to the other editors.

        :rtype: int
        """

        from ..editor_db.base import EditorDBConfig as _EditorDBConfig

        os_interval = QtWidgets.QApplication.doubleClickInterval()
        avg = _EditorDBConfig.double_click_average

        if not avg:
            return os_interval

        return int(
            min(os_interval, max(self._SELECT_MIN_MS, avg * self._SELECT_MARGIN)))


class TreeItem:

    def __init__(self, browser: "ObjectBrowserPanel",
                 treeitem, obj: "_object_base.ObjectBase"):

        self._treeitem = treeitem
        self._obj = obj
        self._browser = browser
        self._treeitems = []

    def add_treeitem(self, treeitem):
        self._treeitems.append(treeitem)

    @property
    def treeitem(self):
        return self._treeitem

    @property
    def obj(self):
        return self._obj

    def set_selected(self):
        self._browser.set_selected(self._obj)

    def delete(self):
        self._browser.remove_object(self._obj)

        for treeitem in self._treeitems:
            self._browser.remove_treeitem(treeitem)

        self._browser.remove_treeitem(self._treeitem)


class ObjectBrowserPanel(QtWidgets.QWidget):
    """
    Represent an object browser panel in :mod:`harness_designer.ui.object_browser.objectbrowser`.
    """

    # Item data role marking an item as the canonical entry for the object
    # it references -- the one under its category (or, for a wire service
    # loop, under its wire) -- as opposed to a plain-text cross-reference
    # mention nested under a *different* object (e.g. "Housing: X" under a
    # Boot). Search only matches canonical entries; see _mark_canonical.
    _CANONICAL_ROLE = QtCore.Qt.ItemDataRole.UserRole + 1

    # (label shown in the search category dropdown, attribute holding the
    # live category root item) -- built once in reset(), re-read fresh by
    # _category_roots() every search since reset() rebuilds the items.
    _CATEGORY_ATTRS = (
        ('Boots', '_boots'),
        ('Bundles', '_bundles'),
        ('Cavities', '_cavities'),
        ('Circuits', '_circuits'),
        ('Covers', '_covers'),
        ('CPA Locks', '_cpa_locks'),
        ('Housings', '_housings'),
        ('Notes', '_notes'),
        ('Seals', '_seals'),
        ('Splices', '_splices'),
        ('Terminals', '_terminals'),
        ('TPA Locks', '_tpa_locks'),
        ('Transitions', '_transitions'),
        ('Wires', '_wires'),
        ('Wire Markers', '_wire_markers'),
    )

    @_check_types.do
    def __init__(self, parent: "_mainframe.MainFrame"):
        """
        Initialise the :class:`ObjectBrowserPanel` instance.

        :param parent: Parent object.
        :type parent: :class:`_mainframe.MainFrame`
        """

        super().__init__(parent)
        self.mainframe = parent

        self._objects = []
        self._selected = None
        self._search_matches: list[QtWidgets.QTreeWidgetItem] = []
        self._search_index = -1

        self._treectrl = _BrowserTree(self)
        self._treectrl.setHeaderHidden(True)
        self._treectrl.setRootIsDecorated(True)
        self._treectrl.setSelectionMode(
            QtWidgets.QAbstractItemView.SelectionMode.SingleSelection)

        self._search_edit = QtWidgets.QLineEdit(self)
        self._search_edit.setPlaceholderText('Search...')
        self._search_edit.textChanged.connect(self._reset_search)  # NOQA
        self._search_edit.returnPressed.connect(self._on_search_clicked)  # NOQA

        self._search_category = QtWidgets.QComboBox(self)
        self._search_category.addItem('All Categories')
        for label, _attr in self._CATEGORY_ATTRS:
            self._search_category.addItem(label)
        self._search_category.currentIndexChanged.connect(self._reset_search)  # NOQA

        self._search_button = QtWidgets.QPushButton('Search', self)
        self._search_button.clicked.connect(self._on_search_clicked)  # NOQA

        self._search_status = QtWidgets.QLabel('', self)

        self._expand_all_button = QtWidgets.QPushButton('Expand All', self)
        self._expand_all_button.clicked.connect(self._treectrl.expandAll)  # NOQA

        self._collapse_all_button = QtWidgets.QPushButton('Collapse All', self)
        self._collapse_all_button.clicked.connect(self._treectrl.collapseAll)  # NOQA

        search_row = QtWidgets.QHBoxLayout()
        search_row.addWidget(self._search_edit, 1)
        search_row.addWidget(self._search_category)
        search_row.addWidget(self._search_button)

        status_row = QtWidgets.QHBoxLayout()
        status_row.addWidget(self._search_status, 1)
        status_row.addWidget(self._expand_all_button)
        status_row.addWidget(self._collapse_all_button)

        h_layout = QtWidgets.QHBoxLayout()
        v_layout = QtWidgets.QVBoxLayout(self)

        v_layout.addLayout(search_row)
        v_layout.addLayout(status_row)

        h_layout.addWidget(self._treectrl)
        v_layout.addLayout(h_layout)

        self._boots: QtWidgets.QTreeWidgetItem = None
        self._bundles: QtWidgets.QTreeWidgetItem = None
        self._cavities: QtWidgets.QTreeWidgetItem = None
        self._circuits: QtWidgets.QTreeWidgetItem = None
        self._covers: QtWidgets.QTreeWidgetItem = None
        self._cpa_locks: QtWidgets.QTreeWidgetItem = None
        self._housings: QtWidgets.QTreeWidgetItem = None
        self._notes: QtWidgets.QTreeWidgetItem = None
        self._seals: QtWidgets.QTreeWidgetItem = None
        self._splices: QtWidgets.QTreeWidgetItem = None
        self._terminals: QtWidgets.QTreeWidgetItem = None
        self._tpa_locks: QtWidgets.QTreeWidgetItem = None
        self._transitions: QtWidgets.QTreeWidgetItem = None
        self._wires: QtWidgets.QTreeWidgetItem = None
        self._wire_markers: QtWidgets.QTreeWidgetItem = None
        self._weakrefs = []

    @_check_types.do
    def _append_item(self, parent: QtWidgets.QTreeWidgetItem, label: str,  # NOQA
                     has_children: bool = False) -> QtWidgets.QTreeWidgetItem:
        """
        Execute the append item operation.

        :param parent: Parent object.
        :type parent: :class:`QtWidgets.QTreeWidgetItem`

        :param label: Value for ``label``.
        :type label: str

        :param has_children: Boolean flag for whether children is available.
        :type has_children: bool

        :rtype: :class:`QtWidgets.QTreeWidgetItem`
        """

        item = QtWidgets.QTreeWidgetItem(parent, [label])
        if has_children:
            item.setChildIndicatorPolicy(
                QtWidgets.QTreeWidgetItem.ChildIndicatorPolicy.ShowIndicator)

        return item

    @_check_types.do
    def _append_top_level_item(self, label: str,  # NOQA
                               has_children: bool = False) -> QtWidgets.QTreeWidgetItem:
        """
        Same as :meth:`_append_item`, but for a category root -- one of
        the 15 items directly under the tree's own (invisible) root,
        rather than nested under another :class:`QTreeWidgetItem`. Kept
        separate instead of loosening ``_append_item``'s own ``parent``
        annotation, since that method is called far more often with a
        real item parent and this case is rare (only :meth:`reset`).

        :param label: Value for ``label``.
        :type label: str
        :param has_children: Boolean flag for whether children is available.
        :type has_children: bool
        :rtype: :class:`QtWidgets.QTreeWidgetItem`
        """

        item = QtWidgets.QTreeWidgetItem(self._treectrl, [label])
        if has_children:
            item.setChildIndicatorPolicy(
                QtWidgets.QTreeWidgetItem.ChildIndicatorPolicy.ShowIndicator)

        return item

    @property
    @_check_types.do
    def _tree_root(self) -> QtWidgets.QTreeWidgetItem:
        """
        The tree's own invisible root -- its children are exactly the 15
        top-level category items (Boots, Bundles, ...) now that there is
        no visible synthetic "root" item wrapping them. Used only by the
        whole-tree walks (:meth:`remove_treeitem`, :meth:`__remove_refs`,
        :meth:`_find_path_matches`, :meth:`_find_name_matches`) that used
        to start from that synthetic item.

        :rtype: :class:`QtWidgets.QTreeWidgetItem`
        """

        return self._treectrl.invisibleRootItem()

    @_check_types.do
    def reset(self) -> None:
        """
        Execute the reset operation.
        """

        self._treectrl.clear()

        self._boots = self._append_top_level_item('Boots', True)
        self._bundles = self._append_top_level_item('Bundles', True)
        self._cavities = self._append_top_level_item('Cavities', True)
        self._circuits = self._append_top_level_item('Circuits', True)
        self._covers = self._append_top_level_item('Covers', True)
        self._cpa_locks = self._append_top_level_item('CPA Locks', True)
        self._housings = self._append_top_level_item('Housings', True)
        self._notes = self._append_top_level_item('Notes', True)
        self._seals = self._append_top_level_item('Seals', True)
        self._splices = self._append_top_level_item('Splices', True)
        self._terminals = self._append_top_level_item('Terminals', True)
        self._tpa_locks = self._append_top_level_item('TPA Locks', True)
        self._transitions = self._append_top_level_item('Transitions', True)
        self._wires = self._append_top_level_item('Wires', True)
        self._wire_markers = self._append_top_level_item('Wire Markers', True)

        self._weakrefs = []

    def remove_treeitem(self, treeitem):

        def iter_tree(parent: QtWidgets.QTreeWidgetItem):
            """
            Iterate over the tree.

            :param parent: Parent object.
            :type parent: :class:`QtWidgets.QTreeWidgetItem`

            :returns: Iterator or iterable result. UNKNOWN details.
            """

            for i in range(parent.childCount() - 1, -1, -1):
                child = parent.child(i)
                if child == treeitem:
                    parent.removeChild(child)
                elif child.childCount() > 0:
                    iter_tree(child)

        iter_tree(self._tree_root)

    @_check_types.do
    def __remove_refs(self, ref):
        """
        Remove a weakref.
        """

        @_check_types.do
        def iter_tree(parent: QtWidgets.QTreeWidgetItem):
            """
            Iterate over the tree.

            :param parent: Parent object.
            :type parent: :class:`QtWidgets.QTreeWidgetItem`

            :returns: Iterator or iterable result. UNKNOWN details.
            """

            for i in range(parent.childCount() - 1, -1, -1):
                child = parent.child(i)
                d_ref = child.data(0, QtCore.Qt.ItemDataRole.UserRole)
                if d_ref is not None:
                    data = d_ref()
                    if data is None:
                        parent.removeChild(child)
                        continue

                if child.childCount() > 0:
                    iter_tree(child)

        iter_tree(self._tree_root)

        try:
            self._weakrefs.remove(ref)
        except ValueError:
            pass

    @_check_types.do
    def _set_data(self, item: QtWidgets.QTreeWidgetItem, ref):  # NOQA
        """
        Set the data.

        :param item: Item identifier or value.
        :type item: :class:`QtWidgets.QTreeWidgetItem`

        :param ref: Value for ``ref``.
        :type ref: UNKNOWN
        """

        item.setData(0, QtCore.Qt.ItemDataRole.UserRole, ref)

    @_check_types.do
    def _mark_canonical(self, item: QtWidgets.QTreeWidgetItem) -> None:
        """
        Flag ``item`` as an object's canonical entry (see
        :attr:`_CANONICAL_ROLE`) so search can tell it apart from the
        plain-text cross-reference mentions of the same object nested under
        unrelated tree items.

        :param item: Item to flag.
        :type item: :class:`QtWidgets.QTreeWidgetItem`
        """

        item.setData(0, self._CANONICAL_ROLE, True)

    @staticmethod
    def _set_treeitem(db_obj, treeitem):
        obj = db_obj.get_object()

        if obj is None:
            def _set_treeitem(obj_):
                obj_.get_treeitem().add_treeitem(treeitem)

            db_obj.bind_object(_set_treeitem)
        else:
            obj_treeitem = obj.get_treeitem()

            if obj_treeitem is None:
                def _set_treeitem(treeitem_):
                    treeitem_.add_treeitem(treeitem)

                obj.bind_for_treeitem(_set_treeitem)
            else:
                obj_treeitem.add_treeitem(treeitem)

    # ── Reverse-lookup helpers ──────────────────────────────────────────
    # None of these relationships have a FK the "child" side can read
    # directly (a wire doesn't know its own bundle/splice, a bundle
    # doesn't know its own transitions) -- only the "parent" side does
    # (PJTBundle.wires, PJTSplice.wires, PJTTransitionBranch.bundle), so
    # showing them from the child's own tree entry means scanning the
    # project's full list of the parent type. Only run when building the
    # tree (add_*, not a hot path), so an O(n) scan per lookup is fine.

    @_check_types.do
    def _bundles_containing_wire(self, wire_db_obj) -> list:
        """Every bundle (as its ``pjt_bundles`` row) this wire is a
        member of."""
        wire_id = wire_db_obj.db_id
        results = []
        for bundle in self.mainframe.project.bundles:
            bundle_db = bundle.db_obj
            for w in bundle_db.wires:
                if w.db_id == wire_id:
                    results.append(bundle_db)
                    break

        return results

    @_check_types.do
    def _splices_containing_wire(self, wire_db_obj) -> list:
        """Every splice (as its ``pjt_splices`` row) this wire is
        attached to."""
        wire_id = wire_db_obj.db_id
        results = []
        for splice in self.mainframe.project.splices:
            splice_db = splice.db_obj
            for w in splice_db.wires:
                if w.db_id == wire_id:
                    results.append(splice_db)
                    break

        return results

    @_check_types.do
    def _wires_for_terminal(self, terminal_db_obj) -> list:
        """Every wire (as its ``pjt_wires`` row) attached to this
        terminal."""
        terminal_id = terminal_db_obj.db_id
        results = []
        for wire in self.mainframe.project.wires:
            wire_db = wire.db_obj
            for t in wire_db.terminals:
                if t.db_id == terminal_id:
                    results.append(wire_db)
                    break

        return results

    @_check_types.do
    def _transitions_for_bundle(self, bundle_db_obj) -> list:
        """Every ``(transition db row, branch number)`` this bundle
        occupies -- a bundle can occupy more than one branch of the same
        transition, so a transition may appear more than once here."""
        bundle_id = bundle_db_obj.db_id
        results = []
        for transition in self.mainframe.project.transitions:
            t_db = transition.db_obj
            branches = [t_db.branch1, t_db.branch2, t_db.branch3,
                        t_db.branch4, t_db.branch5, t_db.branch6]

            for i, branch in enumerate(branches):
                if branch is None:
                    continue

                b = branch.bundle
                if b is not None and b.db_id == bundle_id:
                    results.append((t_db, i + 1))

        return results

    @_check_types.do
    def _transitions_for_wire(self, wire_db_obj) -> dict:
        """Map transition db-row-id -> ``[transition db row, [branch
        numbers]]``, merged across every bundle this wire belongs to --
        a wire whose bundle passes through the same transition on more
        than one branch shows every branch nested under that one
        transition entry (see :meth:`add_wire`)."""
        grouped = {}
        for bundle_db in self._bundles_containing_wire(wire_db_obj):
            for t_db, branch_num in self._transitions_for_bundle(bundle_db):
                entry = grouped.setdefault(t_db.db_id, [t_db, []])
                entry[1].append(branch_num)

        return grouped

    # ── Shared cross-reference builders ─────────────────────────────────
    # A cavity's seal/terminal children (and a terminal's own seal/wires
    # children) are shown in two places -- the canonical Cavities/
    # Terminals entry, and nested inside a housing's own Cavities group
    # (see add_housing) -- built here once so both stay in sync.

    @_check_types.do
    def _build_cavity_children(self, parent_item: QtWidgets.QTreeWidgetItem,
                               cavity_db_obj) -> None:
        """Append *cavity_db_obj*'s own seal, then its seated terminal
        (itself expanded via :meth:`_build_terminal_children`), under
        *parent_item*.

        :param parent_item: Item to append under.
        :type parent_item: :class:`QtWidgets.QTreeWidgetItem`
        """

        seal = cavity_db_obj.seal
        if seal is not None:
            ref2 = weakref.ref(seal, self.__remove_refs)
            self._weakrefs.append(ref2)
            child = self._append_item(parent_item, f'Seal: {seal.name}')
            self._set_data(child, ref2)

            self._set_treeitem(seal, child)

        terminal = cavity_db_obj.terminal
        if terminal is not None:
            ref2 = weakref.ref(terminal, self.__remove_refs)
            self._weakrefs.append(ref2)
            child = self._append_item(
                parent_item, f'Terminal: {terminal.name}', True)

            self._set_data(child, ref2)
            self._set_treeitem(terminal, child)

            self._build_terminal_children(child, terminal)

    @_check_types.do
    def _build_terminal_children(self, parent_item: QtWidgets.QTreeWidgetItem,
                                 terminal_db_obj) -> None:
        """Append *terminal_db_obj*'s own seal, then every wire attached
        to it, under *parent_item*.

        :param parent_item: Item to append under.
        :type parent_item: :class:`QtWidgets.QTreeWidgetItem`
        """

        seal = terminal_db_obj.seal
        if seal is not None:
            ref2 = weakref.ref(seal, self.__remove_refs)
            self._weakrefs.append(ref2)
            child = self._append_item(parent_item, f'Seal: {seal.name}')
            self._set_data(child, ref2)

            self._set_treeitem(seal, child)

        wires = self._wires_for_terminal(terminal_db_obj)
        if wires:
            wires_treeitem = self._append_item(parent_item, 'Wires', True)

            for wire in wires:
                ref2 = weakref.ref(wire, self.__remove_refs)
                self._weakrefs.append(ref2)
                child = self._append_item(wires_treeitem, f'Wire: {wire.name}')
                self._set_data(child, ref2)

                self._set_treeitem(wire, child)

    @_check_types.do
    def add_boot(self, obj: _boot.Boot):
        """
        Add a boot.

        :param obj: Object instance to operate on.
        :type obj: :class:`_boot.Boot`
        """

        ref = weakref.ref(obj, self.__remove_refs)
        self._weakrefs.append(ref)

        treeitem = self._append_item(self._boots, obj.db_obj.name, True)
        ti = TreeItem(self, treeitem, obj)

        self._set_data(treeitem, ref)

        housing = obj.db_obj.housing
        ref2 = weakref.ref(housing, self.__remove_refs)
        self._weakrefs.append(ref2)

        child = self._append_item(treeitem, f'Housing: {housing.name}')

        self._set_treeitem(housing, child)

        self._set_data(child, ref2)
        self._mark_canonical(treeitem)

        obj.set_treeitem(ti)

    @_check_types.do
    def add_bundle(self, obj: _bundle.Bundle):
        """
        Add a bundle.

        :param obj: Object instance to operate on.
        :type obj: :class:`_bundle.Bundle`
        """

        ref = weakref.ref(obj, self.__remove_refs)
        self._weakrefs.append(ref)

        treeitem = self._append_item(self._bundles, obj.db_obj.name, True)
        ti = TreeItem(self, treeitem, obj)

        self._set_data(treeitem, ref)

        transitions_treeitem = self._append_item(treeitem, 'Transitions', True)

        for t_db, branch_num in self._transitions_for_bundle(obj.db_obj):
            ref2 = weakref.ref(t_db, self.__remove_refs)
            self._weakrefs.append(ref2)
            child = self._append_item(
                transitions_treeitem, f'Transition: {t_db.name} : {branch_num}')

            self._set_data(child, ref2)
            self._set_treeitem(t_db, child)

        wires_treeitem = self._append_item(treeitem, 'Wires', True)

        for wire in obj.db_obj.wires:
            ref2 = weakref.ref(wire, self.__remove_refs)
            self._weakrefs.append(ref2)
            child = self._append_item(wires_treeitem, f'Wire: {wire.name}')
            self._set_data(child, ref2)

            self._set_treeitem(wire, child)

        self._mark_canonical(treeitem)
        obj.set_treeitem(ti)

    @_check_types.do
    def add_cavity(self, obj: _cavity.Cavity):
        """
        Add a cavity.

        :param obj: Object instance to operate on.
        :type obj: :class:`_cavity.Cavity`
        """

        ref = weakref.ref(obj, self.__remove_refs)
        self._weakrefs.append(ref)

        housing = obj.db_obj.housing

        if housing is not None:
            label = f'Cavity: {housing.name} : {obj.db_obj.name}'
        else:
            label = f'Cavity: {obj.db_obj.name}'

        treeitem = self._append_item(self._cavities, label, True)

        ti = TreeItem(self, treeitem, obj)

        self._set_data(treeitem, ref)

        self._build_cavity_children(treeitem, obj.db_obj)

        if housing is not None:
            ref2 = weakref.ref(housing, self.__remove_refs)
            self._weakrefs.append(ref2)
            child = self._append_item(treeitem, f'Housing: {housing.name}')

            self._set_treeitem(housing, child)
            self._set_data(child, ref2)

        self._mark_canonical(treeitem)

        obj.set_treeitem(ti)

    @_check_types.do
    def add_circuit(self, obj: _circuit.Circuit):
        """
        Add a circuit.

        :param obj: Object instance to operate on.
        :type obj: :class:`_circuit.Circuit`
        """

        ref = weakref.ref(obj, self.__remove_refs)
        self._weakrefs.append(ref)

        treeitem = self._append_item(
            self._circuits, obj.db_obj.name, True)

        ti = TreeItem(self, treeitem, obj)

        self._set_data(treeitem, ref)

        wire_treeitem = self._append_item(
            treeitem, 'Wires', True)

        for wire in obj.db_obj.wires:
            ref2 = weakref.ref(wire, self.__remove_refs)
            self._weakrefs.append(ref2)
            wireitem = self._append_item(
                wire_treeitem, f'Wire: {wire.name}')

            self._set_data(wireitem, ref2)

            self._set_treeitem(wire, wireitem)

        loop_treeitem = self._append_item(
            treeitem, 'Wire Service Loops', True)

        for wire in obj.db_obj.wire_service_loops:
            ref2 = weakref.ref(wire, self.__remove_refs)
            self._weakrefs.append(ref2)
            loopitem = self._append_item(
                loop_treeitem, f'Wire Loop: {wire.name}')

            self._set_data(loopitem, ref2)

            self._set_treeitem(wire, loopitem)

        terminal_treeitem = self._append_item(
            treeitem, 'Terminals', True)

        for terminal in obj.db_obj.terminals:
            ref2 = weakref.ref(terminal, self.__remove_refs)
            self._weakrefs.append(ref2)
            terminalitem = self._append_item(
                terminal_treeitem, f'Terminal: {terminal.name}')

            self._set_data(terminalitem, ref2)

            self._set_treeitem(terminal, terminalitem)

        splice_treeitem = self._append_item(
            treeitem, 'Splices', True)

        for splice in obj.db_obj.splices:
            ref2 = weakref.ref(splice, self.__remove_refs)
            self._weakrefs.append(ref2)
            spliceitem = self._append_item(
                splice_treeitem, f'Splice: {splice.name}')

            self._set_data(spliceitem, ref2)

            self._set_treeitem(splice, spliceitem)

        self._mark_canonical(treeitem)
        obj.set_treeitem(ti)

    @_check_types.do
    def add_cover(self, obj: _cover.Cover):
        """
        Add a cover.

        :param obj: Object instance to operate on.
        :type obj: :class:`_cover.Cover`
        """

        ref = weakref.ref(obj, self.__remove_refs)
        self._weakrefs.append(ref)

        treeitem = self._append_item(
            self._covers, obj.db_obj.name, True)

        ti = TreeItem(self, treeitem, obj)

        self._set_data(treeitem, ref)

        housing = obj.db_obj.housing
        if housing is not None:
            ref2 = weakref.ref(housing, self.__remove_refs)
            self._weakrefs.append(ref2)
            child = self._append_item(
                treeitem, f'Housing: {housing.name}')

            self._set_data(child, ref2)

            self._set_treeitem(housing, child)

        self._mark_canonical(treeitem)
        obj.set_treeitem(ti)

    @_check_types.do
    def add_cpa_lock(self, obj: _cpa_lock.CPALock):
        """
        Add a CPA lock.

        :param obj: Object instance to operate on.
        :type obj: :class:`_cpa_lock.CPALock`
        """

        ref = weakref.ref(obj, self.__remove_refs)
        self._weakrefs.append(ref)

        treeitem = self._append_item(
            self._cpa_locks, obj.db_obj.name, True)

        ti = TreeItem(self, treeitem, obj)

        self._set_data(treeitem, ref)

        housing = obj.db_obj.housing
        if housing is not None:
            ref2 = weakref.ref(housing, self.__remove_refs)
            self._weakrefs.append(ref2)
            child = self._append_item(
                treeitem, f'Housing: {housing.name}')

            self._set_data(child, ref2)

            self._set_treeitem(housing, child)

        self._mark_canonical(treeitem)
        obj.set_treeitem(ti)

    @_check_types.do
    def add_housing(self, obj: _housing.Housing):
        """
        Add a housing.

        :param obj: Object instance to operate on.
        :type obj: :class:`_housing.Housing`
        """

        ref = weakref.ref(obj, self.__remove_refs)
        self._weakrefs.append(ref)

        treeitem = self._append_item(
            self._housings, obj.db_obj.name, True)

        ti = TreeItem(self, treeitem, obj)

        self._set_data(treeitem, ref)

        boot = obj.db_obj.boot
        cover = obj.db_obj.cover
        cpa_lock = obj.db_obj.cpa_lock
        tpa_lock1 = obj.db_obj.tpa_lock1
        tpa_lock2 = obj.db_obj.tpa_lock2
        seal = obj.db_obj.seal
        cavities = obj.db_obj.cavities

        if boot is not None:
            ref2 = weakref.ref(boot, self.__remove_refs)
            self._weakrefs.append(ref2)
            child = self._append_item(treeitem, f'Boot: {boot.name}')
            self._set_data(child, ref2)

            self._set_treeitem(boot, child)

        if cover is not None:
            ref2 = weakref.ref(cover, self.__remove_refs)
            self._weakrefs.append(ref2)
            child = self._append_item(treeitem, f'Cover: {cover.name}')
            self._set_data(child, ref2)

            self._set_treeitem(cover, child)

        if cpa_lock is not None:
            ref2 = weakref.ref(cpa_lock, self.__remove_refs)
            self._weakrefs.append(ref2)
            child = self._append_item(
                treeitem, f'CPA Lock: {cpa_lock.name}')

            self._set_data(child, ref2)

            self._set_treeitem(cpa_lock, child)

        if tpa_lock1 is not None:
            ref2 = weakref.ref(tpa_lock1, self.__remove_refs)
            self._weakrefs.append(ref2)
            child = self._append_item(
                treeitem, f'TPA Lock 1: {tpa_lock1.name}')

            self._set_data(child, ref2)

            self._set_treeitem(tpa_lock1, child)

        if tpa_lock2 is not None:
            ref2 = weakref.ref(tpa_lock2, self.__remove_refs)
            self._weakrefs.append(ref2)
            child = self._append_item(
                treeitem, f'TPA Lock 2: {tpa_lock2.name}')

            self._set_data(child, ref2)

            self._set_treeitem(tpa_lock2, child)

        if seal is not None:
            ref2 = weakref.ref(seal, self.__remove_refs)
            self._weakrefs.append(ref2)
            child = self._append_item(treeitem, f'Seal: {seal.name}')
            self._set_data(child, ref2)

            self._set_treeitem(seal, child)

        cavities_treeitem = self._append_item(
            treeitem, 'Cavities', True)

        for cavity in cavities:
            ref2 = weakref.ref(cavity, self.__remove_refs)
            self._weakrefs.append(ref2)
            cavityitem = self._append_item(
                cavities_treeitem, f'Cavity: {cavity.name}', True)

            self._set_data(cavityitem, ref2)

            self._set_treeitem(cavity, cavityitem)

            self._build_cavity_children(cavityitem, cavity)

        self._mark_canonical(treeitem)
        obj.set_treeitem(ti)

    @_check_types.do
    def add_note(self, obj: _note.Note):
        """
        Add a note.

        :param obj: Object instance to operate on.
        :type obj: :class:`_note.Note`
        """

        ref = weakref.ref(obj, self.__remove_refs)
        self._weakrefs.append(ref)

        treeitem = self._append_item(self._notes, obj.db_obj.notes)
        ti = TreeItem(self, treeitem, obj)

        self._set_data(treeitem, ref)

        self._mark_canonical(treeitem)
        obj.set_treeitem(ti)

    @_check_types.do
    def add_seal(self, obj: _seal.Seal):
        """
        Add a seal.

        :param obj: Object instance to operate on.
        :type obj: :class:`_seal.Seal`
        """

        ref = weakref.ref(obj, self.__remove_refs)
        self._weakrefs.append(ref)

        treeitem = self._append_item(
            self._seals, obj.db_obj.name, True)

        ti = TreeItem(self, treeitem, obj)

        self._set_data(treeitem, ref)

        housing = obj.db_obj.housing
        cavity = obj.db_obj.cavity
        terminal = obj.db_obj.terminal

        if terminal is not None:
            ref2 = weakref.ref(terminal, self.__remove_refs)
            self._weakrefs.append(ref2)
            child = self._append_item(
                treeitem, f'Terminal: {terminal.name}')

            self._set_data(child, ref2)

            self._set_treeitem(terminal, child)

        elif cavity is not None:
            ref2 = weakref.ref(cavity, self.__remove_refs)
            self._weakrefs.append(ref2)
            child = self._append_item(treeitem, f'Cavity: {cavity.name}')
            self._set_data(child, ref2)

            self._set_treeitem(cavity, child)

        elif housing is not None:
            ref2 = weakref.ref(housing, self.__remove_refs)
            self._weakrefs.append(ref2)
            child = self._append_item(
                treeitem, f'Housing: {housing.name}')

            self._set_data(child, ref2)

            self._set_treeitem(housing, child)

        self._mark_canonical(treeitem)
        obj.set_treeitem(ti)

    @_check_types.do
    def add_splice(self, obj: _splice.Splice):
        """
        Add a splice.

        :param obj: Object instance to operate on.
        :type obj: :class:`_splice.Splice`
        """

        ref = weakref.ref(obj, self.__remove_refs)
        self._weakrefs.append(ref)

        treeitem = self._append_item(
            self._splices, obj.db_obj.name, True)

        ti = TreeItem(self, treeitem, obj)

        self._set_data(treeitem, ref)

        for wire in obj.db_obj.wires:
            ref2 = weakref.ref(wire, self.__remove_refs)
            self._weakrefs.append(ref2)
            child = self._append_item(treeitem, f'Wire: {wire.name}')
            self._set_data(child, ref2)

            self._set_treeitem(wire, child)

        self._mark_canonical(treeitem)
        obj.set_treeitem(ti)

    @_check_types.do
    def add_terminal(self, obj: _terminal.Terminal):
        """
        Add a terminal.

        :param obj: Object instance to operate on.
        :type obj: :class:`_terminal.Terminal`
        """

        ref = weakref.ref(obj, self.__remove_refs)
        self._weakrefs.append(ref)

        treeitem = self._append_item(
            self._terminals, obj.db_obj.name, True)

        ti = TreeItem(self, treeitem, obj)

        self._set_data(treeitem, ref)

        cavity = obj.db_obj.cavity
        circuit = obj.db_obj.circuit

        if cavity is not None:
            ref2 = weakref.ref(cavity, self.__remove_refs)
            self._weakrefs.append(ref2)
            child = self._append_item(treeitem, f'Cavity: {cavity.name}')
            self._set_data(child, ref2)

            self._set_treeitem(cavity, child)

        self._build_terminal_children(treeitem, obj.db_obj)

        if circuit is not None:
            ref2 = weakref.ref(circuit, self.__remove_refs)
            self._weakrefs.append(ref2)
            child = self._append_item(treeitem, f'Circuit: {circuit.name}')
            self._set_data(child, ref2)

            self._set_treeitem(circuit, child)

        self._mark_canonical(treeitem)
        obj.set_treeitem(ti)

    @_check_types.do
    def add_tpa_lock(self, obj: _tpa_lock.TPALock):
        """
        Add a TPA lock.

        :param obj: Object instance to operate on.
        :type obj: :class:`_tpa_lock.TPALock`
        """

        ref = weakref.ref(obj, self.__remove_refs)
        self._weakrefs.append(ref)

        treeitem = self._append_item(
            self._tpa_locks, obj.db_obj.name, True)

        ti = TreeItem(self, treeitem, obj)

        self._set_data(treeitem, ref)

        housing = obj.db_obj.housing
        ref2 = weakref.ref(housing, self.__remove_refs)
        self._weakrefs.append(ref2)
        child = self._append_item(treeitem, f'Housing: {housing.name}')
        self._set_data(child, ref2)

        self._set_treeitem(housing, child)

        self._mark_canonical(treeitem)
        obj.set_treeitem(ti)

    @_check_types.do
    def add_transition(self, obj: _transition.Transition):
        """
        Add a transition.

        :param obj: Object instance to operate on.
        :type obj: :class:`_transition.Transition`
        """

        ref = weakref.ref(obj, self.__remove_refs)
        self._weakrefs.append(ref)

        treeitem = self._append_item(
            self._transitions, obj.db_obj.name, True)

        ti = TreeItem(self, treeitem, obj)

        self._set_data(treeitem, ref)

        branches = [obj.db_obj.branch1, obj.db_obj.branch2, obj.db_obj.branch3,
                    obj.db_obj.branch4, obj.db_obj.branch5, obj.db_obj.branch6]

        for i, branch in enumerate(branches):
            if branch is None:
                continue

            branch_treeitem = self._append_item(
                treeitem, f'Branch {i + 1}', True)

            bundle = branch.bundle
            if bundle is not None:
                ref2 = weakref.ref(bundle, self.__remove_refs)
                self._weakrefs.append(ref2)
                child = self._append_item(
                    branch_treeitem, f'Bundle: {bundle.name}')

                self._set_data(child, ref2)

                self._set_treeitem(bundle, child)

            wires_treeitem = self._append_item(
                branch_treeitem, 'Wires', True)

            for wire in branch.wires:
                ref2 = weakref.ref(wire, self.__remove_refs)
                self._weakrefs.append(ref2)
                child = self._append_item(
                    wires_treeitem, f'Wire: {wire.name}')

                self._set_data(child, ref2)

                self._set_treeitem(wire, child)

        self._mark_canonical(treeitem)
        obj.set_treeitem(ti)

    @_check_types.do
    def add_wire(self, obj: _wire.Wire):
        """
        Add a wire.

        :param obj: Object instance to operate on.
        :type obj: :class:`_wire.Wire`
        """

        ref = weakref.ref(obj, self.__remove_refs)
        self._weakrefs.append(ref)

        treeitem = self._append_item(
            self._wires, obj.db_obj.name, True)

        ti = TreeItem(self, treeitem, obj)

        self._set_data(treeitem, ref)

        terminals = obj.db_obj.terminals
        circuit = obj.db_obj.circuit
        wire_markers = obj.db_obj.wire_markers

        if circuit is not None:
            ref2 = weakref.ref(circuit, self.__remove_refs)
            self._weakrefs.append(ref2)
            child = self._append_item(treeitem, f'Circuit: {circuit.name}')
            self._set_data(child, ref2)

            self._set_treeitem(circuit, child)

        terminals_treeitem = self._append_item(
            treeitem, 'Terminals', True)

        for terminal in terminals:
            ref2 = weakref.ref(terminal, self.__remove_refs)
            self._weakrefs.append(ref2)
            child = self._append_item(
                terminals_treeitem, f'Terminal: {terminal.name}')

            self._set_data(child, ref2)

            self._set_treeitem(terminal, child)

        splices_treeitem = self._append_item(
            treeitem, 'Splices', True)

        for splice in self._splices_containing_wire(obj.db_obj):
            ref2 = weakref.ref(splice, self.__remove_refs)
            self._weakrefs.append(ref2)
            child = self._append_item(
                splices_treeitem, f'Splice: {splice.name}')

            self._set_data(child, ref2)

            self._set_treeitem(splice, child)

        bundles_treeitem = self._append_item(
            treeitem, 'Bundles', True)

        for bundle in self._bundles_containing_wire(obj.db_obj):
            ref2 = weakref.ref(bundle, self.__remove_refs)
            self._weakrefs.append(ref2)
            child = self._append_item(
                bundles_treeitem, f'Bundle: {bundle.name}')

            self._set_data(child, ref2)

            self._set_treeitem(bundle, child)

        transitions_treeitem = self._append_item(
            treeitem, 'Transitions', True)

        for t_db, branch_nums in self._transitions_for_wire(obj.db_obj).values():
            ref2 = weakref.ref(t_db, self.__remove_refs)
            self._weakrefs.append(ref2)
            t_item = self._append_item(
                transitions_treeitem, f'Transition: {t_db.name}', True)

            self._set_data(t_item, ref2)
            self._set_treeitem(t_db, t_item)

            for branch_num in sorted(branch_nums):
                self._append_item(t_item, f'Branch: {branch_num}')

        markers_treeitem = self._append_item(
            treeitem, 'Wire Markers', True)

        for marker in wire_markers:
            ref2 = weakref.ref(marker, self.__remove_refs)
            self._weakrefs.append(ref2)
            child = self._append_item(
                markers_treeitem, f'Marker: {marker.name}')

            self._set_data(child, ref2)

            self._set_treeitem(marker, child)

        self._mark_canonical(treeitem)
        obj.set_treeitem(ti)

    @_check_types.do
    def add_wire_marker(self, obj: _wire_marker.WireMarker):
        """
        Add a wire marker.

        :param obj: Object instance to operate on.
        :type obj: :class:`_wire_marker.WireMarker`
        """

        ref = weakref.ref(obj, self.__remove_refs)
        self._weakrefs.append(ref)

        treeitem = self._append_item(
            self._wire_markers, obj.db_obj.name, True)

        ti = TreeItem(self, treeitem, obj)

        self._set_data(treeitem, ref)

        wire = obj.db_obj.wire
        ref2 = weakref.ref(wire, self.__remove_refs)
        self._weakrefs.append(ref2)
        child = self._append_item(treeitem, f'Wire: {wire.name}')
        self._set_data(child, ref2)

        self._set_treeitem(wire, child)

        self._mark_canonical(treeitem)
        obj.set_treeitem(ti)

    @_check_types.do
    def add_wire_service_loop(self, obj: _wire_service_loop.WireServiceLoop):
        """
        Add a wire service loop as a child of the wire it's attached to.

        A wire has at most one service loop, so it isn't a browsable
        category of its own the way boots/seals/etc. are -- it's shown
        nested under its wire's existing tree item instead. Requires the
        wire's own item to already exist (``add_wire`` runs first, both
        during project load and for an interactive add onto an
        already-placed wire); silently does nothing otherwise.

        :param obj: Object instance to operate on.
        :type obj: :class:`_wire_service_loop.WireServiceLoop`
        """

        wire = obj.db_obj.wire
        if wire is None:
            return

        wire_obj = wire.get_object()
        if wire_obj is None:
            return

        wire_treeitem = wire_obj.get_treeitem()
        if wire_treeitem is None:
            return

        ref = weakref.ref(obj, self.__remove_refs)
        self._weakrefs.append(ref)

        treeitem = self._append_item(wire_treeitem.treeitem,
                                     f'Wire Service Loop: {obj.db_obj.name}',
                                     True)

        self._set_data(treeitem, ref)

        ti = TreeItem(self, treeitem, obj)

        terminal = obj.db_obj.terminal
        circuit = obj.db_obj.circuit

        if terminal is not None:
            ref2 = weakref.ref(terminal, self.__remove_refs)
            self._weakrefs.append(ref2)
            child = self._append_item(
                treeitem, f'Terminal: {terminal.name}')

            self._set_data(child, ref2)

            self._set_treeitem(terminal, child)

        if circuit is not None:
            ref2 = weakref.ref(circuit, self.__remove_refs)
            self._weakrefs.append(ref2)
            child = self._append_item(treeitem, f'Circuit: {circuit.name}')
            self._set_data(child, ref2)

            self._set_treeitem(circuit, child)

        self._mark_canonical(treeitem)
        obj.set_treeitem(ti)

    @_check_types.do
    def set_selected(self, obj: "_object_base.ObjectBase"):
        """
        Reflect a selection made in one of the editors: expand the tree
        down to the object's item, highlight it, and scroll it into view.
        Called by ``mainframe._set_selected`` for every selection change,
        including this panel's own (see :meth:`select_object`, which
        calls this directly a second time after ``obj.set_selected(True)``
        to guarantee the tree ends up reflecting the object actually
        clicked, even if that object's own selection cascade redirects
        the *real* selection elsewhere downstream, e.g. a seated
        terminal's selection redirecting to its cavity/housing) -- being
        called more than once per click is fine; :meth:`_focus_item`
        moves the tree via ``_BrowserTree.set_current_item_silently``
        instead of a plain ``setCurrentItem``, so none of these calls
        re-arms the tree's own deferred cross-editor select timer (see
        that method's docstring for why a plain ``setCurrentItem`` would
        cause a reentrant, runaway busy-cursor flicker here).

        :param obj: Newly selected object, or ``None`` on deselect.
        :type obj: :class:`_object_base.ObjectBase` | None
        """

        if obj is None:
            self._treectrl.clearSelection()
            self._treectrl.setCurrentItem(None)
            return

        treeitem = obj.get_treeitem()
        if treeitem is None:
            # object types the browser has no category for (project,
            # generic, project_model, wire_layout, bundle_layout) and
            # gizmo objects (RotationRings, MoveArrows) never get one
            return

        self._focus_item(treeitem.treeitem)

    @_check_types.do
    def _expand_ancestors(self, item: QtWidgets.QTreeWidgetItem) -> None:
        """
        Expand every ancestor of ``item`` so it is actually visible.

        :param item: Item to reveal.
        :type item: :class:`QtWidgets.QTreeWidgetItem`
        """

        parent = item.parent()
        while parent is not None:
            parent.setExpanded(True)
            parent = parent.parent()

    @_check_types.do
    def _focus_item(self, item: QtWidgets.QTreeWidgetItem) -> None:
        """
        Expand down to ``item``, make it current, and scroll it into view.
        Shared by :meth:`set_selected` (a selection made in an editor) and
        :meth:`_goto_match` (a search hit).

        :param item: Item to focus.
        :type item: :class:`QtWidgets.QTreeWidgetItem`
        """

        self._expand_ancestors(item)
        self._treectrl.set_current_item_silently(item)
        self._treectrl.scrollToItem(item)

    @_check_types.do
    def _resolve_object(self, obj):
        """
        Resolve a value pulled from a tree item's stored weakref to the
        :class:`_object_base.ObjectBase` wrapper the rest of this method
        operates on.

        Canonical entries (see :meth:`_mark_canonical`) store the wrapper
        directly, but cross-reference children -- e.g. the "Housing: X"
        entry nested under a cavity's canonical entry, or "Cavity: X" under
        a housing (see :meth:`add_housing`, :meth:`add_cavity`, etc.) --
        store the referenced object's raw DB row instead, so search can
        match it by name. DB rows expose ``get_object()`` to get back to
        their wrapper; :class:`_object_base.ObjectBase` does not, so that
        is what tells the two apart here.

        :param obj: Value resolved from a tree item's stored weakref.
        :rtype: _object_base.ObjectBase | None
        """

        get_object = getattr(obj, 'get_object', None)
        if get_object is None:
            return obj

        return get_object()

    @_check_types.do
    def select_object(self, obj: "_object_base.ObjectBase") -> None:
        """
        Make ``obj`` the active selection in every editor. Called by
        :class:`_BrowserTree` once a single click's double-click window has
        passed with no second click.

        :param obj: Object whose tree item was clicked.
        :type obj: :class:`_object_base.ObjectBase`
        """

        obj = self._resolve_object(obj)
        if obj is None:
            return

        curr_selected = self.mainframe.get_selected()

        if obj is curr_selected:
            return

        self.mainframe._selection_source_editor = 'object_browser'  # NOQA

        if curr_selected is not None:
            curr_selected.set_selected(False)

        obj.set_selected(True)

        # obj.set_selected(True)'s own cascade can end up reflecting a
        # DIFFERENT object as the real selection than obj itself (e.g. a
        # seated terminal's selection redirecting to its cavity/housing
        # somewhere downstream) -- this call makes sure the tree still
        # ends up showing the object actually clicked here, regardless
        # of what the rest of the cascade decided. Calling set_selected
        # twice for one click is fine; what actually caused the earlier
        # busy-cursor flicker was setCurrentItem re-arming the tree's own
        # deferred select timer each time -- fixed at the source in
        # _focus_item/_BrowserTree.set_current_item_silently instead of
        # here, so this stays.
        self.set_selected(obj)

    @_check_types.do
    def open_properties(self, obj: "_object_base.ObjectBase") -> None:
        """
        Open the modeless properties dialog for ``obj`` without touching
        the current selection, so the object editor dock can keep showing
        a different object. Called by :class:`_BrowserTree` on double
        click.

        :param obj: Object whose tree item was double-clicked.
        :type obj: :class:`_object_base.ObjectBase`
        """

        obj = self._resolve_object(obj)
        if obj is None:
            return

        from ...objects.objects_3d import menu_ops as _menu_ops

        _menu_ops.show_properties_for_object(self.mainframe, obj)

    @_check_types.do
    def _category_roots(self) -> dict[str, QtWidgets.QTreeWidgetItem]:
        """
        Return the current category label -> live root item mapping.

        Resolved fresh on every call (rather than cached) since
        :meth:`reset` replaces every category item wholesale.

        :rtype: dict[str, :class:`QtWidgets.QTreeWidgetItem`]
        """

        return {label: getattr(self, attr) for label, attr in self._CATEGORY_ATTRS}

    @_check_types.do
    def _ancestor_category(self, item: QtWidgets.QTreeWidgetItem):
        """
        Return the category root ``item`` lives under, or ``None``.

        Walks up to the nearest ancestor that is one of the category roots
        -- a wire service loop's canonical item, for example, is a child of
        its wire's item, itself a child of the "Wires" root, two levels up.

        :param item: Item to categorize.
        :type item: :class:`QtWidgets.QTreeWidgetItem`
        :rtype: :class:`QtWidgets.QTreeWidgetItem` | None
        """

        roots = self._category_roots().values()

        parent = item.parent()
        while parent is not None:
            for root in roots:
                if root is parent:
                    return parent

            parent = parent.parent()

        return None

    @_check_types.do
    def _find_matches(self, keyword: str,
                      category_label: str) -> list[QtWidgets.QTreeWidgetItem]:
        """
        Return the search hits for ``keyword``, trying path-style traversal
        first and falling back to a plain name search.

        ``keyword`` may use ``:`` or ``.`` as a level marker to walk down
        the tree as displayed -- e.g. ``"Housing 1:Cavity 1"`` finds items
        under "Housing 1" (any depth, including cross-reference mentions
        like "Cavity: Cavity 1") that in turn contain "Cavity 1". A marker
        only counts as such with no adjacent whitespace, so
        ``"Housing 1 : Cavity 1"`` (spaces around it) is left as one plain
        string. If no marker is present, or the path search finds nothing
        (the marker character turns out to just be part of a real name,
        e.g. "Housing 1.5"), falls back to a plain substring match of the
        whole original ``keyword`` against every *canonical* item's own
        label -- cross-reference mentions never match in that fallback.

        :param keyword: Lowercased search text.
        :type keyword: str
        :param category_label: Combo box selection; ``'All Categories'``
            (or anything not in :attr:`_CATEGORY_ATTRS`) searches everything.
        :type category_label: str
        :rtype: list[:class:`QtWidgets.QTreeWidgetItem`]
        """

        segments = self._split_path_query(keyword)

        if len(segments) > 1:
            path_matches = self._find_path_matches(segments, category_label)
            if path_matches:
                return path_matches

        return self._find_name_matches(keyword, category_label)

    @_check_types.do
    def _split_path_query(self, keyword: str) -> list[str]:
        """
        Split ``keyword`` on a ``:`` or ``.`` level marker.

        Either character works and both can be mixed in one query; a
        character only counts as a marker when it has no adjacent
        whitespace, which is what tells a marker apart from a literal
        character in a name. Returns ``[keyword]`` unchanged when no marker
        is present, so callers can treat both cases the same way.

        :param keyword: Search text (already lowercased).
        :type keyword: str
        :rtype: list[str]
        """

        segments = [s for s in _PATH_SEPARATOR_RE.split(keyword) if s]
        return segments if len(segments) > 1 else [keyword]

    @_check_types.do
    def _find_path_matches(self, segments: list[str],
                           category_label: str) -> list[QtWidgets.QTreeWidgetItem]:
        """
        Resolve a marker-separated path, one segment per tree level.

        Every item (canonical entries and cross-reference mentions alike)
        is fair game here -- unlike the plain name fallback, the point is
        to follow the tree exactly as displayed, and a housing's cavities,
        for instance, only appear nested under it as cross-references (the
        canonical cavity entries live entirely separately, under the
        top-level "Cavities" category).

        :param segments: Path segments in top-to-bottom order.
        :type segments: list[str]
        :param category_label: Restricts the first segment's search the
            same way :meth:`_find_name_matches` does; later segments only
            ever search inside items already found, so they need no
            separate restriction.
        :type category_label: str
        :rtype: list[:class:`QtWidgets.QTreeWidgetItem`]
        """

        category_root = self._category_roots().get(category_label)
        if category_root is not None:
            start = category_root
        else:
            start = self._tree_root

        if start is None:
            return []

        candidates = self._items_containing(start, segments[0])

        for segment in segments[1:]:
            next_candidates = []
            for candidate in candidates:
                next_candidates.extend(self._items_containing(candidate, segment))

            candidates = next_candidates
            if not candidates:
                break

        return candidates

    @_check_types.do
    def _items_containing(self, root_item: QtWidgets.QTreeWidgetItem,
                          needle: str) -> list[QtWidgets.QTreeWidgetItem]:
        """
        Return every descendant of ``root_item`` (any depth, not including
        ``root_item`` itself) whose label contains ``needle``.

        :param root_item: Item to search under.
        :type root_item: :class:`QtWidgets.QTreeWidgetItem`
        :param needle: Lowercased substring to look for.
        :type needle: str
        :rtype: list[:class:`QtWidgets.QTreeWidgetItem`]
        """

        found = []

        @_check_types.do
        def _walk(parent):
            for i in range(parent.childCount()):
                child = parent.child(i)
                if needle in child.text(0).lower():
                    found.append(child)

                _walk(child)

        _walk(root_item)

        return found

    @_check_types.do
    def _find_name_matches(self, keyword: str,
                           category_label: str) -> list[QtWidgets.QTreeWidgetItem]:
        """
        Return every canonical item whose own label contains ``keyword``
        (case-insensitive), optionally restricted to one category's subtree.

        Cross-reference mentions (e.g. "Housing: X" under a Boot) are never
        matched -- only entries :meth:`_mark_canonical` flagged.

        :param keyword: Lowercased search text.
        :type keyword: str
        :param category_label: Combo box selection; ``'All Categories'``
            (or anything not in :attr:`_CATEGORY_ATTRS`) searches everything.
        :type category_label: str
        :rtype: list[:class:`QtWidgets.QTreeWidgetItem`]
        """

        category_root = self._category_roots().get(category_label)
        matches = []

        @_check_types.do
        def _walk(parent):
            for i in range(parent.childCount()):
                child = parent.child(i)

                if (
                    child.data(0, self._CANONICAL_ROLE) and
                    keyword in child.text(0).lower() and
                    (category_root is None or self._ancestor_category(child) is category_root)
                ):
                    matches.append(child)

                _walk(child)

        _walk(self._tree_root)

        return matches

    @_check_types.do
    def _reset_search(self, *_) -> None:
        """
        Clear search-cycling state after the keyword or category
        changes, so the next Search click starts from the first match.
        """

        self._search_index = -1
        self._search_status.setText('')

    @_check_types.do
    def _on_search_clicked(self) -> None:
        """
        Run (or continue) a search: jump to the next match for the current
        keyword/category, wrapping back to the first match after the last.
        """

        keyword = self._search_edit.text().strip().lower()
        if not keyword:
            self._reset_search()
            return

        matches = self._find_matches(keyword, self._search_category.currentText())

        if not matches:
            self._search_index = -1
            self._search_status.setText('No matches')
            return

        self._search_index = (self._search_index + 1) % len(matches)
        self._goto_match(matches[self._search_index])
        self._search_status.setText(f'{self._search_index + 1} of {len(matches)}')

    @_check_types.do
    def _goto_match(self, item: QtWidgets.QTreeWidgetItem) -> None:
        """
        Focus a search hit in the tree and select its object in every
        editor -- equivalent to clicking the row, but immediate since a
        deliberate Search click carries no double-click ambiguity to guard
        against.

        :param item: Matched item.
        :type item: :class:`QtWidgets.QTreeWidgetItem`
        """

        self._focus_item(item)

        ref = item.data(0, QtCore.Qt.ItemDataRole.UserRole)

        if ref is not None:
            obj = ref()

            if obj is not None:
                self.select_object(obj)

    @_check_types.do
    def add_object(self, obj):
        """
        Add an object.

        :param obj: Object instance to operate on.
        :type obj: UNKNOWN
        """

        self._objects.append(obj)

    @_check_types.do
    def remove_object(self, obj):
        """
        Remove the object.

        :param obj: Object instance to operate on.
        :type obj: UNKNOWN
        """

        try:
            self._objects.remove(obj)
        except ValueError:
            pass
