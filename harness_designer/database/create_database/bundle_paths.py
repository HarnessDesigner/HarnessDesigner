# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

from . import bundle_covers as _bundle_covers
from . import points3d as _points3d
from . import points_pegboard as _points_pegboard
from .. import db_connectors as _con


pjt_id_field = _con.UUIDField('id', is_primary=True)

# A bundle's own interior waypoints, in order: one row per point per bundle
# per view. Every row always has bundle_id, idx and exactly one of
# point3d_id/point_pegboard_id (enforced in PJTBundlePathsTable.insert) --
# no point2d_id, bundles are never shown in the schematic view. The point
# rows referenced here are shared with whatever else uses them (e.g. the
# routes of the wires that run through the bundle), which is why idx lives
# here and not on the point row. The bundle's own start and stop stay as
# columns on pjt_bundles, exterior to this list.
pjt_table = _con.SQLTable(
    'pjt_bundle_paths',
    pjt_id_field,
    _con.UUIDField('bundle_id', no_null=True,
                   references=_con.SQLFieldReference(_bundle_covers.pjt_table,
                                                     _bundle_covers.pjt_id_field,
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
    _con.IntField('idx', no_null=True)
)
