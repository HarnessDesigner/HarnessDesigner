# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

"""
Schema for ``pjt_cable_conductors``.

One row per conductor of a placed cable (``pjt_cables``), plus one for its shielding when the cable part is shielded
(``is_shield``; the catalog's ``wire_conductors`` has no row for a shield). A conductor is wire-like: it is what a
circuit contains and it has end points that land on a terminal or splice, so this table has every column of
``pjt_wires`` under the same name (``PJTCableConductor`` subclasses ``PJTWire``) and the columns below on top of those.

The row holds NO copy of the conductor's own values: ``conductor_id`` is the row of ``wire_conductors`` (the catalog) it is,
and its colour, stripe colour, plating, insulation material, size, strands, ``od_mm`` and ``resistance_1km`` are read from there,
so a change made to the part is made everywhere the part is used. A shield has no catalog row (``conductor_id`` is NULL).

``start_point*_id`` / ``stop_point*_id`` are where the conductor lands (its terminal or splice). The ``*_split_point*_id``
columns are where it leaves the cable's trunk at that end; a cable end that is not split has the two together.
``start_order`` / ``stop_order`` are the place of the conductor in the fan-out at that end (``idx`` by default).

NEW 2026-11-05, nothing draws a conductor yet.
"""

from . import cables as _cables
from . import circuits as _circuits
from . import wires as _wires
from . import wire_conductors as _wire_conductors
from . import points2d as _points2d
from . import points3d as _points3d
from . import points_pegboard as _points_pegboard
from . import bundle_covers as _bundle_covers
from . import transitions as _transitions
from . import concentric_layers as _concentric_layers
from .. import db_connectors as _con


pjt_id_field = _con.UUIDField('id', is_primary=True)

pjt_table = _con.SQLTable(
    'pjt_cable_conductors',
    pjt_id_field,

    # ---- the columns of pjt_wires, same names (the PJTWire mixins read them) ----
    # the cable's catalog wire (the same part as the cable's)
    _con.UUIDField('part_id', no_null=True,
                   references=_con.SQLFieldReference(_wires.table,
                                                     _wires.id_field,
                                                     on_delete=_con.REFERENCE_NO_ACTION,
                                                     on_update=_con.REFERENCE_NO_ACTION)),
    _con.UUIDField('circuit_id', default='NULL',
                   references=_con.SQLFieldReference(_circuits.pjt_table,
                                                     _circuits.pjt_id_field,
                                                     on_update=_con.REFERENCE_NO_ACTION)),
    _con.UUIDField('bundle_id', default='NULL',
                   references=_con.SQLFieldReference(_bundle_covers.pjt_table,
                                                     _bundle_covers.pjt_id_field,
                                                     on_update=_con.REFERENCE_NO_ACTION)),
    _con.UUIDField('transition_id', default='NULL',
                   references=_con.SQLFieldReference(_transitions.pjt_table,
                                                     _transitions.pjt_id_field,
                                                     on_update=_con.REFERENCE_NO_ACTION)),
    _con.UUIDField('start_point3d_id', default='NULL',
                   references=_con.SQLFieldReference(_points3d.pjt_table,
                                                     _points3d.pjt_id_field,
                                                     on_update=_con.REFERENCE_NO_ACTION)),
    _con.UUIDField('stop_point3d_id', default='NULL',
                   references=_con.SQLFieldReference(_points3d.pjt_table,
                                                     _points3d.pjt_id_field,
                                                     on_update=_con.REFERENCE_NO_ACTION)),
    _con.UUIDField('start_point2d_id', default='NULL',
                   references=_con.SQLFieldReference(_points2d.pjt_table,
                                                     _points2d.pjt_id_field,
                                                     on_update=_con.REFERENCE_NO_ACTION)),
    _con.UUIDField('stop_point2d_id', default='NULL',
                   references=_con.SQLFieldReference(_points2d.pjt_table,
                                                     _points2d.pjt_id_field,
                                                     on_update=_con.REFERENCE_NO_ACTION)),
    _con.UUIDField('start_point_pegboard_id', default='NULL',
                   references=_con.SQLFieldReference(_points_pegboard.pjt_table,
                                                     _points_pegboard.pjt_id_field,
                                                     on_update=_con.REFERENCE_NO_ACTION)),
    _con.UUIDField('stop_point_pegboard_id', default='NULL',
                   references=_con.SQLFieldReference(_points_pegboard.pjt_table,
                                                     _points_pegboard.pjt_id_field,
                                                     on_update=_con.REFERENCE_NO_ACTION)),
    _con.UUIDField('layer_view_point_id', default='NULL',
                   references=_con.SQLFieldReference(_points2d.pjt_table,
                                                     _points2d.pjt_id_field,
                                                     on_update=_con.REFERENCE_NO_ACTION)),
    _con.UUIDField('layer_id', default='NULL',
                   references=_con.SQLFieldReference(_concentric_layers.pjt_table,
                                                     _concentric_layers.pjt_id_field,
                                                     on_update=_con.REFERENCE_NO_ACTION)),
    _con.IntField('is_filler_wire', default='0', no_null=True),
    _con.TextField('notes', default='""', no_null=True),
    _con.IntField('is_visible2d', default='1', no_null=True),
    _con.IntField('is_visible3d', default='1', no_null=True),
    _con.IntField('is_visible_pegboard', default='1', no_null=True),
    _con.IntField('smooth', default='NULL'),
    _con.TextField('name', default='""', no_null=True),
    _con.FloatField('operating_temp', default='NULL'),

    # ---- what a conductor adds ----
    _con.UUIDField('cable_id', no_null=True,
                   references=_con.SQLFieldReference(_cables.pjt_table,
                                                     _cables.pjt_id_field,
                                                     on_delete=_con.REFERENCE_NO_ACTION,
                                                     on_update=_con.REFERENCE_NO_ACTION)),
    # the place inside the cable (0 first); a shield is the last
    _con.IntField('idx', no_null=True),
    # the row is the cable's shielding, not a conductor
    _con.IntField('is_shield', default='0', no_null=True),
    # the catalog conductor (wire_conductors) this row is; NULL for a shield
    _con.UUIDField('conductor_id', default='NULL',
                   references=_con.SQLFieldReference(_wire_conductors.table,
                                                     _wire_conductors.id_field,
                                                     on_update=_con.REFERENCE_NO_ACTION)),
    # where the conductor leaves the cable's trunk, per view and end (see the module docstring)
    _con.UUIDField('start_split_point3d_id', default='NULL',
                   references=_con.SQLFieldReference(_points3d.pjt_table,
                                                     _points3d.pjt_id_field,
                                                     on_update=_con.REFERENCE_NO_ACTION)),
    _con.UUIDField('stop_split_point3d_id', default='NULL',
                   references=_con.SQLFieldReference(_points3d.pjt_table,
                                                     _points3d.pjt_id_field,
                                                     on_update=_con.REFERENCE_NO_ACTION)),
    _con.UUIDField('start_split_point_pegboard_id', default='NULL',
                   references=_con.SQLFieldReference(_points_pegboard.pjt_table,
                                                     _points_pegboard.pjt_id_field,
                                                     on_update=_con.REFERENCE_NO_ACTION)),
    _con.UUIDField('stop_split_point_pegboard_id', default='NULL',
                   references=_con.SQLFieldReference(_points_pegboard.pjt_table,
                                                     _points_pegboard.pjt_id_field,
                                                     on_update=_con.REFERENCE_NO_ACTION)),
    _con.IntField('start_order', default='0', no_null=True),
    _con.IntField('stop_order', default='0', no_null=True),
)
