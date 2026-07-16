# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

"""Schema for ``pjt_points_peg``.

One row per peg-board point -- either an anchor's own position (housing/
splice/transition-branch/terminal, referenced FROM the owning row's own
``position_peg_id`` FK, mirroring ``pjt_points2d``/``pjt_points3d``
exactly) or a bundle waypoint (a peg-board-only bend point with no
independent 3D placement of its own, self-identifying via
``bundle_id``/``idx`` instead of being referenced from elsewhere).
``bundle_id``/``idx`` are ``NULL`` for an anchor point; ``x``/``z`` are
always set either way -- this single nullable-column split is what makes
"is this row an anchor or a waypoint" and "give me every waypoint for
bundle X, in order" both trivial lookups against one table, instead of
maintaining ``pjt_pegboard_waypoints`` as a separate parallel table.

Every peg-board point is a genuine 3D world position with Y pinned to 0
(the board is a flat plane) -- so this table stores ``x``/``z`` (matching
``pjt_points3d``'s own axis names), not ``x``/``y``. The in-memory
``Point`` built from a row (``PJTPointPeg.point``) is a real 3-component
point (``Point(x, 0.0, z)``, ``is2d=False``), so callers read ``.x``/
``.y``/``.z`` directly with no relabeling needed anywhere the point is
handed to real-3D-space code (uniforms, ``position3d`` projections, etc).

No length-budget column: a bundle waypoint has no independent 3D
placement, so there is no independent 3D distance to persist for the edge
ending at it. Each edge's length budget (``gl.canvas_pegboard.layout_graph.
PegboardEdge.max_length_mm``) is instead computed live, at graph-build
time, as the bundle's real total length (``PJTBundle.length_mm``, itself
computed live from the real 3D start/stop points) split proportionally by
each edge's *current* 2D distance -- recomputed fresh every
``load_project()``/graph-rebuild (never mid-drag, which would make the
clamp chase its own tail), so nothing here needs to persist it either.
"""

from . import projects as _projects
from . import bundle_covers as _bundle_covers

from .. import db_connectors as _con


pjt_id_field = _con.PrimaryKeyField('id')

pjt_table = _con.SQLTable(
    'pjt_points_peg',
    pjt_id_field,
    _con.IntField('project_id', no_null=True,
                  references=_con.SQLFieldReference(_projects.pjt_table,
                                                    _projects.pjt_id_field,
                                                    on_delete=_con.REFERENCE_CASCADE,
                                                    on_update=_con.REFERENCE_CASCADE)),
    _con.FloatField('x', no_null=True),
    _con.FloatField('z', no_null=True),
    # Bundle-waypoint-only columns -- NULL for an anchor's own point row.
    _con.IntField('bundle_id', default='NULL',
                  references=_con.SQLFieldReference(_bundle_covers.pjt_table,
                                                    _bundle_covers.pjt_id_field,
                                                    on_delete=_con.REFERENCE_CASCADE,
                                                    on_update=_con.REFERENCE_CASCADE)),
    _con.IntField('idx', default='NULL')
)
