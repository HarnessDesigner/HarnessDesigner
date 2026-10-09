# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

from . import wires as _wires
from . import points3d as _points3d
from . import points2d as _points2d
from . import points_pegboard as _points_pegboard
from . import bundle_covers as _bundle_covers
from . import concentrics as _concentrics
from . import transitions as _transitions
from . import transition_branches as _transition_branches
from .. import db_connectors as _con


pjt_id_field = _con.UUIDField('id', is_primary=True)

# One row per point per wire per view: a wire's route, in order. Every row
# always has wire_id, idx and exactly one of point3d_id/point_pegboard_id/
# point2d_id (enforced in PJTWirePathsTable.insert); the four tag columns
# describe what the row is (see BUNDLE_DESIGN.md, section 2.6).
#
# The point rows referenced here are SHARED: a bundle waypoint, a transition
# branch position, a transition centre or a housing point is a single point
# row referenced by every wire path that goes through it, which is why idx
# lives here (per wire, per view) and not on the point row.
pjt_table = _con.SQLTable(
    'pjt_wire_paths',
    pjt_id_field,
    _con.UUIDField('wire_id', no_null=True,
                   references=_con.SQLFieldReference(_wires.pjt_table,
                                                     _wires.pjt_id_field,
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
    _con.UUIDField('point2d_id', default='NULL',
                   references=_con.SQLFieldReference(_points2d.pjt_table,
                                                     _points2d.pjt_id_field,
                                                     on_delete=_con.REFERENCE_NO_ACTION,
                                                     on_update=_con.REFERENCE_NO_ACTION)),
    _con.IntField('idx', no_null=True),
    # Set when the row lies inside this bundle's span (optional -- also set
    # on a transition branch position that a bundle is plugged into).
    _con.UUIDField('bundle_id', default='NULL',
                   references=_con.SQLFieldReference(_bundle_covers.pjt_table,
                                                     _bundle_covers.pjt_id_field,
                                                     on_delete=_con.REFERENCE_NO_ACTION,
                                                     on_update=_con.REFERENCE_NO_ACTION)),
    # Only when concentric twisting is used.
    _con.UUIDField('concentric_id', default='NULL',
                   references=_con.SQLFieldReference(_concentrics.pjt_table,
                                                     _concentrics.pjt_id_field,
                                                     on_delete=_con.REFERENCE_NO_ACTION,
                                                     on_update=_con.REFERENCE_NO_ACTION)),
    # Set on a transition branch position and on the transition centre.
    _con.UUIDField('transition_id', default='NULL',
                   references=_con.SQLFieldReference(_transitions.pjt_table,
                                                     _transitions.pjt_id_field,
                                                     on_delete=_con.REFERENCE_NO_ACTION,
                                                     on_update=_con.REFERENCE_NO_ACTION)),
    # Set on a transition branch position.
    _con.UUIDField('transition_branch_id', default='NULL',
                   references=_con.SQLFieldReference(_transition_branches.pjt_table,
                                                     _transition_branches.pjt_id_field,
                                                     on_delete=_con.REFERENCE_NO_ACTION,
                                                     on_update=_con.REFERENCE_NO_ACTION))
)
