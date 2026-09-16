# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

"""Schema for ``pjt_pegboard_tables``.

One row per anchor that has a floating Excel-like data table overlaid on the
peg-board view. ``point_pegboard_id`` is this table's CENTER position --
auto-placed once at row-creation time (nearest spot to the owning anchor
that doesn't overlap any other object's OBB/AABB -- see
``objects.objects_pegboard.table_placement``) and freely draggable by the
user afterward like any other peg-board position.

Deliberately the SAME ``pjt_points_pegboard`` row as the owning anchor's own
``table_point_peg_id`` column (see ``mixins.table_position_peg.
TablePositionPegMixin``, mixed into every anchor type that can own one of
these overlays: ``PJTHousing``/``PJTBundle``/``PJTTransition``/
``PJTTransitionBranch``) -- NOT a fresh point of this row's own, and not
connected back to the anchor via a reverse FK on either side. Sharing that
one point is what lets ``PJTPegboardTable.anchor`` and
``PJTPegboardTablesTable.get_from_point_pegboard_id`` find one row from the
other with a plain equality lookup on ``point_pegboard_id`` /
``table_point_peg_id``, in either direction.
"""

from . import projects as _projects
from . import points_pegboard as _points_pegboard

from .. import db_connectors as _con


pjt_id_field = _con.UUIDField('id', is_primary=True)

pjt_table = _con.SQLTable(
    'pjt_pegboard_tables',
    pjt_id_field,
    _con.UUIDField('point_pegboard_id', no_null=True,
                  references=_con.SQLFieldReference(_points_pegboard.pjt_table,
                                                    _points_pegboard.pjt_id_field,
                                                    on_delete=_con.REFERENCE_NO_ACTION,
                                                    on_update=_con.REFERENCE_NO_ACTION)),

    # str((width, height)) -- one column instead of two separate width/
    # height floats, so reading the table's size back is a single query
    # (see PJTPegboardTable.size).
    _con.TextField('size', no_null=True),

    # Same VisiblePegboardMixin every other peg-board object already has
    # -- lets a table be hidden without deleting its row/losing its
    # column selection or position.
    _con.IntField('is_visible_pegboard', no_null=True, default='1'),

    # Which columns are shown, and in what order -- a string-encoded
    # list of ints indexing into pegboard_table.column_defs.COLUMN_DEFS
    # (same list-in-a-TextField convention as wires.accessory_part_nums:
    # '[0, 1, 4, 2]', read/written by PJTPegboardTable.visible_columns).
    _con.TextField('visible_columns', default='""', no_null=True),
)
