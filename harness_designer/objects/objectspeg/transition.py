# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

from typing import TYPE_CHECKING

from . import basepeg as _basepeg
from ...gl.canvas_pegboard import flatten as _flatten
from ...gl.canvas_pegboard import table_rows as _table_rows


if TYPE_CHECKING:
    from ...database.project_db import pjt_transition as _pjt_transition
    from .. import transition as _transition
    from ...geometry import point as _point


class Transition(_basepeg.BasePeg):
    """
    Peg Board Editor representation of a transition -- reuses the real 3D
    mesh/material/scale the 3D editor already holds. Transitions have no
    catalog part/``Model3D`` of their own (their mesh is procedurally
    generated at runtime, ``objects.objects3d.transition._build_model``,
    always synchronously -- no async ``model.load()`` step, unlike
    ``Housing``/``Splice``/``Terminal``), so the real ``vbo`` is available
    immediately and the flatten orientation (via
    ``flatten_quaternion_for_transition``, which uses the fact that
    ``_build_model`` confines every branch to local Z=0) is applied right
    here instead of deferred to :meth:`~.basepeg.BasePeg._set_model`.
    """
    db_obj: "_pjt_transition.PJTTransition"

    def __init__(self, parent: "_transition.Transition",
                 db_obj: "_pjt_transition.PJTTransition"):
        """Initialise the :class:`Transition` instance.

        :param parent: Parent object.
        :type parent: :class:`_transition.Transition`
        :param db_obj: Database-backed object.
        :type db_obj: :class:`_pjt_transition.PJTTransition`
        """
        obj3d = parent.obj3d

        _basepeg.BasePeg.__init__(
            self, parent, db_obj,
            vbo=obj3d._vbo,  # NOQA
            angle=db_obj.anglepeg,
            position=db_obj.position_peg,
            scale=obj3d.scale,
            material=obj3d.material,
        )
        self.smooth = getattr(obj3d, 'smooth', False)

        # Identity key for gl.canvas_pegboard's bundle-graph matching.
        self.point3d_id = db_obj.position3d_id

        if self._position.x == 0.0 and self._position.z == 0.0:
            pos3d = db_obj.position3d
            self._position.x = float(pos3d.x)
            self._position.z = float(pos3d.z)

        flatten_quat = _flatten.flatten_quaternion_for_transition(
            obj3d._vbo.local_obb)  # NOQA
        self._apply_flatten_if_untouched(flatten_quat.as_euler)

    @property
    def table_anchor_points(self) -> list:
        """One table-anchor point per populated branch (1-6) -- a
        transition gets **one data table per branch**, not one combined
        table for the whole transition, since each
        :class:`~harness_designer.database.project_db.pjt_transition_branch.PJTTransitionBranch`
        represents an independent bundle attachment point and already has
        its own independent ``position3d_id`` (``Position3DMixin``) to key
        a ``pjt_pegboard_tables`` row by -- no schema change needed.

        :returns: One entry per populated branch.
        :rtype: list[tuple[int, float, float, str]]
        """
        if not self.is_active:
            return []

        points = []
        for i in range(1, 7):
            branch = getattr(self.db_obj, f'branch{i}')
            if branch is None:
                continue

            pos = branch.position3d
            points.append((branch.position3d_id, float(pos.x), float(pos.z),
                            f'{self._table_label()} - Branch {i}'))

        return points

    def table_anchor_live_position(self, point3d_id: int) -> "_point.Point":
        """One branch's live ``position3d`` -- *point3d_id* must be one of
        this transition's own branches' ``position3d_id`` (see
        :attr:`table_anchor_points`), not the transition's own anchor
        point. Falls back to the transition's own :attr:`position` if no
        branch matches (shouldn't happen given the caller always passes
        one of this transition's own ``table_anchor_points`` ids).
        """
        for i in range(1, 7):
            branch = getattr(self.db_obj, f'branch{i}')
            if branch is not None and branch.position3d_id == point3d_id:
                return branch.position3d

        return self.position

    def build_table_rows(self, project, point3d_id: int) -> list:
        """One branch's non-filler wires -- see
        ``table_rows.build_rows_for_transition_branch``. *point3d_id* must
        be one of this transition's own branches' ``position3d_id`` (see
        :attr:`table_anchor_points`), not the transition's own anchor point.
        """
        for i in range(1, 7):
            branch = getattr(self.db_obj, f'branch{i}')
            if branch is not None and branch.position3d_id == point3d_id:
                return _table_rows.build_rows_for_transition_branch(branch)

        return []
