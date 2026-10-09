# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

"""Blue "this is where the selected wire goes" highlight for the Peg Board
Editor.

Selecting a wire row in ANY peg-board wire table (housing, bundle or
transition) lights up everything that wire touches, so a transition's one
table can show which branch each wire goes through:

- the wire itself, if it is visible in the peg-board view -- otherwise the
  bundle(s) it is routed through (a wire inside a bundle isn't drawn; the
  bundle is)
- each transition BRANCH the wire is routed through -- never the whole
  transition, only its branches
- the wire's end parts: the housing when the terminal is seated in one,
  the terminal itself when it isn't

Bundle and branch membership is read from ``pjt_wire_paths`` (the
``bundle_id``/``transition_branch_id`` tags on a wire's route rows), the
same source ``PJTBundle``/``PJTTransitionBranch`` use to list a table's
wires, so the highlight and the table rows always agree.

Objects are lit through their existing ``identify()`` override (the same
mechanism the add handlers use for hover highlights); a transition branch
through ``Transition.highlight_branch()``. One instance per editor
(``EditorPegboard.wire_highlight``) holds the current highlight so a new
selection, or clearing the selection, can undo it.
"""

from typing import TYPE_CHECKING, Union as _Union

from ...gl import materials as _materials
from ... import color as _color
from ... import config as _config
from ... import check_types as _check_types


if TYPE_CHECKING:
    from .. import object_base as _object_base
    from ...ui import editor_pegboard as _editor_pegboard
    from ...database import project_db as _project_db
    from . import base_pegboard as _base_pegboard
    from . import transition as _transition


Config = _config.Config.editor_pegboard


class WireHighlight:
    """The editor's single current wire highlight -- see the module
    docstring."""

    @_check_types.do
    def __init__(self, editor: "_editor_pegboard.EditorPegboard") -> None:
        """Initialise the :class:`WireHighlight` instance.

        :param editor: The Peg Board Editor to repaint after a change.
        :type editor: :class:`_editor_pegboard.EditorPegboard`
        """
        self._editor = editor
        self._owner: _Union["_base_pegboard.BasePegboard", None] = None
        self._objects: list["_base_pegboard.BasePegboard"] = []
        self._transitions: list["_transition.Transition"] = []

    @_check_types.do
    def show(self, owner: "_base_pegboard.BasePegboard", ptables: "_project_db.PJTTables", wire_id: bytes) -> None:
        """Highlight everything *wire_id* touches, replacing any
        highlight already showing.

        :param owner: Whoever is asking (the table the selection was made
            in) -- only that same owner can later :meth:`clear` it.
        :type owner: object
        :param ptables: The project's tables.
        :type ptables: :class:`_project_db.PJTTables`
        :param wire_id: The selected ``pjt_wires`` row id.
        :type wire_id: bytes
        """
        self._undo()
        self._owner = owner

        material = _materials.Glowing(_color.Color(*Config.wire_highlight_color))

        self._light_wire_or_bundles(ptables, wire_id, material)
        self._light_branches(ptables, wire_id, material)
        self._light_ends(ptables, wire_id, material)

        self._editor.Refresh()

    @_check_types.do
    def clear(self, owner: "_base_pegboard.BasePegboard") -> None:
        """Remove the highlight, if *owner* is the one that made it.

        :param owner: Whoever is asking to clear.
        :type owner: object
        """
        if owner is not self._owner:
            return

        self._undo()
        self._editor.Refresh()

    @_check_types.do
    def _undo(self) -> None:
        for obj in self._objects:
            if not obj.parent._deleted:  # NOQA
                obj.identify(None)

        for transition in self._transitions:
            if not transition.parent._deleted:  # NOQA
                transition.clear_branch_highlights()

        self._objects = []
        self._transitions = []
        self._owner = None

    @_check_types.do
    def _add_object(self, facade: _Union["_object_base.ObjectBase", None],
                    material: _materials.GLMaterial) -> None:
        """Light *facade*'s peg-board view (skipped if it has none)."""
        if facade is None or facade.objpegboard is None:
            return

        facade.objpegboard.identify(material)
        self._objects.append(facade.objpegboard)

    @_check_types.do
    def _light_wire_or_bundles(self, ptables: "_project_db.PJTTables", wire_id: bytes,
                               material: _materials.GLMaterial) -> None:
        wire_facade = ptables.pjt_wires_table[wire_id].get_object()

        if wire_facade is not None and wire_facade.objpegboard is not None:
            if wire_facade.objpegboard.is_visible:
                self._add_object(wire_facade, material)
                return

        for bundle_id in ptables.pjt_wire_paths_table.bundle_ids_for_wire(wire_id):
            self._add_object(ptables.pjt_bundles_table[bundle_id].get_object(), material)

    @_check_types.do
    def _light_branches(self, ptables: "_project_db.PJTTables", wire_id: bytes,
                        material: _materials.GLMaterial) -> None:
        """Light each transition branch the wire is routed through --
        the branch only, never the transition's hub or body."""
        for branch_id in ptables.pjt_wire_paths_table.transition_branch_ids_for_wire(wire_id):
            branch = ptables.pjt_transition_branches_table[branch_id]

            transition_facade = branch.transition.get_object()
            if transition_facade is None or transition_facade.objpegboard is None:
                continue

            transition = transition_facade.objpegboard

            for peg_branch in transition.branches:
                if peg_branch.db_obj is None or peg_branch.db_obj.db_id != branch.db_id:
                    continue

                transition.highlight_branch(peg_branch, material)

                if transition not in self._transitions:
                    self._transitions.append(transition)

    @_check_types.do
    def _light_ends(self, ptables: "_project_db.PJTTables", wire_id: bytes,
                    material: _materials.GLMaterial) -> None:
        """Light what each end of the wire is attached to: the housing
        its terminal is seated in, or the terminal itself when it isn't
        in one."""
        wire = ptables.pjt_wires_table[wire_id]

        for point_id in (wire.start_position3d_id, wire.stop_position3d_id):
            if point_id is None:
                continue

            for row in ptables.pjt_terminals_table.select('id', attach_point3d_id=point_id):
                terminal = ptables.pjt_terminals_table[row[0]]
                cavity_id = terminal.cavity_id

                if cavity_id is None:
                    self._add_object(terminal.get_object(), material)
                else:
                    housing = ptables.pjt_cavities_table[cavity_id].housing
                    self._add_object(housing.get_object(), material)
