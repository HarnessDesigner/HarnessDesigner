# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

from . import projects as _projects

from .. import db_connectors as _con


pjt_id_field = _con.UUIDField('id', is_primary=True)

pjt_table = _con.SQLTable(
    'pjt_points3d',
    pjt_id_field,
    _con.FloatField('x', no_null=True),
    _con.FloatField('y', no_null=True),
    _con.FloatField('z', no_null=True),
    # Wire/bundle-waypoint-only columns -- NULL for every other point3d row
    # (an anchor referenced FROM its owning row's own position3d_id/
    # *_point3d_id FK, same as always). Self-identifying via wire_id/
    # bundle_id + idx instead of being referenced from elsewhere, mirroring
    # pjt_points_pegboard's bundle_id/idx. A single row is only ever one or the
    # other (or neither) -- never both -- so idx is shared between the two
    # rather than needing its own bundle_idx column.
    #
    # No SQLFieldReference to pjt_wires/pjt_bundles here -- wires.py/
    # bundle_covers.py already import this module for their own start/stop
    # point3d FK columns, so a real FK back the other way would be a
    # circular module import. Same resolution as pjt_bundles.
    # table_point_peg_id (see bundle_covers.py): still holds a real row id,
    # just without a DB-enforced constraint. Cleanup on delete is explicit
    # (see PJTWire.delete/PJTBundle.delete).
    _con.UUIDField('wire_id', default='NULL'),
    _con.UUIDField('bundle_id', default='NULL'),
    _con.IntField('idx', default='NULL'),
    # Set only on a cloned point (see objects.terminal.Terminal.
    # _own_or_cloned_point_id) -- the id of the "real"/canonical point this
    # one was cloned from (a terminal's own wire_point3d/attach_point3d, or
    # a cavity's own wire_position3d), so a housing move/rotate can find
    # every clone and move it right along with its parent instead of
    # leaving it behind. No SQLFieldReference for the same reason wire_id/
    # bundle_id above have none -- this table can't reference its own
    # not-yet-fully-defined pjt_table from within its own definition.
    # Present on every pjt_point* table (points2d/points_pegboard included) even
    # though only points3d needs it today, so all three stay structurally
    # identical for whatever future use needs it on the others.
    _con.UUIDField('parent_point_id', default='NULL')
)
