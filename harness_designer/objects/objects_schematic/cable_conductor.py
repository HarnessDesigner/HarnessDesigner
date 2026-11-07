# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

"""The schematic view of a cable conductor (``TWISTED_WIRE_DESIGN.md`` section 8a, step 8).

A cable is never drawn in the schematic, and neither are the leads it is split into: a conductor is drawn as one wire from the
terminal or splice at the end of its lead at one cable end to the one at the end of its lead at the other. That is an ordinary
schematic wire between two 2D points (the leads' own end points, so it follows the terminals), with the ordinary single list of
2D waypoints, so this is the schematic wire view as it is. What differs is who it belongs to: its parent is the conductor's
:class:`~harness_designer.objects.cable_conductor.ConductorRun`, which answers what the router asks of a wire, and its menu is a
short one, because a conductor cannot be split, branched or deleted from the schematic (it is part of a cable).
"""

from typing import TYPE_CHECKING

from PySide6 import QtWidgets

from . import wire as _wire_schematic
from ..objects_3d import menu_ops as _menu_ops
from ... import check_types as _check_types
from ...crash_dump import capturable


if TYPE_CHECKING:
    from .. import cable_conductor as _cable_conductor
    from ...ui.editor_schematic import editor_schematic as _editor_schematic


@capturable()
class CableConductor(_wire_schematic.Wire):
    """The schematic view of one conductor of a split cable."""

    parent: "_cable_conductor.ConductorRun" = None

    @_check_types.do
    def get_context_menu(self) -> "ConductorMenu":
        """Return the context menu.

        :rtype: :class:`ConductorMenu`
        """
        return ConductorMenu(self.editor2d.editor, self)


class ConductorMenu(QtWidgets.QMenu):
    """The context menu of a cable conductor in the schematic: select it and look at its properties."""

    @_check_types.do
    def __init__(self, canvas: "_editor_schematic.EditorSchematicPanel", selected: CableConductor):
        """Initialise the :class:`ConductorMenu` instance.

        :param canvas: The schematic editor panel.
        :param selected: The conductor's schematic view.
        """
        QtWidgets.QMenu.__init__(self)
        self.canvas = canvas
        self.selected = selected

        action = self.addAction('Select')
        action.triggered.connect(self.on_select)

        self.addSeparator()
        action = self.addAction('Properties')
        action.triggered.connect(self.on_properties)

    @_check_types.do
    def on_select(self) -> None:
        """Make this conductor the active selection."""
        _menu_ops.select_object(self.selected)

    @_check_types.do
    def on_properties(self) -> None:
        """Show this conductor's properties in the object editor."""
        _menu_ops.show_properties(self.selected)
