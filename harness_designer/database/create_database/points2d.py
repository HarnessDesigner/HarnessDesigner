# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

from . import projects as _projects
from .. import db_connectors as _con


pjt_id_field = _con.UUIDField('id', is_primary=True)

pjt_table = _con.SQLTable(
    'pjt_points2d',
    pjt_id_field,
    _con.FloatField('x', no_null=True),
    _con.FloatField('y', no_null=True),
    # Added after the table already existed in users' project databases, so
    # it needs a default for the ALTER TABLE ADD COLUMN to be legal on a
    # NOT NULL column. PJTPoints2DTable._update_table_in_db moves every
    # pre-existing row's old ``y`` into this column (the schematic plane's
    # second axis used to be stored in ``y`` and mapped onto ``Point.z``)
    # and zeroes ``y``, so x/y/z now line up 1:1 with ``Point``'s own axes.
    _con.FloatField('z', default='0.0', no_null=True),
    # A point is pure geometry: it carries no owner and no order. A wire's own
    # ordered waypoint list is stored in pjt_wire_paths, whose rows reference
    # these rows.
    # See pjt_points3d's identical column -- kept structurally identical
    # across every pjt_point* table even though only points3d uses this
    # today (see database.project_db.pjt_terminal/objects.terminal.Terminal.
    # _own_or_cloned_point_id).
    _con.UUIDField('parent_point_id', default='NULL')
)
