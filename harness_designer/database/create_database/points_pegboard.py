# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

"""Schema for ``pjt_points_pegboard``.

One row per peg-board point -- either an anchor's own position (housing/
cavity/terminal/transition/transition-branch, referenced FROM the owning
row's own ``position_pegboard_id`` FK, mirroring ``pjt_points3d``/
``pjt_points2d`` exactly), a wire/bundle waypoint (self-identifying via
``wire_id``/``bundle_id`` + ``idx`` instead of being referenced from
elsewhere), or a wire/bundle's own start/stop point (referenced FROM the
owning row's own ``start_point_pegboard_id``/``stop_point_pegboard_id``
FK). Structurally identical to ``pjt_points3d`` -- real ``x``/``y``/``z``,
same waypoint/clone columns -- since every peg-board point is a genuine
world position, not a flattened 2D one; Y is honored and stored like any
other axis (see ``database.project_db.mixins.position_pegboard``/
``objects.objects_pegboard`` for where Y actually gets constrained per
object type -- that happens at the object layer, not here).
"""

from . import projects as _projects

from .. import db_connectors as _con


pjt_id_field = _con.UUIDField('id', is_primary=True)

pjt_table = _con.SQLTable(
    'pjt_points_pegboard',
    pjt_id_field,
    _con.FloatField('x', no_null=True),
    _con.FloatField('y', no_null=True),
    _con.FloatField('z', no_null=True),
    # Wire/bundle-waypoint-only columns -- NULL for every other peg-board
    # point row (an anchor referenced FROM its owning row's own
    # position_pegboard_id/*_point_pegboard_id FK, same as always).
    # Self-identifying via wire_id/bundle_id + idx instead of being
    # referenced from elsewhere, mirroring pjt_points3d exactly.
    #
    # No SQLFieldReference to pjt_wires/pjt_bundles here -- same reason as
    # pjt_points3d: wires.py/bundle_covers.py already import this module
    # for their own start/stop point_pegboard FK columns, so a real FK back
    # the other way would be a circular module import. Cleanup on delete is
    # explicit (see PJTWire.delete/PJTBundle.delete), same as points3d.
    _con.UUIDField('wire_id', default='NULL'),
    _con.UUIDField('bundle_id', default='NULL'),
    _con.IntField('idx', default='NULL'),
    # Set only on a cloned point (see objects.terminal.Terminal.
    # _own_or_cloned_point_id) -- the id of the "real"/canonical point this
    # one was cloned from, so a housing move/rotate can find every clone
    # and move it right along with its parent instead of leaving it behind.
    # Present on every pjt_point* table (points2d/points3d included) even
    # though only points3d needs it today, so all three stay structurally
    # identical for whatever future use needs it on the others.
    _con.UUIDField('parent_point_id', default='NULL')
)
