# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

from typing import TYPE_CHECKING

from PySide6.QtWidgets import (
    QWidget, QTreeWidget, QTreeWidgetItem, QAbstractItemView,
    QVBoxLayout, QHBoxLayout
)
from PySide6.QtCore import Qt
from PySide6 import QtWidgets

import weakref

from ...objects import (
    boot as _boot,
    bundle as _bundle,
    cavity as _cavity,
    circuit as _circuit,
    cover as _cover,
    cpa_lock as _cpa_lock,
    housing as _housing,
    note as _note,
    seal as _seal,
    splice as _splice,
    terminal as _terminal,
    tpa_lock as _tpa_lock,
    transition as _transition,
    wire as _wire,
    wire_marker as _wire_marker,
    wire_service_loop as _wire_service_loop
)


if TYPE_CHECKING:
    from .. import mainframe as _mainframe


class ObjectBrowser:
    """Represent an object browser in :mod:`harness_designer.ui.object_browser.objectbrowser`.

    UNKNOWN details are inferred from the class name and surrounding code.
    """

    def __init__(self, mainframe: "_mainframe.MainFrame"):
        """Initialise the :class:`ObjectBrowser` instance.

        UNKNOWN details are inferred from the callable name and signature.

        :param mainframe: Main application frame.
        :type mainframe: :class:`_mainframe.MainFrame`
        """
        self.editor = ObjectBrowserPanel(mainframe)
        self.mainframe = mainframe

        # Register the panel with the dock system (handled in mainframe)
        self._dock = mainframe._make_dock(
            title='Object Browser',
            name='object_browser',
            widget=self.editor,
            area=Qt.DockWidgetArea.LeftDockWidgetArea,
        )
        self._dock.show()

    def add_boot(self, obj: _boot.Boot):
        """Add a boot.

        UNKNOWN details are inferred from the callable name and signature.

        :param obj: Object instance to operate on.
        :type obj: :class:`_boot.Boot`
        """
        self.editor.add_boot(obj)

    def add_bundle(self, obj: _bundle.Bundle):
        """Add a bundle.

        UNKNOWN details are inferred from the callable name and signature.

        :param obj: Object instance to operate on.
        :type obj: :class:`_bundle.Bundle`
        """
        self.editor.add_bundle(obj)

    def add_cavity(self, obj: _cavity.Cavity):
        """Add a cavity.

        UNKNOWN details are inferred from the callable name and signature.

        :param obj: Object instance to operate on.
        :type obj: :class:`_cavity.Cavity`
        """
        self.editor.add_cavity(obj)

    def add_circuit(self, obj: _circuit.Circuit):
        """Add a circuit.

        UNKNOWN details are inferred from the callable name and signature.

        :param obj: Object instance to operate on.
        :type obj: :class:`_circuit.Circuit`
        """
        self.editor.add_circuit(obj)

    def add_cover(self, obj: _cover.Cover):
        """Add a cover.

        UNKNOWN details are inferred from the callable name and signature.

        :param obj: Object instance to operate on.
        :type obj: :class:`_cover.Cover`
        """
        self.editor.add_cover(obj)

    def add_cpa_lock(self, obj: _cpa_lock.CPALock):
        """Add a CPA lock.

        UNKNOWN details are inferred from the callable name and signature.

        :param obj: Object instance to operate on.
        :type obj: :class:`_cpa_lock.CPALock`
        """
        self.editor.add_cpa_lock(obj)

    def add_housing(self, obj: _housing.Housing):
        """Add a housing.

        UNKNOWN details are inferred from the callable name and signature.

        :param obj: Object instance to operate on.
        :type obj: :class:`_housing.Housing`
        """
        self.editor.add_housing(obj)

    def add_note(self, obj: _note.Note):
        """Add a note.

        UNKNOWN details are inferred from the callable name and signature.

        :param obj: Object instance to operate on.
        :type obj: :class:`_note.Note`
        """
        self.editor.add_note(obj)

    def add_seal(self, obj: _seal.Seal):
        """Add a seal.

        UNKNOWN details are inferred from the callable name and signature.

        :param obj: Object instance to operate on.
        :type obj: :class:`_seal.Seal`
        """
        self.editor.add_seal(obj)

    def add_splice(self, obj: _splice.Splice):
        """Add a splice.

        UNKNOWN details are inferred from the callable name and signature.

        :param obj: Object instance to operate on.
        :type obj: :class:`_splice.Splice`
        """
        self.editor.add_splice(obj)

    def add_terminal(self, obj: _terminal.Terminal):
        """Add a terminal.

        UNKNOWN details are inferred from the callable name and signature.

        :param obj: Object instance to operate on.
        :type obj: :class:`_terminal.Terminal`
        """
        self.editor.add_terminal(obj)

    def add_tpa_lock(self, obj: _tpa_lock.TPALock):
        """Add a TPA lock.

        UNKNOWN details are inferred from the callable name and signature.

        :param obj: Object instance to operate on.
        :type obj: :class:`_tpa_lock.TPALock`
        """
        self.editor.add_tpa_lock(obj)

    def add_transition(self, obj: _transition.Transition):
        """Add a transition.

        UNKNOWN details are inferred from the callable name and signature.

        :param obj: Object instance to operate on.
        :type obj: :class:`_transition.Transition`
        """
        self.editor.add_transition(obj)

    def add_wire(self, obj: _wire.Wire):
        """Add a wire.

        UNKNOWN details are inferred from the callable name and signature.

        :param obj: Object instance to operate on.
        :type obj: :class:`_wire.Wire`
        """
        self.editor.add_wire(obj)

    def add_wire_marker(self, obj: _wire_marker.WireMarker):
        """Add a wire marker.

        UNKNOWN details are inferred from the callable name and signature.

        :param obj: Object instance to operate on.
        :type obj: :class:`_wire_marker.WireMarker`
        """
        self.editor.add_wire_marker(obj)

    def add_wire_service_loop(self, obj: _wire_service_loop.WireServiceLoop):
        """Add a wire service loop.

        UNKNOWN details are inferred from the callable name and signature.

        :param obj: Object instance to operate on.
        :type obj: :class:`_wire_service_loop.WireServiceLoop`
        """
        self.editor.add_wire_service_loop(obj)

    def reset(self):
        """Execute the reset operation.

        UNKNOWN details are inferred from the callable name and signature.
        """
        self.editor.reset()

    def set_selected(self, obj):
        """Set the selected.

        UNKNOWN details are inferred from the callable name and signature.

        :param obj: Object instance to operate on.
        :type obj: UNKNOWN
        """
        self.editor.set_selected(obj)

    def add_object(self, obj):
        """Add an object.

        UNKNOWN details are inferred from the callable name and signature.

        :param obj: Object instance to operate on.
        :type obj: UNKNOWN
        """
        self.editor.add_object(obj)

    def remove_object(self, obj):
        """Remove the object.

        UNKNOWN details are inferred from the callable name and signature.

        :param obj: Object instance to operate on.
        :type obj: UNKNOWN
        """
        self.editor.remove_object(obj)

    def Refresh(self, *args, **kwargs):
        """Execute the refresh operation.

        UNKNOWN details are inferred from the callable name and signature.

        :param args: Additional positional arguments.
        :type args: UNKNOWN
        :param kwargs: Additional keyword arguments.
        :type kwargs: UNKNOWN
        """
        self.editor.update()

    def Destroy(self):
        """Execute the destroy operation.

        UNKNOWN details are inferred from the callable name and signature.
        """
        self.editor.deleteLater()


