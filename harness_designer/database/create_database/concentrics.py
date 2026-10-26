# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

from . import projects as _projects
from . import bundle_covers as _bundle_covers
from . import transition_branches as _transition_branches
from .. import db_connectors as _con


pjt_id_field = _con.UUIDField('id', is_primary=True)

pjt_table = _con.SQLTable(
    'pjt_concentrics',
    pjt_id_field,
    # Nullable (2026-10-25). A concentric is attached to a bundle, to a
    # transition branch, or -- when a bundle and a transition branch are
    # connected -- to BOTH, in which case they share this one row (and so the
    # one pjt_pegboard_sections widget). A branch-only concentric has NO
    # bundle: handlers.transition_handler._create_branch_concentric inserts
    # (bundle_id=None, transition_branch_id=<branch>), which this NOT NULL
    # column rejected -- the 2026-09-29 fix below relaxed only
    # transition_branch_id, the other half of the pair, so the branch path
    # could never have inserted a row. Both columns are nullable now; that at
    # least one is set is not enforced in SQL (SQLTable has no CHECK support).
    _con.UUIDField('bundle_id', default="NULL",
                   references=_con.SQLFieldReference(_bundle_covers.pjt_table,
                                                     _bundle_covers.pjt_id_field,
                                                     on_delete=_con.REFERENCE_NO_ACTION,
                                                     on_update=_con.REFERENCE_NO_ACTION)),

    # Nullable -- PJTConcentricsTable.insert()'s own signature already
    # types both this and bundle_id as `bytes | None` (a concentric row
    # belonged to exactly one of a bundle or a transition branch -- since
    # 2026-10-25 a connected pair share one row, see bundle_id above -- but
    # this column was left NOT NULL with no default, which no
    # bundle-only insert (bundle_id set, this None) could ever satisfy --
    # never caught before because nothing had actually exercised this
    # insert path (see BUNDLE_PLACEMENT.md's "none of the bundle code has
    # ever been tested"). Fixed 2026-09-29, hit for real the moment
    # skeleton bundle placement (BUNDLE_PLACEMENT.md section 3) started
    # actually running.
    _con.UUIDField('transition_branch_id', default="NULL",
                   references=_con.SQLFieldReference(_transition_branches.pjt_table,
                                                     _transition_branches.pjt_id_field,
                                                     on_delete=_con.REFERENCE_NO_ACTION,
                                                     on_update=_con.REFERENCE_NO_ACTION)),
    _con.TextField('notes', default='""', no_null=True)
)
