# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

"""Schema for ``pjt_pegboard_points``.

One row per anchor (housing, splice endpoint, transition, transition
branch, bare terminal, bundle-layout point, etc.) that has been given a
position on the peg-board view. The table is keyed purely by ``point3d_id``
-- it has no knowledge of what kind of anchor owns that 3D point. A row is
created lazily the first time the anchor is dragged in the peg-board view.
"""

from . import projects as _projects
from . import points3d as _points3d

from .. import db_connectors as _con


pjt_id_field = _con.PrimaryKeyField('id')

pjt_table = _con.SQLTable(
    'pjt_pegboard_points',
    pjt_id_field,
    _con.IntField('project_id', no_null=True,
                  references=_con.SQLFieldReference(_projects.pjt_table,
                                                    _projects.pjt_id_field,
                                                    on_delete=_con.REFERENCE_CASCADE,
                                                    on_update=_con.REFERENCE_CASCADE)),
    _con.IntField('point3d_id', no_null=True, is_unique=True,
                  references=_con.SQLFieldReference(_points3d.pjt_table,
                                                    _points3d.pjt_id_field,
                                                    on_delete=_con.REFERENCE_CASCADE,
                                                    on_update=_con.REFERENCE_CASCADE)),
    _con.FloatField('x', no_null=True, default='0.0'),
    _con.FloatField('y', no_null=True, default='0.0'),
    _con.FloatField('rotation', no_null=True, default='0.0'),
    _con.IntField('is_user_placed', no_null=True, default='0')
)
