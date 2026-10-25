# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

"""Circuit membership for a freshly connected wire.

A circuit is the set of wires, splices, terminals and wire service loops that
carry one signal (see ``database.project_db.pjt_circuit``). It is never typed
in while drawing a wire; it follows from what the wire ends on.
:func:`reconcile_wire_circuit` runs once a wire's ends are attached -- from
the three add-wire handlers, ``wire_snap.commit_snap`` and
``wire_drag_base.merge_wire_into`` -- and works the circuit out from the
wire's two ends and the wire itself, in that order (start end first):

* none of them is in a circuit and one end is a terminal: a new circuit is
  created and the first terminal becomes its start terminal;
* exactly one circuit among them: the wire and every end that has none join it;
* two or more circuits: the user is asked whether to merge them into the
  first (start-side) one. Declining leaves everything as it was.

Drawing a wire never takes a circuit away from anything, so nothing here
removes a member from a circuit.

The circuit then spreads to the entire chain of connected objects (``PJTCircuitsTable.propagate``), so the wire's whole chain is
looked at when deciding: a circuit anywhere along it, not only on the two ends, takes part in the choice above.

The same moment is when the operating temperature spreads: a connected part
that has none takes the value of what it is connected to, and when the parts
hold different values the user is asked whether to make them all the same
(see :func:`_replicate_operating_temp`).
"""

from typing import TYPE_CHECKING

from PySide6 import QtWidgets

from .. import check_types as _check_types


if TYPE_CHECKING:
    from ..objects import project as _project
    from ..objects import wire as _wire


@_check_types.do
def _reconcile_circuits(project: "_project.Project", wire: "_wire.Wire") -> None:
    """Put *wire*, the objects at its two ends and everything connected to them into one circuit.

    Reads the ends from :attr:`Wire.start_sibling`/:attr:`Wire.stop_sibling`,
    so call it only after the wire's ends are attached. A free or
    wire-layout end is not a member and is skipped.

    :param project: The loaded project.
    :type project: :class:`_project.Project`
    :param wire: The wire whose ends were just attached.
    :type wire: :class:`_wire.Wire`
    """
    ends = []

    start_sibling = wire.start_sibling
    if start_sibling is not None:
        ends.append(start_sibling)

    stop_sibling = wire.stop_sibling
    if stop_sibling is not None:
        ends.append(stop_sibling)

    # Start end first, then the wire, then the stop end: when two circuits
    # meet, the start side's wins.
    rows = []
    if start_sibling is not None:
        rows.append(start_sibling.db_obj)

    rows.append(wire.db_obj)

    if stop_sibling is not None:
        rows.append(stop_sibling.db_obj)

    circuits_table = project.ptables.pjt_circuits_table

    # The whole chain the wire is part of, not only the two objects it ends on: the chosen circuit spreads to all of it, so a
    # circuit further along has to be part of the decision. The two ends and the wire stay first, so the start side still wins.
    chain = list(rows)
    seen = {row.db_id for row in chain}

    for row in circuits_table.connected_members(wire.db_obj):
        if row.db_id not in seen:
            seen.add(row.db_id)
            chain.append(row)

    circuit_ids = []
    for row in chain:
        circuit_id = row.circuit_id

        if circuit_id is not None and circuit_id not in circuit_ids:
            circuit_ids.append(circuit_id)

    if not circuit_ids:
        if not any(end.is_terminal for end in ends):
            return

        keep = project.create_circuit().db_obj
    else:
        keep = circuits_table[circuit_ids[0]]

        if len(circuit_ids) > 1:
            others = [circuits_table[circuit_id] for circuit_id in circuit_ids[1:]]
            labels = ', '.join(other.label for other in others)

            button = QtWidgets.QMessageBox.question(
                project.mainframe, 'Join Circuits',
                f'This wire connects circuit {keep.label} to circuit '
                f'{labels}.\n\nMerge them into circuit {keep.label}?')

            if button == QtWidgets.QMessageBox.StandardButton.No:
                return

            for other in others:
                project.merge_circuits(keep.db_id, other.db_id)

    for row in rows:
        keep.add_member(row)


@_check_types.do
def _replicate_operating_temp(project: "_project.Project", wire: "_wire.Wire") -> None:
    """Give *wire* and the objects at its two ends one operating temperature.

    Parts that hold no value take the one the others hold. When the parts
    hold different values, a Yes/No dialog asks whether to set them all to the
    start side's value (a harness passing a firewall legitimately has parts at
    different temperatures, so No leaves everything as it was).

    :param project: The loaded project.
    :type project: :class:`_project.Project`
    :param wire: The wire whose ends were just attached.
    :type wire: :class:`_wire.Wire`
    """
    entries = []

    start_sibling = wire.start_sibling
    if start_sibling is not None:
        if start_sibling.is_terminal:
            entries.append(('Terminal', start_sibling.db_obj))
        elif start_sibling.is_splice:
            entries.append(('Splice', start_sibling.db_obj))
        else:
            entries.append(('Wire service loop', start_sibling.db_obj))

    entries.append(('Wire', wire.db_obj))

    stop_sibling = wire.stop_sibling
    if stop_sibling is not None:
        if stop_sibling.is_terminal:
            entries.append(('Terminal', stop_sibling.db_obj))
        elif stop_sibling.is_splice:
            entries.append(('Splice', stop_sibling.db_obj))
        else:
            entries.append(('Wire service loop', stop_sibling.db_obj))

    values = []
    for _, row in entries:
        value = row.operating_temp

        if value is not None and value not in values:
            values.append(value)

    if not values:
        return

    if len(values) > 1:
        lines = []
        for kind, row in entries:
            value = row.operating_temp

            if value is not None:
                lines.append(f'{kind}: {value:g} \u00b0C')

        button = QtWidgets.QMessageBox.question(
            project.mainframe, 'Operating Temperature',
            'These connected parts work at different temperatures:\n\n'
            + '\n'.join(lines)
            + f'\n\nSet them all to {values[0]:g} \u00b0C?')

        if button == QtWidgets.QMessageBox.StandardButton.No:
            return

    for _, row in entries:
        if row.operating_temp != values[0]:
            row.operating_temp = values[0]


@_check_types.do
def reconcile_wire_circuit(project: "_project.Project", wire: "_wire.Wire") -> None:
    """Settle what a freshly connected wire shares with the objects at its two
    ends: their circuit (:func:`_reconcile_circuits`) and their operating
    temperature (:func:`_replicate_operating_temp`).

    Reads the ends from :attr:`Wire.start_sibling`/:attr:`Wire.stop_sibling`,
    so call it only after the wire's ends are attached.

    :param project: The loaded project.
    :type project: :class:`_project.Project`
    :param wire: The wire whose ends were just attached.
    :type wire: :class:`_wire.Wire`
    """
    _reconcile_circuits(project, wire)
    _replicate_operating_temp(project, wire)
