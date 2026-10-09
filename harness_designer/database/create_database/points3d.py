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
    # A point is pure geometry: it carries no owner and no order. A wire's or
    # bundle's own ordered waypoint list is stored in pjt_wire_paths/
    # pjt_bundle_paths, whose rows reference these rows (any number of
    # wires can share one point).
    # Set only on a cloned point (see objects.terminal.Terminal.
    # _own_or_cloned_point_id) -- the id of the "real"/canonical point this
    # one was cloned from (a terminal's own wire_point3d/attach_point3d, or
    # a cavity's own wire_position3d), so a housing move/rotate can find
    # every clone and move it right along with its parent instead of
    # leaving it behind. No SQLFieldReference -- this table can't reference
    # its own not-yet-fully-defined pjt_table from within its own definition.
    # Present on every pjt_point* table (points2d/points_pegboard included) even
    # though only points3d needs it today, so all three stay structurally
    # identical for whatever future use needs it on the others.
    _con.UUIDField('parent_point_id', default='NULL')
)