class ObjectBrowserPanel(QWidget):
    """Represent an object browser panel in :mod:`harness_designer.ui.object_browser.objectbrowser`.

    UNKNOWN details are inferred from the class name and surrounding code.
    """

    def __init__(self, parent: "_mainframe.MainFrame"):
        """Initialise the :class:`ObjectBrowserPanel` instance.

        UNKNOWN details are inferred from the callable name and signature.

        :param parent: Parent object.
        :type parent: :class:`_mainframe.MainFrame`
        """
        QWidget.__init__(self, parent)
        self.mainframe = parent

        self._objects = []
        self._selected = None
        self._treectrl = QTreeWidget(self)
        self._treectrl.setHeaderHidden(True)
        self._treectrl.setRootIsDecorated(True)
        self._treectrl.setSelectionMode(
            QAbstractItemView.SelectionMode.SingleSelection)

        h_layout = QHBoxLayout()
        v_layout = QVBoxLayout(self)

        h_layout.addWidget(self._treectrl)
        v_layout.addLayout(h_layout)

        self._root: QTreeWidgetItem = None
        self._boots: QTreeWidgetItem = None
        self._bundles: QTreeWidgetItem = None
        self._cavities: QTreeWidgetItem = None
        self._circuits: QTreeWidgetItem = None
        self._covers: QTreeWidgetItem = None
        self._cpa_locks: QTreeWidgetItem = None
        self._housings: QTreeWidgetItem = None
        self._notes: QTreeWidgetItem = None
        self._seals: QTreeWidgetItem = None
        self._splices: QTreeWidgetItem = None
        self._terminals: QTreeWidgetItem = None
        self._tpa_locks: QTreeWidgetItem = None
        self._transitions: QTreeWidgetItem = None
        self._wires: QTreeWidgetItem = None
        self._wire_markers: QTreeWidgetItem = None
        self._weakrefs = []

    def _append_item(self, parent: QTreeWidgetItem, label: str,  # NOQA
                     has_children: bool = False) -> QTreeWidgetItem:
        """Execute the append item operation.

        UNKNOWN details are inferred from the callable name and signature.

        :param parent: Parent object.
        :type parent: :class:`QTreeWidgetItem`
        :param label: Value for ``label``.
        :type label: str
        :param has_children: Boolean flag for whether children is available.
        :type has_children: bool
        :returns: Return value. UNKNOWN details.
        :rtype: :class:`QTreeWidgetItem`
        """
        item = QTreeWidgetItem(parent, [label])
        if has_children:
            item.setChildIndicatorPolicy(
                QTreeWidgetItem.ChildIndicatorPolicy.ShowIndicator)
        return item

    def reset(self):
        """Execute the reset operation.

        UNKNOWN details are inferred from the callable name and signature.
        """
        self._treectrl.clear()
        self._root = QTreeWidgetItem(self._treectrl, ['root'])
        self._treectrl.addTopLevelItem(self._root)

        self._boots = self._append_item(self._root, 'Boots', True)
        self._bundles = self._append_item(self._root, 'Bundles', True)
        self._cavities = self._append_item(self._root, 'Cavities', True)
        self._circuits = self._append_item(self._root, 'Circuits', True)
        self._covers = self._append_item(self._root, 'Covers', True)
        self._cpa_locks = self._append_item(self._root, 'CPA Locks', True)
        self._housings = self._append_item(self._root, 'Housings', True)
        self._notes = self._append_item(self._root, 'Notes', True)
        self._seals = self._append_item(self._root, 'Seals', True)
        self._splices = self._append_item(self._root, 'Splices', True)
        self._terminals = self._append_item(self._root, 'Terminals', True)
        self._tpa_locks = self._append_item(self._root, 'TPA Locks', True)
        self._transitions = self._append_item(self._root, 'Transitions', True)
        self._wires = self._append_item(self._root, 'Wires', True)
        self._wire_markers = self._append_item(self._root, 'Wire Markers', True)

        self._weakrefs = []

    def __remove_refs(self, ref):
        """Remove the refs.

        UNKNOWN details are inferred from the callable name and signature.

        :param ref: Value for ``ref``.
        :type ref: UNKNOWN
        """
        def iter_tree(parent: QTreeWidgetItem):
            """Iterate over the tree.

            UNKNOWN details are inferred from the callable name and signature.

            :param parent: Parent object.
            :type parent: :class:`QTreeWidgetItem`
            :returns: Iterator or iterable result. UNKNOWN details.
            :rtype: UNKNOWN
            """
            for i in range(parent.childCount() - 1, -1, -1):
                child = parent.child(i)
                d_ref = child.data(0, Qt.ItemDataRole.UserRole)
                if d_ref is not None:
                    data = d_ref()
                    if data is None:
                        parent.removeChild(child)
                        continue
                if child.childCount() > 0:
                    iter_tree(child)

        if self._root is not None:
            iter_tree(self._root)

        try:
            self._weakrefs.remove(ref)
        except ValueError:
            pass

    def _set_data(self, item: QTreeWidgetItem, ref):  # NOQA
        """Set the data.

        UNKNOWN details are inferred from the callable name and signature.

        :param item: Item identifier or value.
        :type item: :class:`QTreeWidgetItem`
        :param ref: Value for ``ref``.
        :type ref: UNKNOWN
        """
        item.setData(0, Qt.ItemDataRole.UserRole, ref)

    def add_boot(self, obj: _boot.Boot):
        """Add a boot.

        UNKNOWN details are inferred from the callable name and signature.

        :param obj: Object instance to operate on.
        :type obj: :class:`_boot.Boot`
        """
        ref = weakref.ref(obj, self.__remove_refs)
        self._weakrefs.append(ref)

        treeitem = self._append_item(self._boots, obj.db_obj.name, True)
        self._set_data(treeitem, ref)

        housing = obj.db_obj.housing
        ref2 = weakref.ref(housing, self.__remove_refs)
        self._weakrefs.append(ref2)
        child = self._append_item(treeitem, f'Housing: {housing.name}')
        self._set_data(child, ref2)

        obj.set_treeitem(treeitem)

    def add_bundle(self, obj: _bundle.Bundle):
        """Add a bundle.

        UNKNOWN details are inferred from the callable name and signature.

        :param obj: Object instance to operate on.
        :type obj: :class:`_bundle.Bundle`
        """
        ref = weakref.ref(obj, self.__remove_refs)
        self._weakrefs.append(ref)

        treeitem = self._append_item(self._bundles, obj.db_obj.name, True)
        self._set_data(treeitem, ref)

        for wire in obj.db_obj.wires:
            ref2 = weakref.ref(wire, self.__remove_refs)
            self._weakrefs.append(ref2)
            child = self._append_item(treeitem, f'Wire: {wire.name}')
            self._set_data(child, ref2)

        obj.set_treeitem(treeitem)

    def add_cavity(self, obj: _cavity.Cavity):
        """Add a cavity.

        UNKNOWN details are inferred from the callable name and signature.

        :param obj: Object instance to operate on.
        :type obj: :class:`_cavity.Cavity`
        """
        ref = weakref.ref(obj, self.__remove_refs)
        self._weakrefs.append(ref)

        treeitem = self._append_item(self._cavities, obj.db_obj.name, True)
        self._set_data(treeitem, ref)

        housing = obj.db_obj.housing
        ref2 = weakref.ref(housing, self.__remove_refs)
        self._weakrefs.append(ref2)
        child = self._append_item(treeitem, f'Housing: {housing.name}')
        self._set_data(child, ref2)

        terminal = obj.db_obj.terminal
        if terminal is not None:
            ref2 = weakref.ref(terminal, self.__remove_refs)
            self._weakrefs.append(ref2)
            child = self._append_item(treeitem, f'Terminal: {terminal.name}')
            self._set_data(child, ref2)

        seal = obj.db_obj.seal
        if seal is not None:
            ref2 = weakref.ref(seal, self.__remove_refs)
            self._weakrefs.append(ref2)
            child = self._append_item(treeitem, f'Seal: {seal.name}')
            self._set_data(child, ref2)

        obj.set_treeitem(treeitem)

    def add_circuit(self, obj: _circuit.Circuit):
        """Add a circuit.

        UNKNOWN details are inferred from the callable name and signature.

        :param obj: Object instance to operate on.
        :type obj: :class:`_circuit.Circuit`
        """
        ref = weakref.ref(obj, self.__remove_refs)
        self._weakrefs.append(ref)

        treeitem = self._append_item(self._circuits, obj.db_obj.name, True)
        self._set_data(treeitem, ref)

        wire_treeitem = self._append_item(treeitem, 'Wires', True)
        for wire in obj.db_obj.wires:
            ref2 = weakref.ref(wire, self.__remove_refs)
            self._weakrefs.append(ref2)
            wireitem = self._append_item(wire_treeitem, f'Wire: {wire.name}')
            self._set_data(wireitem, ref2)

        loop_treeitem = self._append_item(treeitem, 'Wire Service Loops', True)
        for wire in obj.db_obj.wire_service_loops:
            ref2 = weakref.ref(wire, self.__remove_refs)
            self._weakrefs.append(ref2)
            loopitem = self._append_item(loop_treeitem, f'Wire Loop: {wire.name}')
            self._set_data(loopitem, ref2)

        terminal_treeitem = self._append_item(treeitem, 'Terminals', True)
        for terminal in obj.db_obj.terminals:
            ref2 = weakref.ref(terminal, self.__remove_refs)
            self._weakrefs.append(ref2)
            terminalitem = self._append_item(terminal_treeitem, f'Terminal: {terminal.name}')
            self._set_data(terminalitem, ref2)

        splice_treeitem = self._append_item(treeitem, 'Splices', True)
        for splice in obj.db_obj.splices:
            ref2 = weakref.ref(splice, self.__remove_refs)
            self._weakrefs.append(ref2)
            spliceitem = self._append_item(splice_treeitem, f'Splice: {splice.name}')
            self._set_data(spliceitem, ref2)

        obj.set_treeitem(treeitem)

    def add_cover(self, obj: _cover.Cover):
        """Add a cover.

        UNKNOWN details are inferred from the callable name and signature.

        :param obj: Object instance to operate on.
        :type obj: :class:`_cover.Cover`
        """
        ref = weakref.ref(obj, self.__remove_refs)
        self._weakrefs.append(ref)

        treeitem = self._append_item(self._covers, obj.db_obj.name, True)
        self._set_data(treeitem, ref)

        housing = obj.db_obj.housing
        if housing is not None:
            ref2 = weakref.ref(housing, self.__remove_refs)
            self._weakrefs.append(ref2)
            child = self._append_item(treeitem, f'Housing: {housing.name}')
            self._set_data(child, ref2)

        obj.set_treeitem(treeitem)

    def add_cpa_lock(self, obj: _cpa_lock.CPALock):
        """Add a CPA lock.

        UNKNOWN details are inferred from the callable name and signature.

        :param obj: Object instance to operate on.
        :type obj: :class:`_cpa_lock.CPALock`
        """
        ref = weakref.ref(obj, self.__remove_refs)
        self._weakrefs.append(ref)

        treeitem = self._append_item(self._cpa_locks, obj.db_obj.name, True)
        self._set_data(treeitem, ref)

        housing = obj.db_obj.housing
        ref2 = weakref.ref(housing, self.__remove_refs)
        self._weakrefs.append(ref2)
        child = self._append_item(treeitem, f'Housing: {housing.name}')
        self._set_data(child, ref2)

        obj.set_treeitem(treeitem)

    def add_housing(self, obj: _housing.Housing):
        """Add a housing.

        UNKNOWN details are inferred from the callable name and signature.

        :param obj: Object instance to operate on.
        :type obj: :class:`_housing.Housing`
        """
        ref = weakref.ref(obj, self.__remove_refs)
        self._weakrefs.append(ref)

        treeitem = self._append_item(self._housings, obj.db_obj.name, True)
        self._set_data(treeitem, ref)

        seal = obj.db_obj.seal
        cover = obj.db_obj.cover
        cpa_lock = obj.db_obj.cpa_lock
        tpa_locks = obj.db_obj.tpa_locks
        cavities = obj.db_obj.cavities

        if seal is not None:
            ref2 = weakref.ref(seal, self.__remove_refs)
            self._weakrefs.append(ref2)
            child = self._append_item(treeitem, f'Seal: {seal.name}')
            self._set_data(child, ref2)

        if cover is not None:
            ref2 = weakref.ref(cover, self.__remove_refs)
            self._weakrefs.append(ref2)
            child = self._append_item(treeitem, f'Cover: {cover.name}')
            self._set_data(child, ref2)

        if cpa_lock is not None:
            ref2 = weakref.ref(cpa_lock, self.__remove_refs)
            self._weakrefs.append(ref2)
            child = self._append_item(treeitem, f'CPA Lock: {cpa_lock.name}')
            self._set_data(child, ref2)

        tpa_locks_treeitem = self._append_item(treeitem, 'TPA Locks', True)
        for lock in tpa_locks:
            ref2 = weakref.ref(lock, self.__remove_refs)
            self._weakrefs.append(ref2)
            lockitem = self._append_item(tpa_locks_treeitem, f'TPA Lock: {lock.name}')
            self._set_data(lockitem, ref2)

        cavities_treeitem = self._append_item(treeitem, 'Cavities', True)
        for cavity in cavities:
            ref2 = weakref.ref(cavity, self.__remove_refs)
            self._weakrefs.append(ref2)
            cavityitem = self._append_item(cavities_treeitem, f'Cavity: {cavity.name}')
            self._set_data(cavityitem, ref2)

        obj.set_treeitem(treeitem)

    def add_note(self, obj: _note.Note):
        """Add a note.

        UNKNOWN details are inferred from the callable name and signature.

        :param obj: Object instance to operate on.
        :type obj: :class:`_note.Note`
        """
        ref = weakref.ref(obj, self.__remove_refs)
        self._weakrefs.append(ref)

        treeitem = self._append_item(self._notes, obj.db_obj.notes)
        self._set_data(treeitem, ref)

        obj.set_treeitem(treeitem)

    def add_seal(self, obj: _seal.Seal):
        """Add a seal.

        UNKNOWN details are inferred from the callable name and signature.

        :param obj: Object instance to operate on.
        :type obj: :class:`_seal.Seal`
        """
        ref = weakref.ref(obj, self.__remove_refs)
        self._weakrefs.append(ref)

        treeitem = self._append_item(self._seals, obj.db_obj.name, True)
        self._set_data(treeitem, ref)

        housing = obj.db_obj.housing
        cavity = obj.db_obj.cavity
        terminal = obj.db_obj.terminal

        if housing is not None:
            ref2 = weakref.ref(housing, self.__remove_refs)
            self._weakrefs.append(ref2)
            child = self._append_item(treeitem, f'Housing: {housing.name}')
            self._set_data(child, ref2)
        elif cavity is not None:
            ref2 = weakref.ref(cavity, self.__remove_refs)
            self._weakrefs.append(ref2)
            child = self._append_item(treeitem, f'Cavity: {cavity.name}')
            self._set_data(child, ref2)
        elif terminal is not None:
            ref2 = weakref.ref(terminal, self.__remove_refs)
            self._weakrefs.append(ref2)
            child = self._append_item(treeitem, f'Terminal: {terminal.name}')
            self._set_data(child, ref2)

        obj.set_treeitem(treeitem)

    def add_splice(self, obj: _splice.Splice):
        """Add a splice.

        UNKNOWN details are inferred from the callable name and signature.

        :param obj: Object instance to operate on.
        :type obj: :class:`_splice.Splice`
        """
        ref = weakref.ref(obj, self.__remove_refs)
        self._weakrefs.append(ref)

        treeitem = self._append_item(self._splices, obj.db_obj.name, True)
        self._set_data(treeitem, ref)

        for wire in obj.db_obj.wires:
            ref2 = weakref.ref(wire, self.__remove_refs)
            self._weakrefs.append(ref2)
            child = self._append_item(treeitem, f'Wire: {wire.name}')
            self._set_data(child, ref2)

        obj.set_treeitem(treeitem)

    def add_terminal(self, obj: _terminal.Terminal):
        """Add a terminal.

        UNKNOWN details are inferred from the callable name and signature.

        :param obj: Object instance to operate on.
        :type obj: :class:`_terminal.Terminal`
        """
        ref = weakref.ref(obj, self.__remove_refs)
        self._weakrefs.append(ref)

        treeitem = self._append_item(self._terminals, obj.db_obj.name, True)
        self._set_data(treeitem, ref)

        seal = obj.db_obj.seal
        cavity = obj.db_obj.cavity
        circuit = obj.db_obj.circuit

        if seal is not None:
            ref2 = weakref.ref(seal, self.__remove_refs)
            self._weakrefs.append(ref2)
            child = self._append_item(treeitem, f'Seal: {seal.name}')
            self._set_data(child, ref2)
        if cavity is not None:
            ref2 = weakref.ref(cavity, self.__remove_refs)
            self._weakrefs.append(ref2)
            child = self._append_item(treeitem, f'Cavity: {cavity.name}')
            self._set_data(child, ref2)
        if circuit is not None:
            ref2 = weakref.ref(circuit, self.__remove_refs)
            self._weakrefs.append(ref2)
            child = self._append_item(treeitem, f'Circuit: {circuit.name}')
            self._set_data(child, ref2)

        obj.set_treeitem(treeitem)

    def add_tpa_lock(self, obj: _tpa_lock.TPALock):
        """Add a TPA lock.

        UNKNOWN details are inferred from the callable name and signature.

        :param obj: Object instance to operate on.
        :type obj: :class:`_tpa_lock.TPALock`
        """
        ref = weakref.ref(obj, self.__remove_refs)
        self._weakrefs.append(ref)

        treeitem = self._append_item(self._tpa_locks, obj.db_obj.name, True)
        self._set_data(treeitem, ref)

        housing = obj.db_obj.housing
        ref2 = weakref.ref(housing, self.__remove_refs)
        self._weakrefs.append(ref2)
        child = self._append_item(treeitem, f'Housing: {housing.name}')
        self._set_data(child, ref2)

        obj.set_treeitem(treeitem)

    def add_transition(self, obj: _transition.Transition):
        """Add a transition.

        UNKNOWN details are inferred from the callable name and signature.

        :param obj: Object instance to operate on.
        :type obj: :class:`_transition.Transition`
        """
        ref = weakref.ref(obj, self.__remove_refs)
        self._weakrefs.append(ref)

        treeitem = self._append_item(self._transitions, obj.db_obj.name, True)
        self._set_data(treeitem, ref)

        branches = [obj.db_obj.branch1, obj.db_obj.branch2, obj.db_obj.branch3,
                    obj.db_obj.branch4, obj.db_obj.branch5, obj.db_obj.branch6]

        for i, branch in enumerate(branches):
            if branch is None:
                continue

            branch_treeitem = self._append_item(treeitem, f'Branch {i + 1}', True)
            bundle = branch.bundle
            if bundle is not None:
                ref2 = weakref.ref(bundle, self.__remove_refs)
                self._weakrefs.append(ref2)
                child = self._append_item(branch_treeitem, f'Bundle: {bundle.name}')
                self._set_data(child, ref2)

            wires_treeitem = self._append_item(branch_treeitem, 'Wires', True)
            for wire in branch.wires:
                ref2 = weakref.ref(wire, self.__remove_refs)
                self._weakrefs.append(ref2)
                child = self._append_item(wires_treeitem, f'Wire: {wire.name}')
                self._set_data(child, ref2)

        obj.set_treeitem(treeitem)

    def add_wire(self, obj: _wire.Wire):
        """Add a wire.

        UNKNOWN details are inferred from the callable name and signature.

        :param obj: Object instance to operate on.
        :type obj: :class:`_wire.Wire`
        """
        ref = weakref.ref(obj, self.__remove_refs)
        self._weakrefs.append(ref)

        treeitem = self._append_item(self._wires, obj.db_obj.name, True)
        self._set_data(treeitem, ref)

        terminals = obj.db_obj.terminals
        circuit = obj.db_obj.circuit
        wire_markers = obj.db_obj.wire_markers

        if circuit is not None:
            ref2 = weakref.ref(circuit, self.__remove_refs)
            self._weakrefs.append(ref2)
            child = self._append_item(treeitem, f'Circuit: {circuit.name}')
            self._set_data(child, ref2)

        terminals_treeitem = self._append_item(treeitem, 'Terminals', True)
        for terminal in terminals:
            ref2 = weakref.ref(terminal, self.__remove_refs)
            self._weakrefs.append(ref2)
            child = self._append_item(terminals_treeitem, f'Terminal: {terminal.name}')
            self._set_data(child, ref2)

        markers_treeitem = self._append_item(treeitem, 'Wire Markers', True)
        for marker in wire_markers:
            ref2 = weakref.ref(marker, self.__remove_refs)
            self._weakrefs.append(ref2)
            child = self._append_item(markers_treeitem, f'Marker: {marker.name}')
            self._set_data(child, ref2)

        obj.set_treeitem(treeitem)

    def add_wire_marker(self, obj: _wire_marker.WireMarker):
        """Add a wire marker.

        UNKNOWN details are inferred from the callable name and signature.

        :param obj: Object instance to operate on.
        :type obj: :class:`_wire_marker.WireMarker`
        """
        ref = weakref.ref(obj, self.__remove_refs)
        self._weakrefs.append(ref)

        treeitem = self._append_item(self._wire_markers, obj.db_obj.name, True)
        self._set_data(treeitem, ref)

        wire = obj.db_obj.wire
        ref2 = weakref.ref(wire, self.__remove_refs)
        self._weakrefs.append(ref2)
        child = self._append_item(treeitem, f'Wire: {wire.name}')
        self._set_data(child, ref2)

    def add_wire_service_loop(self, obj: _wire_service_loop.WireServiceLoop):
        """Add a wire service loop.

        UNKNOWN details are inferred from the callable name and signature.

        :param obj: Object instance to operate on.
        :type obj: :class:`_wire_service_loop.WireServiceLoop`
        """
        ref = weakref.ref(obj, self.__remove_refs)
        self._weakrefs.append(ref)

        treeitem = self._append_item(self._wire_markers, obj.db_obj.name, True)
        self._set_data(treeitem, ref)

        wire = obj.db_obj.wire
        ref2 = weakref.ref(wire, self.__remove_refs)
        self._weakrefs.append(ref2)
        child = self._append_item(treeitem, f'Wire: {wire.name}')
        self._set_data(child, ref2)

        terminal = obj.db_obj.terminal
        circuit = obj.db_obj.circuit

        if terminal is not None:
            ref2 = weakref.ref(terminal, self.__remove_refs)
            self._weakrefs.append(ref2)
            child = self._append_item(treeitem, f'Terminal: {terminal.name}')
            self._set_data(child, ref2)

        if circuit is not None:
            ref2 = weakref.ref(circuit, self.__remove_refs)
            self._weakrefs.append(ref2)
            child = self._append_item(treeitem, f'Circuit: {circuit.name}')
            self._set_data(child, ref2)

    def set_selected(self, obj):
        """Set the selected.

        UNKNOWN details are inferred from the callable name and signature.

        :param obj: Object instance to operate on.
        :type obj: UNKNOWN
        """
        if obj is not None:
            treeitem = obj.get_treeitem()
            if treeitem is not None:
                self._treectrl.scrollToItem(treeitem)

    def add_object(self, obj):
        """Add an object.

        UNKNOWN details are inferred from the callable name and signature.

        :param obj: Object instance to operate on.
        :type obj: UNKNOWN
        """
        self._objects.append(obj)

    def remove_object(self, obj):
        """Remove the object.

        UNKNOWN details are inferred from the callable name and signature.

        :param obj: Object instance to operate on.
        :type obj: UNKNOWN
        """
        try:
            self._objects.remove(obj)
        except ValueError:
            pass
