# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

from . import projects as _projects

from .. import db_connectors as _con


pjt_id_field = _con.PrimaryKeyField('id')

pjt_table = _con.SQLTable(
    'pjt_points3d',
    pjt_id_field,
    _con.IntField('project_id', no_null=True,
                  references=_con.SQLFieldReference(_projects.pjt_table,
                                                    _projects.pjt_id_field,
                                                    on_delete=_con.REFERENCE_CASCADE,
                                                    on_update=_con.REFERENCE_CASCADE)),
    _con.FloatField('x', no_null=True),
    _con.FloatField('y', no_null=True),
    _con.FloatField('z', no_null=True),
    # Wire/bundle-waypoint-only columns -- NULL for every other point3d row
    # (an anchor referenced FROM its owning row's own position3d_id/
    # *_point3d_id FK, same as always). Self-identifying via wire_id/
    # bundle_id + idx instead of being referenced from elsewhere, mirroring
    # pjt_points_peg's bundle_id/idx. A single row is only ever one or the
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
    _con.IntField('wire_id', default='NULL'),
    _con.IntField('bundle_id', default='NULL'),
    _con.IntField('idx', default='NULL')
)
