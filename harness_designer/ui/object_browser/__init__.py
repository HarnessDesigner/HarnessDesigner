from typing import TYPE_CHECKING

import wx

from wx import aui

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


class ObjectBrowser(aui.AuiPaneInfo):

    def __init__(self, mainframe: "_mainframe.MainFrame"):
        self.editor = ObjectBrowserPanel(mainframe)
        self.mainframe = mainframe
        self.manager = mainframe.manager

        aui.AuiPaneInfo.__init__(self)

        self.Name('object_browser')
        self.CaptionVisible()
        self.Floatable()
        self.MinimizeButton()
        self.MaximizeButton()
        self.Dockable()
        self.CloseButton(True)
        self.PaneBorder()
        self.Caption('Object Browser')
        self.DestroyOnClose(False)
        self.Gripper()
        self.Left()
        self.Resizable()
        self.Window(self.editor)

        self.manager.AddPane(self.editor, self)
        self.Show()
        self.manager.Update()

    def add_boot(self, obj: _boot.Boot):
        self.editor.add_boot(obj)

    def add_bundle(self, obj: _bundle.Bundle):
        self.editor.add_bundle(obj)

    def add_cavity(self, obj: _cavity.Cavity):
        self.editor.add_cavity(obj)

    def add_circuit(self, obj: _circuit.Circuit):
        self.editor.add_circuit(obj)

    def add_cover(self, obj: _cover.Cover):
        self.editor.add_cover(obj)

    def add_cpa_lock(self, obj: _cpa_lock.CPALock):
        self.editor.add_cpa_lock(obj)

    def add_housing(self, obj: _housing.Housing):
        self.editor.add_housing(obj)

    def add_note(self, obj: _note.Note):
        self.editor.add_note(obj)

    def add_seal(self, obj: _seal.Seal):
        self.editor.add_seal(obj)

    def add_splice(self, obj: _splice.Splice):
        self.editor.add_splice(obj)

    def add_terminal(self, obj: _terminal.Terminal):
        self.editor.add_terminal(obj)

    def add_tpa_lock(self, obj: _tpa_lock.TPALock):
        self.editor.add_tpa_lock(obj)

    def add_transition(self, obj: _transition.Transition):
        self.editor.add_transition(obj)

    def add_wire(self, obj: _wire.Wire):
        self.editor.add_wire(obj)

    def add_wire_marker(self, obj: _wire_marker.WireMarker):
        self.editor.add_wire_marker(obj)

    def add_wire_service_loop(self, obj: _wire_service_loop.WireServiceLoop):
        self.editor.add_wire_service_loop(obj)

    def reset(self):
        self.editor.reset()

    def set_selected(self, obj):
        self.editor.set_selected(obj)

    def add_object(self, obj):
        self.editor.add_object(obj)

    def remove_object(self, obj):
        self.editor.remove_object(obj)

    def Refresh(self, *args, **kwargs):
        self.editor.Refresh(*args, **kwargs)

    def Destroy(self):
        self.editor.Destroy()


