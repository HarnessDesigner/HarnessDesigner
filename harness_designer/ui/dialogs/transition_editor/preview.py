# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

"""The transition editor dialog's own live-preview facade.

Per the user's own steer (2026-09-27): ``ui/dialogs/part_orientation.py``
doesn't reuse a concrete class like ``objects_3d.housing.Housing`` for its
own preview because THAT dialog previews every catalog part type
generically -- its ``PartModel3D`` is a parallel, from-scratch ``Base3D``
subclass out of necessity. This dialog deals with transitions
specifically, so ``PreviewTransition3D`` below SUBCLASSES
``objects_3d.transition.Transition`` directly (not a parallel facade) --
overriding only what actually differs (its ``__init__``, to source data
from a catalog ``Transition``/``TransitionBranch`` part instead of a
placed ``PJTTransition``): ``build()``, ``_update_angle``/
``_update_position``, and every rendering/hit-testing/AABB-OBB
mechanism are all inherited UNCHANGED.

Never moves or rotates on its own (always the origin, identity angle) --
inherited ``build()``'s delta-transform bookkeeping around
``self._position``/``self._angle`` degenerates to a no-op against those,
so nothing needed overriding there either.
"""

from typing import TYPE_CHECKING

from ....objects import ObjectBase as _ObjectBase
from ....objects.objects_3d import base_3d as _base_3d
from ....objects.objects_3d import transition as _transition_3d
from ....gl import vbo as _vbo
from ....gl import materials as _materials
from ....geometry import point as _point
from ....geometry import angle as _angle
from ....gl.canvas_base import interaction as _interaction
from .... import check_types as _check_types

if TYPE_CHECKING:
    from ....database.global_db import transition as _g_transition
    from . import dialog as _dialog


class PreviewTransition(_ObjectBase):
    """Non-selectable wrapper for the transition preview, matching
    ``part_orientation.py``'s ``PartModel``'s own role exactly."""
    obj3d: "PreviewTransition3D" = None

    @_check_types.do
    def __init__(self, dialog: "_dialog.TransitionEditorDialog", part: "_g_transition.Transition") -> None:
        super().__init__(dialog, None)
        self.dialog = dialog
        self.obj3d = PreviewTransition3D(self, part)

        dialog.add_object(self)

    @_check_types.do
    def set_selected(self, flag: bool) -> None:
        pass

    @_check_types.do
    def delete(self) -> None:
        pass

    @_check_types.do
    def close(self) -> None:
        pass


class PreviewTransition3D(_transition_3d.Transition):
    """See module docstring. Built directly from a catalog
    ``Transition``/its ``TransitionBranch`` rows -- never a
    ``PJTTransition``.
    """

    @_check_types.do
    def __init__(self, parent: PreviewTransition, part: "_g_transition.Transition") -> None:
        self._part = part
        self.branch_count = part.branch_count

        angle = _angle.Angle()
        position = _point.Point(0.0, 0.0, 0.0)
        material = _materials.Rubber(part.color.ui)

        # No PJTTransitionBranch rows at all -- Branch's own db_obj=None
        # allowance (see its __init__'s docstring) is exactly what lets
        # this preview exist with no placed transition; each branch's
        # diameter is seeded at the catalog's own min_dia (Branch.
        # __init__'s own fallback for a None db_obj), the same default a
        # brand-new real placement's branches start at (see Transition.
        # start_add).
        branch_db_objs = [None] * part.branch_count

        # Highlight overrides -- see Transition.__init__'s own comment;
        # this bypasses that method entirely (see the Base3D.__init__
        # call below), so it must be set up here too.
        self._branch_materials: dict[int, _materials.GLMaterial] = {}

        with parent.dialog.context:
            self._body = _transition_3d._Body(part, branch_db_objs)  # NOQA -- same module family, private by convention only
            self._body.apply_transform(position, angle)

        scale = _point.Point(1.0, 1.0, 1.0)

        # Deliberately calls Base3D.__init__ directly, NOT super().__init__
        # (which would resolve to Transition.__init__, the PJTTransition-
        # specific one this class exists to bypass) -- this reaches exactly
        # the same point in construction Transition.__init__ itself does,
        # just fed from a catalog part instead of a PJTTransition.
        _base_3d.Base3D.__init__(self, parent, part, self._body, angle, position, scale, material)
        self._is_visible = True

    @_check_types.do
    def set_selected(self, flag: bool) -> None:
        pass

    @_check_types.do
    def delete(self) -> None:
        pass

    @_check_types.do
    def handle_interaction(
        self, last_pos: _point.Point, current_pos: _point.Point, had_motion: bool,
        interaction_type: "_interaction.MouseInteraction", clicked_object: object | None
    ) -> bool:
        """Never draggable/rotatable by a click in the dialog's own canvas
        -- unlike a real placed Transition, this preview always sits at
        the origin; the dialog's own camera controls are how a user looks
        at it from a different angle. (Branch-level drag interaction --
        TRANSITION_EDITOR_DIALOG.md stage 6 -- is a separate, later
        concern from this whole-object drag Base3D would otherwise offer.)
        """
        return False

    @_check_types.do
    def rebuild(self, part: "_g_transition.Transition") -> None:
        """Rebuild from *part*'s current branch data -- called by the
        dialog whenever a branch field changes, whenever ``branch_count``
        changes, or whenever a different transition is loaded (in which
        case *part* is the new one).

        A thin wrapper around the inherited ``build()``: when the branch
        COUNT changed, ``self._body.branches`` is the wrong length and
        must be rebuilt from scratch first (``build()`` itself only ever
        repositions/re-diameters the branches it's already holding,
        matching what a real placed Transition needs -- its own
        ``branch_count`` can't change after placement -- but this
        dialog's very purpose is editing ``branch_count``, so this
        preview has to tolerate it changing under it). ``build()`` right
        after this redoes the same rebuild once more (harmless, cheap,
        simpler than duplicating its own extraction logic here) --
        exactly the shape ``build()`` already expects: a plain list of
        each branch's own ``db_obj`` (``None`` for every branch here).

        Also evicts *part*'s own shared body VBO (see ``objects_3d.
        transition._Body._build_body_model``) from the pool before
        rebuilding -- unlike a real placed ``PJTTransition``, THIS dialog
        is the one place a catalog part's own bulb geometry (offset/
        angle/bulb_length/bulb_offset/max_dia) can actually change under
        an unchanged ``part_number``, and ``_build_body_model`` would
        otherwise keep reusing the pre-edit mesh it already cached under
        that same id. Harmless if nothing was cached yet.
        """
        self._part = part
        _vbo.PooledVBOHandler.evict(part.part_number + ':transition')

        if len(self._body.branches) != part.branch_count:
            self._body.rebuild(part, [None] * part.branch_count)
            self.branch_count = part.branch_count

        self.build()
