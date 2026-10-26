# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

"""Schema for ``pjt_pegboard_sections``.

One row per concentric-twist cross-section widget shown on the peg-board
view (``ui.concentric_section``: drawn into a buffer and uploaded as a GL
texture, the same way the floating wire tables in ``pegboard_tables`` are).
The row holds only the widget's placement -- its position and its size.

``concentric_id`` is UNIQUE: there is exactly ONE widget per concentric.
What the widget is attached to is not stored here -- it is whatever the
concentric row itself points at (``pjt_concentrics.bundle_id`` and/or
``pjt_concentrics.transition_branch_id``). A bundle and a transition branch
that are connected share ONE concentric row (both columns set), so they also
share the one widget; no second row can exist for either of them.

``point_pegboard_id`` is the widget's anchor: the X of its LEFT edge and the Z
of its vertical middle (how the quad is drawn). Unlike
``pjt_pegboard_tables`` it is NOT shared with the anchor's own
``table_point_peg_id`` -- this row owns its own ``pjt_points_pegboard`` row,
created by ``PJTPegboardSectionsTable.insert`` and removed with the row.
"""

from . import concentrics as _concentrics
from . import points_pegboard as _points_pegboard
from .. import db_connectors as _con


pjt_id_field = _con.UUIDField('id', is_primary=True)

pjt_table = _con.SQLTable(
    'pjt_pegboard_sections',
    pjt_id_field,
    _con.UUIDField('concentric_id', no_null=True, is_unique=True,
                  references=_con.SQLFieldReference(_concentrics.pjt_table,
                                                    _concentrics.pjt_id_field,
                                                    on_delete=_con.REFERENCE_NO_ACTION,
                                                    on_update=_con.REFERENCE_NO_ACTION)),
    _con.UUIDField('point_pegboard_id', no_null=True,
                  references=_con.SQLFieldReference(_points_pegboard.pjt_table,
                                                    _points_pegboard.pjt_id_field,
                                                    on_delete=_con.REFERENCE_NO_ACTION,
                                                    on_update=_con.REFERENCE_NO_ACTION)),

    # str((width, height)) in world mm -- one column instead of two floats,
    # same convention as pjt_pegboard_tables.size (see PJTPegboardSection.size).
    _con.TextField('size', no_null=True),

    # Same VisiblePegboardMixin every other peg-board object already has --
    # lets the widget be hidden (closed) without deleting its row or
    # losing its position and size.
    _con.IntField('is_visible_pegboard', no_null=True, default='1'),
)