class ObjectBrowserPanel(wx.Panel):

    def __init__(self, parent: "_mainframe.MainFrame"):
        wx.Panel.__init__(self, parent, wx.ID_ANY, style=wx.BORDER_NONE)
        self.mainframe = parent

        self._objects = []
        self._selected = None
        self._treectrl = wx.TreeCtrl(
            self, wx.ID_ANY, style=wx.TR_HAS_BUTTONS | wx.TR_SINGLE)

        hsizer = wx.BoxSizer(wx.HORIZONTAL)
        vsizer = wx.BoxSizer(wx.VERTICAL)

        hsizer.Add(self._treectrl, 1, wx.EXPAND)
        vsizer.Add(hsizer, 1, wx.EXPAND | wx.ALL, 10)
        self.SetSizer(vsizer)

        self._root: wx.TreeItemId = None
        self._boots: wx.TreeItemId = None
        self._bundles: wx.TreeItemId = None
        self._cavities: wx.TreeItemId = None
        self._circuits: wx.TreeItemId = None
        self._covers: wx.TreeItemId = None
        self._cpa_locks: wx.TreeItemId = None
        self._housings: wx.TreeItemId = None
        self._notes: wx.TreeItemId = None
        self._seals: wx.TreeItemId = None
        self._splices: wx.TreeItemId = None
        self._terminals: wx.TreeItemId = None
        self._tpa_locks: wx.TreeItemId = None
        self._transitions: wx.TreeItemId = None
        self._wires: wx.TreeItemId = None
        self._wire_markers: wx.TreeItemId = None
        self._weakrefs = []

        # EVT_TREE_ITEM_ACTIVATED
        # EVT_TREE_ITEM_MENU
        # EVT_TREE_SEL_CHANGED
        #
        # EVT_TREE_ITEM_COLLAPSING
        # EVT_TREE_ITEM_EXPANDING

    def reset(self):
        self._treectrl.DeleteAllItems()
        self._root = self._treectrl.AddRoot('root')

        self._boots = self._treectrl.AppendItem(self._root, 'Boots')
        self._treectrl.SetItemHasChildren(self._boots, True)

        self._bundles = self._treectrl.AppendItem(self._root, 'Bundles')
        self._treectrl.SetItemHasChildren(self._bundles, True)

        self._cavities = self._treectrl.AppendItem(self._root, 'Cavities')
        self._treectrl.SetItemHasChildren(self._cavities, True)

        self._circuits = self._treectrl.AppendItem(self._root, 'Circuits')
        self._treectrl.SetItemHasChildren(self._circuits, True)

        self._covers = self._treectrl.AppendItem(self._root, 'Covers')
        self._treectrl.SetItemHasChildren(self._covers, True)

        self._cpa_locks = self._treectrl.AppendItem(self._root, 'CPA Locks')
        self._treectrl.SetItemHasChildren(self._cpa_locks, True)

        self._housings = self._treectrl.AppendItem(self._root, 'Housings')
        self._treectrl.SetItemHasChildren(self._housings, True)

        self._notes = self._treectrl.AppendItem(self._root, 'Notes')
        self._treectrl.SetItemHasChildren(self._notes, True)

        self._seals = self._treectrl.AppendItem(self._root, 'Seals')
        self._treectrl.SetItemHasChildren(self._seals, True)

        self._splices = self._treectrl.AppendItem(self._root, 'Splices')
        self._treectrl.SetItemHasChildren(self._splices, True)

        self._terminals = self._treectrl.AppendItem(self._root, 'Terminals')
        self._treectrl.SetItemHasChildren(self._terminals, True)

        self._tpa_locks = self._treectrl.AppendItem(self._root, 'TPA Locks')
        self._treectrl.SetItemHasChildren(self._tpa_locks, True)

        self._transitions = self._treectrl.AppendItem(self._root, 'Transitions')
        self._treectrl.SetItemHasChildren(self._transitions, True)

        self._wires = self._treectrl.AppendItem(self._root, 'Wires')
        self._treectrl.SetItemHasChildren(self._wires, True)

        self._wire_markers = self._treectrl.AppendItem(self._root, 'Wire Markers')
        self._treectrl.SetItemHasChildren(self._wire_markers, True)

        self._weakrefs = []

    def __remove_refs(self, ref):

        def iter_tree(parent):
            child, cookie = self._treectrl.GetFirstChild(parent)

            while child.IsOk():
                d_ref = self._treectrl.GetItemData(child)

                if d_ref is not None:
                    data = d_ref()
                    if data is None:
                        if self._treectrl.ItemHasChildren(child):
                            self._treectrl.DeleteChildren(child)
                        else:
                            self._treectrl.Delete(child)

                if child.IsOk() and self._treectrl.ItemHasChildren(child):
                    iter_tree(child)

                child = self._treectrl.GetNextChild(parent, cookie)

        iter_tree(self._root)

        self._weakrefs.remove(ref)

    def add_boot(self, obj: _boot.Boot):
        ref = weakref.ref(obj, self.__remove_refs)
        self._weakrefs.append(ref)

        treeitem = self._treectrl.AppendItem(self._boots, obj.db_obj.name)
        self._treectrl.SetItemHasChildren(treeitem, True)
        self._treectrl.SetItemData(treeitem, ref)

        housing = obj.db_obj.housing

        ref = weakref.ref(housing, self.__remove_refs)
        self._weakrefs.append(ref)

        child = self._treectrl.AppendItem(treeitem, f'Housing: {housing.name}')
        self._treectrl.SetItemData(child, ref)

        obj.set_treeitem(treeitem)

    def add_bundle(self, obj: _bundle.Bundle):
        ref = weakref.ref(obj, self.__remove_refs)
        self._weakrefs.append(ref)

        treeitem = self._treectrl.AppendItem(self._bundles, obj.db_obj.name)
        self._treectrl.SetItemHasChildren(treeitem, True)
        self._treectrl.SetItemData(treeitem, ref)

        for wire in obj.db_obj.wires:
            ref = weakref.ref(wire, self.__remove_refs)
            self._weakrefs.append(ref)

            child = self._treectrl.AppendItem(treeitem, f'Wire: {wire.name}')
            self._treectrl.SetItemData(child, ref)

        obj.set_treeitem(treeitem)

    def add_cavity(self, obj: _cavity.Cavity):
        ref = weakref.ref(obj, self.__remove_refs)
        self._weakrefs.append(ref)

        treeitem = self._treectrl.AppendItem(self._cavities, obj.db_obj.name)
        self._treectrl.SetItemHasChildren(treeitem, True)
        self._treectrl.SetItemData(treeitem, ref)

        housing = obj.db_obj.housing

        ref = weakref.ref(housing, self.__remove_refs)
        self._weakrefs.append(ref)

        child = self._treectrl.AppendItem(treeitem, f'Housing: {housing.name}')
        self._treectrl.SetItemData(child, ref)

        terminal = obj.db_obj.terminal
        if terminal is not None:
            ref = weakref.ref(terminal, self.__remove_refs)
            self._weakrefs.append(ref)

            child = self._treectrl.AppendItem(treeitem, f'Terminal: {terminal.name}')
            self._treectrl.SetItemData(child, ref)

        seal = obj.db_obj.seal
        if seal is not None:
            ref = weakref.ref(seal, self.__remove_refs)
            self._weakrefs.append(ref)

            child = self._treectrl.AppendItem(treeitem, f'Seal: {seal.name}')
            self._treectrl.SetItemData(child, ref)

        obj.set_treeitem(treeitem)

    def add_circuit(self, obj: _circuit.Circuit):
        ref = weakref.ref(obj, self.__remove_refs)
        self._weakrefs.append(ref)

        treeitem = self._treectrl.AppendItem(self._circuits, obj.db_obj.name)
        self._treectrl.SetItemHasChildren(treeitem, True)
        self._treectrl.SetItemData(treeitem, ref)

        wire_treeitem = self._treectrl.AppendItem(treeitem, 'Wires')
        self._treectrl.SetItemHasChildren(wire_treeitem, True)
        for wire in obj.db_obj.wires:
            ref = weakref.ref(wire, self.__remove_refs)
            self._weakrefs.append(ref)

            wireitem = self._treectrl.AppendItem(wire_treeitem, f'Wire: {wire.name}')
            self._treectrl.SetItemData(wireitem, ref)

        loop_treeitem = self._treectrl.AppendItem(treeitem, 'Wire Service Loops')
        self._treectrl.SetItemHasChildren(loop_treeitem, True)
        for wire in obj.db_obj.wire_service_loops:
            ref = weakref.ref(wire, self.__remove_refs)
            self._weakrefs.append(ref)

            loopitem = self._treectrl.AppendItem(loop_treeitem, f'Wire Loop: {wire.name}')
            self._treectrl.SetItemData(loopitem, ref)

        terminal_treeitem = self._treectrl.AppendItem(treeitem, 'Terminals')
        self._treectrl.SetItemHasChildren(terminal_treeitem, True)
        for terminal in obj.db_obj.terminals:
            ref = weakref.ref(terminal, self.__remove_refs)
            self._weakrefs.append(ref)

            terminalitem = self._treectrl.AppendItem(terminal_treeitem, f'Terminal: {terminal.name}')
            self._treectrl.SetItemData(terminalitem, ref)

        splice_treeitem = self._treectrl.AppendItem(treeitem, 'Splices')
        self._treectrl.SetItemHasChildren(splice_treeitem, True)
        for splice in obj.db_obj.splices:
            ref = weakref.ref(splice, self.__remove_refs)
            self._weakrefs.append(ref)

            spliceitem = self._treectrl.AppendItem(splice_treeitem, f'Splice: {splice.name}')
            self._treectrl.SetItemData(spliceitem, ref)

        obj.set_treeitem(treeitem)

    def add_cover(self, obj: _cover.Cover):
        ref = weakref.ref(obj, self.__remove_refs)
        self._weakrefs.append(ref)

        treeitem = self._treectrl.AppendItem(self._covers, obj.db_obj.name)
        self._treectrl.SetItemHasChildren(treeitem, True)
        self._treectrl.SetItemData(treeitem, ref)

        housing = obj.db_obj.housing

        ref = weakref.ref(housing, self.__remove_refs)
        self._weakrefs.append(ref)

        child = self._treectrl.AppendItem(treeitem, f'Housing: {housing.name}')
        self._treectrl.SetItemData(child, ref)

        obj.set_treeitem(treeitem)

    def add_cpa_lock(self, obj: _cpa_lock.CPALock):
        ref = weakref.ref(obj, self.__remove_refs)
        self._weakrefs.append(ref)

        treeitem = self._treectrl.AppendItem(self._cpa_locks, obj.db_obj.name)
        self._treectrl.SetItemHasChildren(treeitem, True)
        self._treectrl.SetItemData(treeitem, ref)

        housing = obj.db_obj.housing

        ref = weakref.ref(housing, self.__remove_refs)
        self._weakrefs.append(ref)

        child = self._treectrl.AppendItem(treeitem, f'Housing: {housing.name}')
        self._treectrl.SetItemData(child, ref)

        obj.set_treeitem(treeitem)

    def add_housing(self, obj: _housing.Housing):
        ref = weakref.ref(obj, self.__remove_refs)
        self._weakrefs.append(ref)

        treeitem = self._treectrl.AppendItem(self._housings, obj.db_obj.name)
        self._treectrl.SetItemHasChildren(treeitem, True)
        self._treectrl.SetItemData(treeitem, ref)

        seal = obj.db_obj.seal
        cover = obj.db_obj.cover
        cpa_lock = obj.db_obj.cpa_lock
        tpa_locks = obj.db_obj.tpa_locks
        cavities = obj.db_obj.cavities

        if seal is not None:
            ref = weakref.ref(seal, self.__remove_refs)
            self._weakrefs.append(ref)

            child = self._treectrl.AppendItem(treeitem, f'Seal: {seal.name}')
            self._treectrl.SetItemData(child, ref)

        if cover is not None:
            ref = weakref.ref(cover, self.__remove_refs)
            self._weakrefs.append(ref)

            child = self._treectrl.AppendItem(treeitem, f'Cover: {cover.name}')
            self._treectrl.SetItemData(child, ref)

        if cpa_lock is not None:
            ref = weakref.ref(cpa_lock, self.__remove_refs)
            self._weakrefs.append(ref)

            child = self._treectrl.AppendItem(treeitem, f'CPA Lock: {cpa_lock.name}')
            self._treectrl.SetItemData(child, ref)

        tpa_locks_treeitem = self._treectrl.AppendItem(treeitem, 'TPA Locks')
        self._treectrl.SetItemHasChildren(tpa_locks_treeitem, True)
        for lock in tpa_locks:
            ref = weakref.ref(lock, self.__remove_refs)
            self._weakrefs.append(ref)

            lockitem = self._treectrl.AppendItem(tpa_locks_treeitem, f'TPA Lock: {lock.name}')
            self._treectrl.SetItemData(lockitem, ref)

        cavities_treeitem = self._treectrl.AppendItem(treeitem, 'Cavities')
        self._treectrl.SetItemHasChildren(cavities_treeitem, True)
        for cavity in cavities:
            ref = weakref.ref(cavity, self.__remove_refs)
            self._weakrefs.append(ref)

            cavityitem = self._treectrl.AppendItem(cavities_treeitem, f'Cavity: {cavity.name}')
            self._treectrl.SetItemData(cavityitem, ref)

        obj.set_treeitem(treeitem)

    def add_note(self, obj: _note.Note):
        ref = weakref.ref(obj, self.__remove_refs)
        self._weakrefs.append(ref)

        treeitem = self._treectrl.AppendItem(self._notes, obj.db_obj.note)
        self._treectrl.SetItemHasChildren(treeitem, False)
        self._treectrl.SetItemData(treeitem, ref)

        obj.set_treeitem(treeitem)

    def add_seal(self, obj: _seal.Seal):
        ref = weakref.ref(obj, self.__remove_refs)
        self._weakrefs.append(ref)

        treeitem = self._treectrl.AppendItem(self._seals, obj.db_obj.name)
        self._treectrl.SetItemHasChildren(treeitem, True)
        self._treectrl.SetItemData(treeitem, ref)

        housing = obj.db_obj.housing
        cavity = obj.db_obj.cavity
        terminal = obj.db_obj.terminal

        if housing is not None:
            ref = weakref.ref(housing, self.__remove_refs)
            self._weakrefs.append(ref)

            child = self._treectrl.AppendItem(treeitem, f'Housing: {housing.name}')
            self._treectrl.SetItemData(child, ref)
        elif cavity is not None:
            ref = weakref.ref(cavity, self.__remove_refs)
            self._weakrefs.append(ref)

            child = self._treectrl.AppendItem(treeitem, f'Cavity: {cavity.name}')
            self._treectrl.SetItemData(child, ref)
        elif terminal is not None:
            ref = weakref.ref(terminal, self.__remove_refs)
            self._weakrefs.append(ref)

            child = self._treectrl.AppendItem(treeitem, f'Terminal: {terminal.name}')
            self._treectrl.SetItemData(child, ref)

        obj.set_treeitem(treeitem)

    def add_splice(self, obj: _splice.Splice):
        ref = weakref.ref(obj, self.__remove_refs)
        self._weakrefs.append(ref)

        treeitem = self._treectrl.AppendItem(self._splices, obj.db_obj.name)
        self._treectrl.SetItemHasChildren(treeitem, True)
        self._treectrl.SetItemData(treeitem, ref)

        for wire in obj.db_obj.wires:
            ref = weakref.ref(wire, self.__remove_refs)
            self._weakrefs.append(ref)

            child = self._treectrl.AppendItem(treeitem, f'Wire: {wire.name}')
            self._treectrl.SetItemData(child, ref)

        obj.set_treeitem(treeitem)

    def add_terminal(self, obj: _terminal.Terminal):
        ref = weakref.ref(obj, self.__remove_refs)
        self._weakrefs.append(ref)

        treeitem = self._treectrl.AppendItem(self._terminals, obj.db_obj.name)
        self._treectrl.SetItemHasChildren(treeitem, True)
        self._treectrl.SetItemData(treeitem, ref)

        seal = obj.db_obj.seal
        cavity = obj.db_obj.cavity
        circuit = obj.db_obj.circuit

        if seal is not None:
            ref = weakref.ref(seal, self.__remove_refs)
            self._weakrefs.append(ref)

            child = self._treectrl.AppendItem(treeitem, f'Seal: {seal.name}')
            self._treectrl.SetItemData(child, ref)
        if cavity is not None:
            ref = weakref.ref(cavity, self.__remove_refs)
            self._weakrefs.append(ref)

            child = self._treectrl.AppendItem(treeitem, f'Cavity: {cavity.name}')
            self._treectrl.SetItemData(child, ref)
        if circuit is not None:
            ref = weakref.ref(circuit, self.__remove_refs)
            self._weakrefs.append(ref)

            child = self._treectrl.AppendItem(treeitem, f'Circuit: {circuit.name}')
            self._treectrl.SetItemData(child, ref)

        obj.set_treeitem(treeitem)

    def add_tpa_lock(self, obj: _tpa_lock.TPALock):
        ref = weakref.ref(obj, self.__remove_refs)
        self._weakrefs.append(ref)

        treeitem = self._treectrl.AppendItem(self._tpa_locks, obj.db_obj.name)
        self._treectrl.SetItemHasChildren(treeitem, True)
        self._treectrl.SetItemData(treeitem, ref)

        housing = obj.db_obj.housing

        ref = weakref.ref(housing, self.__remove_refs)
        self._weakrefs.append(ref)

        child = self._treectrl.AppendItem(treeitem, f'Housing: {housing.name}')
        self._treectrl.SetItemData(child, ref)

        obj.set_treeitem(treeitem)

    def add_transition(self, obj: _transition.Transition):
        ref = weakref.ref(obj, self.__remove_refs)
        self._weakrefs.append(ref)

        treeitem = self._treectrl.AppendItem(self._transitions, obj.db_obj.name)
        self._treectrl.SetItemHasChildren(treeitem, True)
        self._treectrl.SetItemData(treeitem, ref)

        branch1 = obj.db_obj.branch1
        branch2 = obj.db_obj.branch2
        branch3 = obj.db_obj.branch3
        branch4 = obj.db_obj.branch4
        branch5 = obj.db_obj.branch5
        branch6 = obj.db_obj.branch6

        for i, branch in enumerate(
            [branch1, branch2, branch3, branch4, branch5, branch6]
        ):
            if branch is None:
                continue

            i += 1
            branch_treeitem = self._treectrl.AppendItem(treeitem, f'Branch {i}')
            self._treectrl.SetItemHasChildren(branch_treeitem, True)
            bundle = branch.bundle
            if bundle is not None:
                ref = weakref.ref(bundle, self.__remove_refs)
                self._weakrefs.append(ref)

                child = self._treectrl.AppendItem(branch_treeitem, f'Bundle: {bundle.name}')
                self._treectrl.SetItemData(child, ref)

            wires_treeitem = self._treectrl.AppendItem(branch_treeitem, 'Wires')
            self._treectrl.SetItemHasChildren(wires_treeitem, True)

            for wire in branch.wires:
                ref = weakref.ref(wire, self.__remove_refs)
                self._weakrefs.append(ref)

                child = self._treectrl.AppendItem(wires_treeitem, f'Wire: {wire.name}')
                self._treectrl.SetItemData(child, ref)

        obj.set_treeitem(treeitem)

    def add_wire(self, obj: _wire.Wire):
        ref = weakref.ref(obj, self.__remove_refs)
        self._weakrefs.append(ref)

        treeitem = self._treectrl.AppendItem(self._wires, obj.db_obj.name)
        self._treectrl.SetItemHasChildren(treeitem, True)
        self._treectrl.SetItemData(treeitem, ref)

        terminals = obj.db_obj.terminals
        circuit = obj.db_obj.circuit
        wire_markers = obj.db_obj.wire_markers

        if circuit is not None:
            ref = weakref.ref(circuit, self.__remove_refs)
            self._weakrefs.append(ref)

            child = self._treectrl.AppendItem(treeitem, f'Circuit: {circuit.name}')
            self._treectrl.SetItemData(child, ref)

        terminals_treeitem = self._treectrl.AppendItem(treeitem, 'Wire Markers')
        self._treectrl.SetItemHasChildren(terminals_treeitem, True)
        for terminal in terminals:
            ref = weakref.ref(terminal, self.__remove_refs)
            self._weakrefs.append(ref)

            child = self._treectrl.AppendItem(terminals_treeitem, f'Terminal: {terminal.name}')
            self._treectrl.SetItemData(child, ref)

        wires_treeitem = self._treectrl.AppendItem(treeitem, 'Wire Markers')
        self._treectrl.SetItemHasChildren(wires_treeitem, True)
        for marker in wire_markers:
            ref = weakref.ref(marker, self.__remove_refs)
            self._weakrefs.append(ref)

            child = self._treectrl.AppendItem(wires_treeitem, f'Housing: {marker.name}')
            self._treectrl.SetItemData(child, ref)

        obj.set_treeitem(treeitem)

    def add_wire_marker(self, obj: _wire_marker.WireMarker):
        ref = weakref.ref(obj, self.__remove_refs)
        self._weakrefs.append(ref)

        treeitem = self._treectrl.AppendItem(self._wire_markers, obj.db_obj.name)
        self._treectrl.SetItemHasChildren(treeitem, True)
        self._treectrl.SetItemData(treeitem, ref)

        wire = obj.db_obj.wire

        ref = weakref.ref(wire, self.__remove_refs)
        self._weakrefs.append(ref)

        child = self._treectrl.AppendItem(treeitem, f'Wire: {wire.name}')
        self._treectrl.SetItemData(child, ref)

    def add_wire_service_loop(self, obj: _wire_service_loop.WireServiceLoop):
        ref = weakref.ref(obj, self.__remove_refs)
        self._weakrefs.append(ref)

        treeitem = self._treectrl.AppendItem(self._wire_markers, obj.db_obj.name)
        self._treectrl.SetItemHasChildren(treeitem, True)
        self._treectrl.SetItemData(treeitem, ref)

        wire = obj.db_obj.wire

        ref = weakref.ref(wire, self.__remove_refs)
        self._weakrefs.append(ref)

        child = self._treectrl.AppendItem(treeitem, f'Wire: {wire.name}')
        self._treectrl.SetItemData(child, ref)

        terminal = obj.db_obj.terminal
        circuit = obj.db_obj.circuit

        if terminal is not None:
            ref = weakref.ref(terminal, self.__remove_refs)
            self._weakrefs.append(ref)

            child = self._treectrl.AppendItem(treeitem, f'Terminal: {terminal.name}')
            self._treectrl.SetItemData(child, ref)

        if circuit is not None:
            ref = weakref.ref(circuit, self.__remove_refs)
            self._weakrefs.append(ref)

            child = self._treectrl.AppendItem(treeitem, f'Circuit: {circuit.name}')
            self._treectrl.SetItemData(child, ref)

    def set_selected(self, obj):
        if obj is not None:
            treeitem = obj.get_treeitem()
            if treeitem.IsOk():
                self._treectrl.EnsureVisible(treeitem)

    def add_object(self, obj):
        self._objects.append(obj)

    def remove_object(self, obj):
        try:
            self._objects.remove(obj)
        except ValueError:
            pass
