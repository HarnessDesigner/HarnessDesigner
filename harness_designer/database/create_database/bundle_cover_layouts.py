# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

from . import projects as _projects
from . import points3d as _points3d
from . import points_pegboard as _points_pegboard


from .. import db_connectors as _con


pjt_id_field = _con.UUIDField('id', is_primary=True)

pjt_table = _con.SQLTable(
    'pjt_bundle_layouts',
    pjt_id_field,
    # Exactly one of point3d_id/point_pegboard_id is ever non-NULL per
    # row (no point2d_id -- bundles are never shown in the schematic
    # view) -- a waypoint's layout is keyed to the specific view it was
    # placed in, since waypoint counts differ per view (see
    # PJTBundleLayout's own exclusive position handling).
    _con.UUIDField('point3d_id', default='NULL',
                   references=_con.SQLFieldReference(_points3d.pjt_table,
                                                     _points3d.pjt_id_field,
                                                     on_delete=_con.REFERENCE_CASCADE,
                                                     on_update=_con.REFERENCE_CASCADE)),
    _con.UUIDField('point_pegboard_id', default='NULL',
                   references=_con.SQLFieldReference(_points_pegboard.pjt_table,
                                                     _points_pegboard.pjt_id_field,
                                                     on_delete=_con.REFERENCE_CASCADE,
                                                     on_update=_con.REFERENCE_CASCADE)),
    _con.TextField('notes', default='""', no_null=True),
    _con.IntField('is_visible3d', default='1', no_null=True),
    _con.IntField('is_visible_pegboard', default='1', no_null=True),
    _con.IntField('smooth', default='NULL')
)
