# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

from . import projects as _projects

from .. import db_connectors as _con


pjt_id_field = _con.PrimaryKeyField('id')

pjt_table = _con.SQLTable(
    'pjt_points2d',
    pjt_id_field,
    _con.IntField('project_id', no_null=True,
                  references=_con.SQLFieldReference(_projects.pjt_table,
                                                    _projects.pjt_id_field,
                                                    on_delete=_con.REFERENCE_CASCADE,
                                                    on_update=_con.REFERENCE_CASCADE)),
    _con.FloatField('x', no_null=True),
    _con.FloatField('y', no_null=True),
    # Wire-waypoint-only columns -- NULL for every other point2d row (an
    # anchor referenced FROM its owning row's own position2d_id/*_point2d_id
    # FK, same as always). Self-identifying via wire_id/idx instead of being
    # referenced from elsewhere, mirroring pjt_points_peg's bundle_id/idx.
    #
    # No SQLFieldReference to pjt_wires here -- wires.py already imports
    # this module for pjt_wires' own start/stop point2d FK columns, so a
    # real FK back the other way would be a circular module import. Same
    # resolution as pjt_bundles.table_point_peg_id (see bundle_covers.py):
    # still holds a real pjt_wires row id, just without a DB-enforced
    # constraint. Cleanup on wire deletion is explicit (see PJTWire.delete).
    _con.IntField('wire_id', default='NULL'),
    _con.IntField('idx', default='NULL')
)
