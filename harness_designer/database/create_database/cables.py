# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

"""
Schema for ``pjt_cables``.

A placed CABLE: a wire part that is shielded or has more than one conductor (see ``Wire.is_cable`` in
``global_db/mixins/wire_conductor.py`` and ``TWISTED_WIRE_DESIGN.md`` section 8a in the repo root). The cable is the
physical thing that is placed, routed, drawn and listed once in the bill of materials; what a circuit contains is its
conductors (``pjt_cable_conductors``), not the cable. So this table mirrors ``pjt_wires`` for position, route and
visibility, and has no ``circuit_id``, no ``operating_temp`` and no ``is_filler_wire``.

There is no 2D (schematic) point and no schematic visibility: like a bundle, a cable is never drawn in the schematic,
where each conductor is drawn as its own wire.

``start_split_mm`` / ``stop_split_mm`` are how far from the cable's start / stop end the conductors are split apart.
``0.0`` means that end is not split yet (the conductors still leave together). The conductors' own split points are
on the ``pjt_cable_conductors`` rows.

``roll_deg`` is how far a ribbon cable's flat side is turned about its axis, degrees, at the start of the trunk (0 for the
frame the 3D view picks). Unused by any other cable.

NEW 2026-11-05, nothing draws a cable yet.
"""

# transition_branches first: transitions and transition_branches import each other, and that only works when
# transition_branches is the one imported first. The schema walk (``pjt_bases._schema_dependency_order``) imports every
# module of this package in alphabetical order and reaches this one ("cable") before anything else has loaded them.
from . import transition_branches as _transition_branches  # NOQA
from . import wires as _wires
from . import points3d as _points3d
from . import points_pegboard as _points_pegboard
from . import bundle_covers as _bundle_covers
from . import transitions as _transitions
from .. import db_connectors as _con


pjt_id_field = _con.UUIDField('id', is_primary=True)

pjt_table = _con.SQLTable(
    'pjt_cables',
    pjt_id_field,
    _con.UUIDField('part_id', no_null=True,
                   references=_con.SQLFieldReference(_wires.table,
                                                     _wires.id_field,
                                                     on_delete=_con.REFERENCE_NO_ACTION,
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
    _con.UUIDField('start_point_pegboard_id', default='NULL',
                   references=_con.SQLFieldReference(_points_pegboard.pjt_table,
                                                     _points_pegboard.pjt_id_field,
                                                     on_update=_con.REFERENCE_NO_ACTION)),
    _con.UUIDField('stop_point_pegboard_id', default='NULL',
                   references=_con.SQLFieldReference(_points_pegboard.pjt_table,
                                                     _points_pegboard.pjt_id_field,
                                                     on_update=_con.REFERENCE_NO_ACTION)),
    _con.FloatField('start_split_mm', default='"0.0"', no_null=True),
    _con.FloatField('stop_split_mm', default='"0.0"', no_null=True),
    _con.FloatField('roll_deg', default='"0.0"', no_null=True),
    _con.TextField('notes', default='""', no_null=True),
    _con.IntField('is_visible3d', default='1', no_null=True),
    _con.IntField('is_visible_pegboard', default='1', no_null=True),
    _con.IntField('smooth', default='NULL'),
    _con.TextField('name', default='""', no_null=True)
)
