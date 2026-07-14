# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

"""Schema for ``pjt_pegboard_tables``.

One row per anchor that has a visible Excel-like data table overlaid on the
peg-board view. Stores the table's geometry (in world units, not pixels)
and its scroll/collapse state. Keyed purely by ``point3d_id``, same as
``pjt_pegboard_points``.
"""

from . import projects as _projects
from . import points3d as _points3d

from .. import db_connectors as _con


pjt_id_field = _con.PrimaryKeyField('id')

pjt_table = _con.SQLTable(
    'pjt_pegboard_tables',
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
    _con.FloatField('x', no_null=True),
    _con.FloatField('y', no_null=True),
    _con.FloatField('width', no_null=True),
    _con.FloatField('height', no_null=True),
    _con.IntField('h_scroll', no_null=True, default='0'),
    _con.IntField('v_scroll', no_null=True, default='0'),
    _con.IntField('is_collapsed', no_null=True, default='0')
)
