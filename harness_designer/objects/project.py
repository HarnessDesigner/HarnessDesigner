from typing import TYPE_CHECKING, Iterator as _Iterator
import wx

from ..config import Config as _Config

from . import boot as _boot
from . import bundle as _bundle
from . import bundle_layout as _bundle_layout
from . import circuit as _circuit
from . import cover as _cover
from . import cpa_lock as _cpa_lock
from . import housing as _housing
from . import note as _note
from . import seal as _seal
from . import splice as _splice
from . import terminal as _terminal
from . import tpa_lock as _tpa_lock
from . import transition as _transition
from . import wire as _wire
from . import wire_marker as _wire_marker
from . import wire_service_loop as _wire_service_loop
from . import wire2d_layout as _wire2d_layout
from . import wire3d_layout as _wire3d_layout

if TYPE_CHECKING:
    from .. import ui as _ui


class Config(metaclass=_Config):
    recent_projects = []


class Project:

    def __init__(self, mainframe: "_ui.MainFrame", project_name: str, project_id: int):
        self.mainframe = mainframe
        self.gtables = mainframe.global_db
        self.connector = mainframe.db_connector
        self.project_id = project_id
        self.project_name = project_name
        self.ptables = ptables = mainframe.project_db

        ptables.load(project_id)

        self._boots = {}
        self._bundles = {}
        self._bundle_layouts = {}
        self._covers = {}
        self._cpa_locks = {}
        self._housings = {}
        self._notes = {}
        self._seals = {}
        self._splices = {}
        self._terminals = {}
        self._tpa_locks = {}
        self._transitions = {}
        self._wires = {}
        self._wire_markers = {}
        self._wire_service_loops = {}
        self._wire2d_layouts = {}
        self._wire3d_layouts = {}
        self._circuits = {}

        self._obj_count = mainframe.project_db.projects_table.get_object_count(project_id)

        mainframe.ShowProgress(self._obj_count)

        for wire_service_loop in ptables.pjt_wire_service_loops_table:
            mainframe.IncrementProgress()
            self._wire_service_loops[wire_service_loop.db_id] = (
                _wire_service_loop.WireServiceLoop(mainframe, wire_service_loop))

        for wire_marker in ptables.pjt_wire_markers_table:
            mainframe.IncrementProgress()
            self._wire_markers[wire_marker.db_id] = (
                _wire_marker.WireMarker(mainframe, wire_marker))

        for note in ptables.pjt_notes_table:
            mainframe.IncrementProgress()
            self._notes[note.db_id] = _note.Note(mainframe, note)

        for circuit in ptables.pjt_circuits_table:
            mainframe.IncrementProgress()
            self._circuits[circuit.db_id] = (
                _circuit.Circuit(mainframe, circuit))

        for boot in ptables.pjt_boots_table:
            mainframe.IncrementProgress()
            self._boots[boot.db_id] = _boot.Boot(mainframe, boot)

        for cover in ptables.pjt_covers_table:
            mainframe.IncrementProgress()
            self._covers[cover.db_id] = _cover.Cover(mainframe, cover)

        for cpa_lock in ptables.pjt_cpa_locks_table:
            mainframe.IncrementProgress()
            self._cpa_locks[cpa_lock.db_id] = (
                _cpa_lock.CPALock(mainframe, cpa_lock))

        for tpa_lock in ptables.pjt_tpa_locks_table:
            mainframe.IncrementProgress()
            self._tpa_locks[tpa_lock.db_id] = (
                _tpa_lock.TPALock(mainframe, tpa_lock))

        for seal in ptables.pjt_seals_table:
            mainframe.IncrementProgress()
            self._seals[seal.db_id] = _seal.Seal(mainframe, seal)

        for terminal in ptables.pjt_terminals_table:
            mainframe.IncrementProgress()
            self._terminals[terminal.db_id] = (
                _terminal.Terminal(mainframe, terminal))

        for transition in ptables.pjt_transitions_table:
            mainframe.IncrementProgress()
            self._transitions[transition.db_id] = (
                _transition.Transition(mainframe, transition))

        for housing in ptables.pjt_housings_table:
            mainframe.IncrementProgress()
            self._housings[housing.db_id] = (
                _housing.Housing(mainframe, housing))

        for splice in ptables.pjt_splices_table:
            mainframe.IncrementProgress()
            self._splices[splice.db_id] = _splice.Splice(mainframe, splice)

        for wire in ptables.pjt_wires_table:
            mainframe.IncrementProgress()
            self._wires[wire.db_id] = _wire.Wire(mainframe, wire)

        for layout in ptables.pjt_wire2d_layouts_table:
            mainframe.IncrementProgress()
            self._wire2d_layouts[layout.db_id] = (
                _wire2d_layout.Wire2DLayout(mainframe, layout))

        for layout in ptables.pjt_wire3d_layouts_table:
            mainframe.IncrementProgress()
            self._wire3d_layouts[layout.db_id] = (
                _wire3d_layout.Wire3DLayout(mainframe, layout))

        for bundle in ptables.pjt_bundles_table:
            mainframe.IncrementProgress()
            self._bundles[bundle.db_id] = _bundle.Bundle(mainframe, bundle)

        for layout in ptables.pjt_bundle_layouts_table:
            mainframe.IncrementProgress()
            self._bundle_layouts[layout.db_id] = (
                _bundle_layout.BundleLayout(mainframe, layout))

        mainframe.IncrementProgress()

    @classmethod
    def select_project(cls, mainframe: "_ui.MainFrame") -> "Project":
        from ..dialogs.project_dialog import OpenProjectDialog

        connector = mainframe.db_connector

        project_names = []

        connector.execute(f'SELECT name FROM projects;')
        for name in connector.fetchall():
            project_names.append(name[0])

        dlg = OpenProjectDialog(mainframe, Config.recent_projects, project_names)

        try:
            if dlg.ShowModal() != wx.ID_CANCEL:
                project_name = dlg.GetValue()
            else:
                return
        finally:
            dlg.Destroy()

        connector.execute(f'SELECT id FROM projects WHERE name = "{project_name}";')
        res = connector.fetchall()

        if res:
            project_id = res[0][0]
        else:
            connector.execute(f'INSERT INTO projects (name) VALUES (?);', (project_name,))
            connector.commit()
            project_id = connector.lastrowid

        return cls(mainframe, project_name, project_id)

    def delete_note(self, db_id):
        note = self._notes.pop(db_id)
        note.delete()
        self.obj_count -= 1

    def add_note(self, point2d, point3d):
        pass

    @property
    def notes(self) -> list["_note.Note"]:
        return list(self._notes.values())

    def delete_seal(self, db_id):
        seal = self._seals.pop(db_id)
        seal.delete()
        self.obj_count -= 1

    def add_note(self, point2d, point3d):
        pass

    @property
    def seals(self) -> list["_seal.Seal"]:
        return list(self._seals.values())

    @property
    def terminals(self) -> list["_terminal.Terminal"]:
        return list(self._terminals.values())

    @property
    def tpa_locks(self) -> list["_tpa_lock.TPALock"]:
        return list(self._tpa_locks.values())

    @property
    def wire_markers(self) -> list["_wire_marker.WireMarker"]:
        return list(self._wire_markers.values())

    @property
    def wire_service_loops(self) -> list["_wire_service_loop.WireServiceLoop"]:
        return list(self._wire_service_loops.values())

    @property
    def circuits(self) -> list["_circuit.Circuit"]:
        return list(self._circuits.values())

    @property
    def cpa_locks(self) -> list["_cpa_lock.CPALock"]:
        return list(self._cpa_locks.values())

    @property
    def covers(self) -> list["_cover.Cover"]:
        return list(self._covers.values())

    @property
    def boots(self) -> list["_boot.Boot"]:
        return list(self._boots.values())

    @property
    def transitions(self) -> list["_transition.Transition"]:
        return list(self._transitions.values())

    @property
    def housings(self) -> list["_housing.Housing"]:
        return list(self._housings.values())

    @property
    def splices(self) -> list["_splice.Splice"]:
        return list(self._splices.values())

    @property
    def wires(self) -> list["_wire.Wire"]:
        return list(self._wires.values())

    @property
    def wire2d_layouts(self) -> list["_wire2d_layout.Wire2DLayout"]:
        return list(self._wire2d_layouts.values())

    @property
    def wire3d_layouts(self) -> list["_wire3d_layout.Wire3DLayout"]:
        return list(self._wire3d_layouts.values())

    @property
    def bundles(self) -> list["_bundle.Bundle"]:
        return list(self._bundles.values())

    @property
    def bundle_layouts(self) -> list["_bundle_layout.BundleLayout"]:
        return list(self._bundle_layouts.values())

    @property
    def recent_projects(self) -> _Iterator:
        return Config.recent_projects[:]
