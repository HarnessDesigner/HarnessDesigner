# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

"""
Schema for ``pjt_cable_paths``.

The route of a placed cable (``pjt_cables``): one row per interior waypoint per view, in order. The same shape as
``pjt_wire_paths`` (see ``wire_paths.py``) and read by the same code (``PJTCablePathsTable`` subclasses
``PJTWirePathsTable``), but a table of its own so that nothing that walks the wires' routes and then looks the id up in
``pjt_wires`` meets a cable's id (a waypoint's marker, a bundle's wires, the peg-board rope pull ...). The column is
still called ``wire_id`` so the inherited code works unchanged; here it holds a cable's id.

NEW 2026-11-05.
"""

from . import cables as _cables
from . import points3d as _points3d
from . import points2d as _points2d
from . import points_pegboard as _points_pegboard
from . import bundle_covers as _bundle_covers
from . import concentrics as _concentrics
from . import transitions as _transitions
from . import transition_branches as _transition_branches
from .. import db_connectors as _con


pjt_id_field = _con.UUIDField('id', is_primary=True)

pjt_table = _con.SQLTable(
    'pjt_cable_paths',
    pjt_id_field,
    _con.UUIDField('wire_id', no_null=True,
                   references=_con.SQLFieldReference(_cables.pjt_table,
                                                     _cables.pjt_id_field,
                                                     on_delete=_con.REFERENCE_NO_ACTION,
                                                     on_update=_con.REFERENCE_NO_ACTION)),
    _con.UUIDField('point3d_id', default='NULL',
                   references=_con.SQLFieldReference(_points3d.pjt_table,
                                                     _points3d.pjt_id_field,
                                                     on_delete=_con.REFERENCE_NO_ACTION,
                                                     on_update=_con.REFERENCE_NO_ACTION)),
    _con.UUIDField('point_pegboard_id', default='NULL',
                   references=_con.SQLFieldReference(_points_pegboard.pjt_table,
                                                     _points_pegboard.pjt_id_field,
                                                     on_delete=_con.REFERENCE_NO_ACTION,
                                                     on_update=_con.REFERENCE_NO_ACTION)),
    _con.UUIDField('point2d_id', default='NULL',
                   references=_con.SQLFieldReference(_points2d.pjt_table,
                                                     _points2d.pjt_id_field,
                                                     on_delete=_con.REFERENCE_NO_ACTION,
                                                     on_update=_con.REFERENCE_NO_ACTION)),
    _con.IntField('idx', no_null=True),
    _con.UUIDField('bundle_id', default='NULL',
                   references=_con.SQLFieldReference(_bundle_covers.pjt_table,
                                                     _bundle_covers.pjt_id_field,
                                                     on_delete=_con.REFERENCE_NO_ACTION,
                                                     on_update=_con.REFERENCE_NO_ACTION)),
    _con.UUIDField('concentric_id', default='NULL',
                   references=_con.SQLFieldReference(_concentrics.pjt_table,
                                                     _concentrics.pjt_id_field,
                                                     on_delete=_con.REFERENCE_NO_ACTION,
                                                     on_update=_con.REFERENCE_NO_ACTION)),
    _con.UUIDField('transition_id', default='NULL',
                   references=_con.SQLFieldReference(_transitions.pjt_table,
                                                     _transitions.pjt_id_field,
                                                     on_delete=_con.REFERENCE_NO_ACTION,
                                                     on_update=_con.REFERENCE_NO_ACTION)),
    _con.UUIDField('transition_branch_id', default='NULL',
                   references=_con.SQLFieldReference(_transition_branches.pjt_table,
                                                     _transition_branches.pjt_id_field,
                                                     on_delete=_con.REFERENCE_NO_ACTION,
                                                     on_update=_con.REFERENCE_NO_ACTION))
)
