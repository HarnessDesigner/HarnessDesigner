# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

"""The routes of the placed cables (``pjt_cable_paths``).

Exactly :class:`~.pjt_wire_path.PJTWirePathsTable`, over a table of its own: the same ``add`` / ``append`` / ``remove`` /
``point_ids`` / ``set_route`` code, and the same row class, but a cable's id never appears in ``pjt_wire_paths``, where
every reader of a wire's route goes on to look the id up in ``pjt_wires``. The ``wire_id`` column holds a cable's id.
"""

from .pjt_wire_path import PJTWirePathsTable
from ... import check_types as _check_types


class PJTCablePathsTable(PJTWirePathsTable):
    """The table of cable routes: one row per point per cable per view."""

    __table_name__ = 'pjt_cable_paths'

    @_check_types.do
    def _table_needs_update(self) -> bool:
        """Return whether the table is missing any schema fields.

        :returns: ``True`` when the table is missing a defined field.
        :rtype: bool
        """
        from ..create_database import cable_paths

        return cable_paths.pjt_table.is_ok(self)

    @_check_types.do
    def _add_table_to_db(self) -> None:
        """Create the ``pjt_cable_paths`` table in the database."""
        from ..create_database import cable_paths

        cable_paths.pjt_table.add_to_db(self)

    @_check_types.do
    def _update_table_in_db(self) -> None:
        """Add any missing fields to the ``pjt_cable_paths`` table."""
        from ..create_database import cable_paths

        cable_paths.pjt_table.update_fields(self)
