# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

from . import projects as _projects
from . import points3d as _points3d
from . import points2d as _points2d
from . import points_pegboard as _points_pegboard
from . import colors as _colors

from harness_designer.database import db_connectors as _con


pjt_id_field = _con.UUIDField('id', is_primary=True)

pjt_table = _con.SQLTable(
    'pjt_notes',
    pjt_id_field,
    _con.UUIDField('point2d_id', default='NULL',
                   references=_con.SQLFieldReference(_points2d.pjt_table,
                                                     _points2d.pjt_id_field,
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
    _con.UUIDField('color_id', default="X'00000000000000000000000000000000'", no_null=True,
                   references=_con.SQLFieldReference(_colors.table,
                                                     _colors.id_field,
                                                     on_update=_con.REFERENCE_NO_ACTION)),
    _con.UUIDField('scale3d_id', default='NULL',
                   references=_con.SQLFieldReference(_points3d.pjt_table,
                                                     _points3d.pjt_id_field,
                                                     on_delete=_con.REFERENCE_NO_ACTION,
                                                     on_update=_con.REFERENCE_NO_ACTION)),
    _con.UUIDField('scale2d_id', default='NULL',
                   references=_con.SQLFieldReference(_points2d.pjt_table,
                                                     _points2d.pjt_id_field,
                                                     on_delete=_con.REFERENCE_NO_ACTION,
                                                     on_update=_con.REFERENCE_NO_ACTION)),
    _con.UUIDField('scale_pegboard_id', default='NULL',
                   references=_con.SQLFieldReference(_points_pegboard.pjt_table,
                                                     _points_pegboard.pjt_id_field,
                                                     on_delete=_con.REFERENCE_NO_ACTION,
                                                     on_update=_con.REFERENCE_NO_ACTION)),

    _con.TextField('notes', default='""', no_null=True),

    # Single, shared size/alignment/style -- a note has exactly one of
    # these regardless of which view renders it. Exactly one of
    # point2d_id/point3d_id/point_pegboard_id is set -- a note belongs
    # to exactly one view, never more than one -- and that's what
    # determines which view actually renders it (see
    # PJTNotesTable.insert()), not a separate per-view copy of this
    # data.
    _con.IntField('size', default='1', no_null=True),
    _con.IntField('h_align', default='1', no_null=True),
    _con.IntField('style', default='1', no_null=True),

    # Visibility, unlike size/h_align/style above, IS kept one column
    # per view (matching every other object type's own Visible2DMixin/
    # Visible3DMixin/VisiblePegboardMixin) rather than collapsed to a
    # single shared column -- a shared column meant a note's own
    # is_visible-setter write (from whichever TWO views it does NOT
    # belong to, each constructing an inert not-visible placeholder --
    # see e.g. objects_pegboard/note.py's own __init__) clobbered the
    # ONE view it actually does belong to's real visibility, since they
    # all aliased the same underlying value.
    _con.IntField('is_visible2d', default='1', no_null=True),
    _con.IntField('is_visible3d', default='1', no_null=True),
    _con.IntField('is_visible_pegboard', default='1', no_null=True),

    _con.TextField('quat2d', default='"[1.0, 0.0, 0.0, 0.0]"', no_null=True),
    _con.TextField('angle2d', default='"[0.0, 0.0, 0.0]"', no_null=True),

    _con.TextField('quat3d', default='"[1.0, 0.0, 0.0, 0.0]"', no_null=True),
    _con.TextField('angle3d', default='"[0.0, 0.0, 0.0]"', no_null=True),

    # Default unlocked (0) -- an unlocked note continuously re-faces the
    # 3D camera instead of holding a fixed angle3d (see objects.objects_3d
    # .note's own camera-follow batch update); locking (the Angle3D
    # property panel checkbox, or bringing up the note's own rotation
    # rings) freezes whatever angle3d/quat3d it's currently showing and
    # flips this to 1, same as any ordinary rotatable object from then on.
    _con.IntField('angle3d_lock', default='0', no_null=True),

    _con.TextField('quat_pegboard', default='"[1.0, 0.0, 0.0, 0.0]"', no_null=True),
    _con.TextField('angle_pegboard', default='"[0.0, 0.0, 0.0]"', no_null=True),

    _con.IntField('smooth', default='NULL')
)
