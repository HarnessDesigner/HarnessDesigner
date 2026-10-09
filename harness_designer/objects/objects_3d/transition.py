# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

from typing import TYPE_CHECKING, Union as _Union

import numpy as np
import build123d
import math
from PySide6 import QtCore, QtWidgets, QtGui

from ...ui.widgets import context_menus as _context_menus
from ...geometry import point as _point
from ...geometry import angle as _angle
from . import base_3d as _base_3d
from . import menu_ops as _menu_ops
from ...shapes import cylinder as _cylinder
from ...shapes import sphere as _sphere
from ... import utils as _utils
from ...gl import vbo as _vbo
from ...gl import materials as _materials
from ...gl.canvas_base import interaction as _interaction
from ... import config as _config
from ... import color as _color
from ... import logger as _logger
from ... import check_types as _check_types
from ...database.project_db import pjt_transition as _pjt_transition


if TYPE_CHECKING:
    from ...ui.editor_3d import editor_3d as _editor_3d
    from .. import ObjectBase as _ObjectBase
    from ...database.global_db import transition as _g_transition
    from ...database.global_db import transition_branch as _g_transition_branch
    from ...database.project_db import pjt_transition as _pjt_transition
    from .. import transition as _transition
    from ...database.project_db import pjt_transition_branch as _pjt_transition_branch
    from ... import ui as _ui
    from ...gl.shaders import program as _shader_program


Config = _config.Config.editor_3d


# TODO:
#       setting the angles
#       setting position
#       routing wire through transition
#       snap wire to branch


# The OCC/build123d boolean-CSG model builder that used to live here
# (`_build_model`) was replaced by the `Branch`/`_Body` classes below --
# a transition's body is simply the sum of its branches' own tube, bulb
# cylinder and bulb cap sphere(s), there is no separate "transition
# body" geometry at all. Each branch's WORLD position/angle is computed
# once by `_Body.apply_transform()` whenever this object's own
# position/angle actually changes (construction, `build()`,
# `_update_position`/`_update_angle`), not recomputed on every single
# `render()` call -- see `Branch.apply_transform`'s own docstring for
# why this is both simpler and safe (never composes two `Angle` objects,
# which would be wrong -- see that method). Kept directly in this file
# (not a separate shared module) per the user's own simplification
# request (2026-09-27); `objects_pegboard/transition.py` has its own
# equivalent, not this same class, since the peg-board view needs its
# own always-flat orientation handling.
#
# `Branch` (2026-09-28, renamed from `_BranchBody`) is BOTH this
# geometry cache AND a branch's real identity (catalog/placed-DB data,
# diameter fit-checking, hit-testing) -- not a `Base3D` subclass, and
# never registered with the canvas as its own pickable object, per the
# user's own steer: `Transition` below owns all real per-branch
# interaction directly (`hit_test_branch`/`highlight_branch`/
# `branch_fits`) rather than each branch being independently picked.
# An EARLIER design had a separate small pickable tip-marker sphere,
# confusingly ALSO called `Branch`, a real `Base3D` object registered
# with the canvas -- retired entirely, see this module's own git
# history for what it used to do.
#
# build123d is back (2026-09-28), but scoped much more narrowly than
# `_build_model` ever was: `_Body._build_body_model` unions ONLY the
# bulb pieces (never the trunk cylinders) into one shared mesh, cached
# by catalog part number (never rebuilt per placed instance),
# specifically to fix the overlapping-primitives-look-bad-when-selected
# problem the all-primitive design above has around every hub -- see
# TRANSITION_DESIGN.md's own decision log. Falls back to this file's
# original all-primitive rendering (unchanged) whenever a part's own
# bulbs don't actually fuse into one solid.
#
# The separate `_Hub` sphere (one per shared branch-root point, papering
# over the gap a bare flat-capped cylinder left there when nothing else
# rounded it off) was removed entirely 2026-09-28, per the user: no
# longer needed now that branches' own bulb pieces are unioned together
# with build123d instead of just overlapping as untrimmed primitives.
# If a part's own bulbs leave a visible gap at the hub now, that's a
# `_build_body_model`-level concern (e.g. widening the bulb cylinders,
# or adding a sphere into the union itself), not a reason to bring
# `_Hub` back.


_ZERO_ANGLE = _angle.Angle.from_euler(0.0, 0.0, 0.0)

# Part numbers whose bulb pieces have already been tried and failed to
# fuse into one single valid build123d solid this session (see _Body.
# _build_body_model) -- skipped on every later attempt (by any other
# placed instance of the same catalog part) rather than re-running the
# same expensive, doomed build123d/OCC pass again. Never cleared; a
# part's bulb geometry is catalog-fixed and can't start succeeding
# without an app restart after the catalog data itself changes.
_FAILED_BODY_IDS: set[str] = set()


@_check_types.do
def _branch_direction(angle: "_angle.Angle") -> np.ndarray:
    """A branch's own trunk direction, in local space: local +X rotated by
    the branch's own 3-axis euler angle -- the 3-axis generalization of
    the pre-migration convention (trunk direction was
    ``(cos(angle), sin(angle), 0)`` for a single Z-axis angle). See
    TRANSITION_DESIGN.md section 3/4.
    """
    direction = np.array([1.0, 0.0, 0.0], dtype=np.float32) @ angle
    direction = np.asarray(direction, dtype=np.float32)
    norm = float(np.linalg.norm(direction))
    if norm > 1e-9:
        direction /= norm

    return direction


class Branch:
    """One branch's own body geometry AND its real identity -- trunk
    cylinder, plus (if it has a bulb) a bulb cylinder and one or two cap
    spheres, plus everything needed to interact with THIS branch
    specifically (diameter fit-checking, sphere hit-testing, persisting
    its own tip position) -- the sole "branch" object in this module.

    Not a ``Base3D`` subclass, and never registered with the canvas as
    its own pickable/renderable object (2026-09-28, replacing an earlier
    design that had a separate small pickable tip-marker sphere,
    confusingly ALSO called ``Branch`` -- see this module's own git
    history) -- per the user's own steer: the amount of real interaction
    a single branch ever needs (lighting up while dragging a wire/bundle
    end near it, if it fits) is small enough that ``Transition`` below
    should own all of it directly (see its own ``hit_test_branch``/
    ``highlight_branch``/``branch_fits``), rather than each branch being
    its own independently-picked scene object. Ported directly from the
    retired OCC ``_build_model`` (see this module's own git history) --
    every branch of a transition contributes exactly this geometry;
    there is no separate "transition body" shape.
    """

    @_check_types.do
    def __init__(self, catalog_branch: "_g_transition_branch.TransitionBranch",
                 db_obj: _Union["_pjt_transition_branch.PJTTransitionBranch", None] = None) -> None:
        """Store this branch's own identity, PERMANENT catalog-defined
        shape data, AND its own render-ready cache, computed immediately
        -- all of it comes from this branch's own catalog row alone
        (offset/direction/bulb geometry never change without a brand new
        ``Branch`` being built), never from the owning TRANSITION's own
        position/angle (the ``pjt_transitions`` row), so there's no
        reason to defer any of it, exactly like the reference sketch this
        class is based on.

        *db_obj* is this branch's own PLACED row (``PJTTransitionBranch``)
        -- ``None`` only for the transition editor dialog's own live
        preview (``ui/dialogs/transition_editor/preview.py``), which
        previews a catalog part directly, never a placed transition. Its
        own ``diameter`` seeds this branch's starting diameter (falling
        back to the catalog's own ``min_dia`` the first time, same as a
        fresh placement always starts at); :meth:`set_diameter` and
        :meth:`write_tip_to_db` write back through it directly -- there
        is no separate tip-marker object standing between this one and
        the database any more.

        The one thing that genuinely can't be known yet here is the
        owning TRANSITION's own world position/angle -- that's seeded to
        identity (world origin, no rotation) so the computation below
        runs once immediately and leaves every attribute holding this
        branch's real LOCAL placement, and :meth:`update_position`/
        :meth:`update_angle` (called by the owning ``_Body`` once right
        after construction with the transition's REAL stored
        position3d/angle3d, and again any time it actually changes)
        re-run that exact same computation to rotate/translate these
        values into world space. ``render()`` reads only this cache -- it
        does no computation of its own at all.
        """
        self.idx = catalog_branch.idx
        self.catalog_branch = catalog_branch
        self.db_obj = db_obj

        self.length = catalog_branch.length
        self.bulb_length = catalog_branch.bulb_length
        self.max_dia = catalog_branch.max_dia

        self._local_offset = catalog_branch.offset.copy()
        self._local_direction = _branch_direction(catalog_branch.angle)

        bulb_offset = catalog_branch.bulb_offset
        # `is not None` is the right (and only) check -- NULL is the
        # catalog's own sentinel for "no bulb offset of its own"
        # (TRANSITION_DESIGN.md section 3: "stays nullable -- NULL means
        # this branch has no bulb offset, a real, meaningful state").
        # A stored `[0.0, 0.0, 0.0]` is NOT the same thing as NULL -- it
        # is real data saying this branch DOES have its own bulb offset,
        # which happens to sit at zero (e.g. `302A024-25/225-0` branch
        # idx 2). Collapsing that into "no bulb offset" was wrong.
        self._has_own_bulb_offset = bool(self.bulb_length and bulb_offset is not None)

        if self._has_own_bulb_offset:
            self._local_bulb_offset = bulb_offset.copy()
        else:
            self._local_bulb_offset = None

        # This branch's own LOCAL tip point (offset + length * direction)
        # -- a fixed fact about this branch's shape, same as the
        # attributes above. write_tip_to_db() persists the WORLD version
        # of this (tip_point below, only meaningful once a real transform
        # has been applied) into db_obj.position3d.
        self.local_tip = _point.Point(*(
            self._local_offset.as_numpy + self._local_direction * self.length).tolist())

        # Whether the owning _Body's shared, part-number-cached "body" VBO
        # already covers this branch's own bulb pieces -- set by
        # use_body_model(), read by _refresh_world() (trims this branch's
        # own trunk cylinder back to the bulb's own end point instead of
        # drawing the full untrimmed length) and by render() (skips this
        # branch's own bulb cylinder/sphere(s) entirely, since the body
        # VBO already draws them once for every placed instance of this
        # catalog part). False -- draw everything the old way -- until a
        # successful _Body._build_body_model() says otherwise.
        self._use_body_model = False

        # Diameter-dependent scales have no local/world distinction at all
        # (a tube's own thickness doesn't care where the transition sits).
        self.diameter: float | None = None
        self.branch_scale: _point.Point | None = None
        self.bulb_scale: _point.Point | None = None
        self.bulb_sphere_scale: _point.Point | None = None

        # Render-ready position/orientation cache -- see docstring above:
        # computed immediately below (via update_diameter()'s own call to
        # _refresh_world()) against an identity TRANSITION transform, then
        # kept current by update_position()/update_angle()/use_body_model().
        self._position: "_point.Point" = _point.Point(0.0, 0.0, 0.0)
        self._angle: "_angle.Angle" = _angle.Angle.from_euler(0.0, 0.0, 0.0)
        self.branch_start: _point.Point | None = None
        self.branch_angle: _angle.Angle | None = None
        self.tip_point: _point.Point | None = None
        self.bulb_start: _point.Point | None = None
        self.bulb_angle: _angle.Angle | None = None
        self.bulb_end: _point.Point | None = None
        self.bulb_start_sphere: _point.Point | None = None

        if db_obj is not None and db_obj.diameter is not None:
            seed_diameter = db_obj.diameter
        else:
            seed_diameter = catalog_branch.min_dia

        # update_diameter() computes branch_scale/bulb_scale/bulb_sphere_
        # scale AND calls _refresh_world() itself (see that method) --
        # called here with whatever diameter is already stored (or the
        # catalog's own min_dia the first time, the same starting default
        # a fresh placement always starts at) -- a SEED, not a change, so
        # it must not go through set_diameter()'s own DB write below.
        self.update_diameter(seed_diameter)

    @property
    @_check_types.do
    def min_diameter(self) -> float:
        """This branch's own catalog-defined minimum diameter."""
        return self.catalog_branch.min_dia

    @property
    @_check_types.do
    def max_diameter(self) -> float:
        """This branch's own catalog-defined maximum diameter."""
        return self.catalog_branch.max_dia

    @_check_types.do
    def set_diameter(self, diameter: float) -> None:
        """Change this branch's own tube diameter -- persists to
        ``db_obj.diameter`` (a no-op for a preview branch with no
        ``db_obj``) and recomputes every diameter-dependent render
        attribute via :meth:`update_diameter`. Distinct from that method
        itself, which is also called once at construction time to SEED
        the cache from whatever diameter is already stored -- that
        seeding must never write back to the database, since it isn't a
        change, just reading what's already there.
        """
        if self.db_obj is not None:
            self.db_obj.diameter = diameter

        self.update_diameter(diameter)

    @_check_types.do
    def update_diameter(self, diameter: float) -> None:
        """(Re)compute this branch's own diameter-dependent cached scales
        -- call once right after construction, and again any time this
        branch's own tube diameter changes (e.g. once the number of wires
        actually routed through it is known). Position/orientation are
        untouched, but branch_scale (which depends on the current
        diameter) is one of the things _refresh_world() recomputes, so
        this calls it too -- see that method.
        """
        self.diameter = diameter

        if self.bulb_length:
            self.bulb_scale = _point.Point(self.max_dia, self.max_dia, self.bulb_length)
            self.bulb_sphere_scale = _point.Point(self.max_dia, self.max_dia, self.max_dia)
        else:
            self.bulb_scale = None
            self.bulb_sphere_scale = None

        self._refresh_world()

    @_check_types.do
    def use_body_model(self, value: bool) -> None:
        """Tell this branch whether the owning _Body's shared, part-
        number-cached build123d "body" VBO already covers its own bulb
        pieces -- called by _Body._build_body_model() once right after a
        successful (or failed/skipped) build, same as update_diameter()/
        update_position()/update_angle() re-run _refresh_world() so every
        cached render attribute reflects it immediately. Meaningless (and
        never set True) for a branch with no bulb of its own -- there's
        nothing for the body VBO to have covered.
        """
        if value == self._use_body_model:
            return

        self._use_body_model = value
        self._refresh_world()

    @_check_types.do
    def update_position(self, position: "_point.Point") -> None:
        """Re-run this branch's own LOCAL-to-WORLD placement computation
        for a new owning-TRANSITION *position* (its ``pjt_transitions``
        row's own ``position3d``, never this branch's own local shape) --
        call once right after construction (alongside :meth:`update_angle`)
        to move this branch from local to its real placed position, and
        again any time the transition itself actually moves.
        """
        self._position = position
        self._refresh_world()

    @_check_types.do
    def update_angle(self, angle: "_angle.Angle") -> None:
        """Same as :meth:`update_position`, for the owning TRANSITION's own
        ``angle3d``."""
        self._angle = angle
        self._refresh_world()

    def _refresh_world(self) -> None:
        """Recompute every position/orientation render attribute fresh
        from this branch's own permanent LOCAL data plus the current
        ``self._position``/``self._angle`` -- the owning TRANSITION's own
        stored position/angle, identity until :meth:`update_position`/
        :meth:`update_angle` are first called with its real values (see
        ``__init__``, which calls this once against that identity seed so
        every attribute below starts out holding this branch's real LOCAL
        placement).

        Always rebuilt fresh from local data, never incrementally
        composed: a piece's own orientation is obtained by rotating its
        LOCAL DIRECTION VECTOR by the current angle and rebuilding a fresh
        ``Angle`` via ``Angle.from_direction()`` -- never by adding/
        composing two ``Angle`` objects (``Angle.__add__`` only does
        naive per-axis euler addition, not a real rotation composition,
        and would be wrong here -- see ``geometry/angle/angle.py``). This
        is the same pattern ``objects_3d/base_3d.py``'s debug OBB-edge
        overlay already uses, and was verified empirically against the
        real ``Angle`` class earlier in this same session.
        """
        position = self._position
        angle = self._angle

        world_start = self._local_offset.copy()
        world_start @= angle
        world_start += position

        world_direction = self._local_direction @ angle
        world_direction = np.asarray(world_direction, dtype=np.float32)
        norm = float(np.linalg.norm(world_direction))
        if norm > 1e-9:
            world_direction /= norm

        self.branch_start = world_start
        self.branch_angle = _angle.Angle.from_direction(world_direction)
        self.branch_scale = _point.Point(self.diameter, self.diameter, self.length)

        # Real world tip, independent of any trimming below -- hit_test_
        # outer() reads this directly rather than re-deriving a tip point
        # from branch_start/self.length, which would be wrong once
        # branch_start itself has been trimmed back to the bulb's own end.
        self.tip_point = _point.Point(*(
            world_start.as_numpy + world_direction * self.length).tolist())

        if not self.bulb_length:
            self.bulb_start = None
            self.bulb_angle = None
            self.bulb_end = None
            self.bulb_start_sphere = None
            return

        # Same rotated direction as the trunk -- _build_model's own
        # bulb-offset-is-set case rotates its bulb cylinder by the
        # branch's own angle too (`Plane(z_dir=(1,0,0)).rotated(
        # (0, 0, angle))`, a real rotation -- see the fix note this
        # session's own history has on this exact point), not a fixed
        # world axis.
        self.bulb_angle = self.branch_angle

        # Both branches below must match build_bulb_solid()'s own sphere
        # placement EXACTLY (round(bulb_length * cos/sin(this branch's
        # own angle.z), 6), added to bulb_offset/offset) -- this is what
        # determines bulb_end, which is what the trunk cylinder gets
        # trimmed back to start at (see _use_body_model below). The old
        # `(x - bulb_length, y, z)` local-X-shift only ever matched
        # build_bulb_solid's own placement for a branch whose angle.z is
        # exactly +-180 (the trunk) -- for any other angle (e.g. -90) it
        # computed a completely different point, leaving the trimmed
        # branch cylinder starting somewhere that doesn't match where the
        # actual rendered bulb ends.
        r = math.radians(self.catalog_branch.angle.z)
        cap_shift = _point.Point(
            round(self.bulb_length * math.cos(r), 6),
            round(self.bulb_length * math.sin(r), 6), 0.0)

        if self._has_own_bulb_offset:
            world_bulb_start = self._local_bulb_offset.copy()
            world_bulb_start @= angle
            world_bulb_start += position

            world_other = cap_shift + self._local_bulb_offset
            world_other @= angle
            world_other += position

            self.bulb_start = world_bulb_start
            self.bulb_end = world_other
            self.bulb_start_sphere = world_bulb_start.copy()
        else:
            world_cap = cap_shift + self._local_offset
            world_cap @= angle
            world_cap += position

            self.bulb_start = world_start.copy()
            self.bulb_end = world_cap
            self.bulb_start_sphere = None

        if self._use_body_model:
            # The shared body VBO already draws this branch's own bulb
            # pieces (once, for every placed instance of this catalog
            # part) -- render() below must not draw them again, and the
            # trunk cylinder itself is trimmed back to start where the
            # bulb already ends, rather than overlapping it for the
            # bulb's own length. bulb_end is exactly on the branch's own
            # axis line in both cases above, so the remaining length is
            # just this branch's own full length minus how far along
            # that axis bulb_end already reaches.
            trimmed_length = self.length - float(
                np.dot(self.bulb_end.as_numpy - world_start.as_numpy, world_direction))
            trimmed_length = max(trimmed_length, 0.0)

            self.branch_start = self.bulb_end.copy()
            self.branch_scale = _point.Point(self.diameter, self.diameter, trimmed_length)

    @_check_types.do
    def render(self, program: "_shader_program.FacesProgram", smooth: bool | None) -> None:
        """Pure cache read -- draws whatever :meth:`update_diameter`/
        :meth:`update_position`/:meth:`update_angle`/:meth:`use_body_model`
        last computed. No transform or scale math happens here at all."""
        cyl = _cylinder.create_vbo()
        cyl.render(program, self.branch_start, self.branch_angle, self.branch_scale, smooth)

        if self._use_body_model:
            # Already drawn once by the owning _Body's shared body VBO --
            # see use_body_model()'s own docstring.
            return

        if self.bulb_scale is not None:
            cyl.render(program, self.bulb_start, self.bulb_angle, self.bulb_scale, smooth)

            sph = _sphere.create_vbo()
            sph.render(program, self.bulb_end, _ZERO_ANGLE, self.bulb_sphere_scale, smooth)

            if self.bulb_start_sphere is not None:
                sph.render(program, self.bulb_start_sphere, _ZERO_ANGLE, self.bulb_sphere_scale, smooth)

    @_check_types.do
    def write_tip_to_db(self, force: bool = False) -> None:
        """Persist this branch's own real WORLD tip point (``tip_point``,
        current as of the last :meth:`update_position`/:meth:`update_angle`
        call) into ``db_obj.position3d`` -- a no-op for a preview branch
        with no ``db_obj``. Only actually writes when that stored point
        is still at the origin (a never-yet-placed/never-yet-moved
        branch) unless *force* is set -- the same guard the old tip-
        marker-based design had in ``_Body.rebuild()``, so a branch
        already snapped to a bundle end (its own position3d row shared
        with that bundle's endpoint) doesn't get silently reset back to
        its own catalog-default tip position by an unrelated rebuild
        (e.g. a diameter edit). ``Transition`` calls this with
        ``force=True`` for every real move/rotate, since in that case
        the branch's own position genuinely must track the transition
        moving as one rigid body, snapped or not.
        """
        if self.db_obj is None or self.tip_point is None:
            return

        pos = self.db_obj.position3d
        if pos.as_float == (0.0, 0.0, 0.0) or force:
            with pos:
                pos.x = self.tip_point.x
                pos.y = self.tip_point.y
                pos.z = self.tip_point.z

    @_check_types.do
    def hit_test_sphere(self, point: "_point.Point") -> bool:
        """Whether world-space *point* falls within a sphere centered on
        this branch's own real end position (``tip_point``), radius this
        branch's own current diameter / 2 -- the whole of this branch's
        own hit-test area (user's own spec, 2026-09-28). Replaces the
        earlier distance-to-outer-segment ``hit_test_outer`` (never
        actually wired to any caller) with something simpler that
        matches exactly how a wire/bundle end approaching a branch's own
        mouth should be judged "close enough to snap." ``Transition``
        below orchestrates the actual pick across every one of its own
        branches (see its own ``hit_test_branch``); this only answers for
        ONE branch.
        """
        if self.tip_point is None:
            return False

        radius = self.diameter / 2.0
        dist_sq = float(np.sum((point.as_numpy - self.tip_point.as_numpy) ** 2))
        return dist_sq <= radius * radius

    @_check_types.do
    def build_bulb_solid(self) -> build123d.Solid | build123d.Compound | None:
        """This branch's own bulb geometry (bulb cylinder plus its one or
        two cap sphere(s)) as a build123d solid, in LOCAL (catalog) space
        -- or ``None`` if this branch has no bulb at all. Same two cases,
        same geometry as the bulb block in ``_refresh_world`` (mirrors it
        exactly, just building real build123d shapes instead of only the
        primitive scale/position values that method caches) -- used ONLY
        by the owning ``_Body`` to build the whole transition's shared,
        part-number-cached "body" mesh (see TRANSITION_DESIGN.md and
        ``_Body._build_body_model``). Never used for per-instance
        rendering -- that stays on the cheap pooled-primitive path in
        :meth:`render`.
        """
        branch = self.catalog_branch

        bulb_len = branch.bulb_length

        if not bulb_len:
            return None

        max_dia = branch.max_dia
        angle = branch.angle
        bulb_offset = branch.bulb_offset
        offset = branch.offset

        if bulb_offset is None:
            pl = build123d.Plane(
                origin=offset.as_float, z_dir=(1, 0, 0)).rotated(angle.as_euler_float)

        else:
            pl = build123d.Plane(
                origin=bulb_offset.as_float, z_dir=(1, 0, 0)).rotated(angle.as_euler_float)

        model = pl * build123d.extrude(build123d.Circle(max_dia / 2.0), bulb_len)

        if bulb_offset is not None:
            pl = build123d.Plane(origin=bulb_offset.as_float, z_dir=(1, 0, 0))

            sphere = pl * build123d.Sphere(max_dia / 2.0)

            model += sphere

            r = math.radians(angle.z)
            pos = _point.Point(round(bulb_len * math.cos(r), 6),
                               round(bulb_len * math.sin(r), 6),
                               0.0) + bulb_offset

            pl = build123d.Plane(origin=pos.as_float, z_dir=(1, 0, 0))
            sphere = pl * build123d.Sphere(max_dia / 2.0).rotate(
                build123d.Axis(origin=(0, 0, 0), direction=(1, 0, 0)), angle.z)

            model += sphere

        else:
            r = math.radians(angle.z)
            pos = _point.Point(round(bulb_len * math.cos(r), 6),
                               round(bulb_len * math.sin(r), 6),
                               0.0) + offset

            pl = build123d.Plane(origin=pos.as_float, z_dir=(1, 0, 0))

            sphere = pl * build123d.Sphere(max_dia / 2.0).rotate(
                build123d.Axis(origin=(0, 0, 0), direction=(1, 0, 0)), angle.z)

            model += sphere

        return model


class _Body:
    """A transition's whole body -- every branch's own ``Branch`` plus
    (whenever ``_build_body_model`` below succeeds) one shared, part-
    number-cached build123d mesh covering every branch's own bulb pieces
    -- standing in directly as the owning ``Transition``'s own
    ``self._vbo`` (the same "compound handler" pattern ``shapes/text.py``'s
    ``Text`` already establishes for a multi-word string: ``BaseVar``'s
    existing AABB/OBB computation and 3-stage ray-mesh hit test need no
    ``Transition``-specific override at all, since they already only ever
    talk to ``self._vbo`` generically).

    No separate hub sphere any more (removed 2026-09-28, user decision) --
    it existed only to paper over the gap a bare flat-capped cylinder
    left at the shared vertex when nothing else rounded it off; now that
    branches' own bulb pieces are unioned together with build123d, that
    gap-filling job belongs in the union itself if it's still needed
    (e.g. widening the bulb cylinders, or a sphere added into ``body`` in
    ``_build_body_model``), not a separate always-drawn piece here.
    """

    #: Never separately dirty -- whoever calls rebuild() (Transition.build())
    #: already knows geometry just changed and re-triggers
    #: _compute_aabb()/_compute_obb() itself right after. Mirrors
    #: shapes.text.Text.is_dirty's own choice, for the same reason.
    is_dirty = False

    @_check_types.do
    def __init__(self, part: "_g_transition.Transition", branch_db_objs: list) -> None:
        self.branches: list[Branch] = []
        self._mesh: tuple[np.ndarray, int] | None = None
        self.local_aabb = np.zeros((2, 3), dtype=np.float32)
        self.local_obb = np.zeros((8, 3), dtype=np.float32)

        # The whole-transition build123d "body" -- the union of every
        # branch's own bulb pieces -- pooled by this catalog part's OWN
        # part number, shared by every placed instance of it. None
        # whenever no branch has a bulb, a build for this exact part
        # number is already known (_FAILED_BODY_IDS) to not fuse into one
        # solid, or this attempt's own fuse just failed. See
        # _build_body_model.
        self._body_vbo: _vbo.PooledVBOHandler | None = None

        self.rebuild(part, branch_db_objs)

    @_check_types.do
    def rebuild(self, part: "_g_transition.Transition", branch_db_objs: list) -> None:
        """(Re)build every branch's local geometry from *part*'s current
        branch definitions -- *branch_db_objs* is a plain list (indexed by
        catalog ``idx``) of this transition's own real placed
        ``PJTTransitionBranch`` rows (``None`` for a preview transition
        with no placed rows at all -- see ``Branch.__init__``'s own
        docstring). Tip persistence is NOT done here -- see
        :meth:`write_tips_to_db`, called separately (by ``Transition``)
        once :meth:`apply_transform` has run, since it needs the WORLD
        tip point, not the local one this method alone produces.
        """
        self.branches = []
        self._mesh = None

        for catalog_branch in part.branches:
            db_obj = branch_db_objs[catalog_branch.idx]
            self.branches.append(Branch(catalog_branch, db_obj))

        self._build_body_model(part)

        # LOCAL bounds only -- independent of the current world transform,
        # so this belongs here (once per actual geometry change), not in
        # apply_transform() (called on every move/rotate, where the local
        # geometry itself hasn't changed at all).
        self._compute_local_bounds()

    @_check_types.do
    def write_tips_to_db(self, force: bool = False) -> None:
        """Persist every branch's own real WORLD tip point into its own
        ``db_obj.position3d`` -- see ``Branch.write_tip_to_db`` for the
        per-branch guard/reasoning. Call once ``apply_transform`` has run
        with the transition's REAL position/angle.
        """
        for branch in self.branches:
            branch.write_tip_to_db(force=force)

    @_check_types.do
    def _build_body_model(self, part: "_g_transition.Transition") -> None:
        """Build (or, most of the time, just look up) this catalog PART's
        shared build123d "body" -- the union of every one of its own
        branches' bulb pieces -- and tell each branch whether the result
        covers its own bulb (see ``Branch.use_body_model``).

        Pooled by *part*'s own ``part_number`` (with a literal
        ``':transition'`` suffix as the VBO id) rather than per placed
        instance: bulb geometry only ever comes from catalog-fixed
        ``max_dia``/``bulb_length``/``offset``/``bulb_offset`` data, never
        a branch's own (per-instance, wire-count-driven) ``diameter``, so
        it is bit-for-bit identical for every placed instance of this
        same catalog part -- see TRANSITION_DESIGN.md.

        Falls back to every branch drawing its own bulb primitives
        unchanged (the always-safe pre-existing path) when: no branch has
        a bulb at all (nothing to build); this exact part number already
        failed once this session (``_FAILED_BODY_IDS``, never re-tried --
        catalog geometry can't start succeeding mid-session); or building/
        fusing/meshing the bulbs raises (below) -- most commonly
        ``build_bulb_solid()`` returning a ``ShapeList`` instead of a
        real ``Shape`` for some branch, which has no ``.wrapped``
        attribute and fails as a plain ``AttributeError`` the moment
        ``convert_model_to_mesh()`` touches it.

        Deliberately does NOT check ``is_valid``/``len(solids()) == 1``
        (removed 2026-09-28, user decision) -- both rejected real parts
        that render perfectly fine. Neither means anything about whether
        the TRIANGULATED MESH looks right: OCC's own solid-validity/trim
        semantics only matter for further CAD operations, never for what
        an opaque, depth-tested render actually shows -- the same
        reasoning TRANSITION_DESIGN.md section 4 already used to justify
        no boolean ops at all for the trunk/hub.
        """
        self._body_vbo = None

        bulb_branches = [b for b in self.branches if b.bulb_length]
        if not bulb_branches:
            for branch in self.branches:
                branch.use_body_model(False)
            return

        vbo_id = part.part_number + ':transition'

        if vbo_id in _vbo.PooledVBOHandler:
            self._body_vbo = _vbo.PooledVBOHandler(vbo_id)
            for branch in self.branches:
                branch.use_body_model(bool(branch.bulb_length))
            return

        if vbo_id in _FAILED_BODY_IDS:
            for branch in self.branches:
                branch.use_body_model(False)
            return

        try:
            body = bulb_branches[0].build_bulb_solid()
            for branch in bulb_branches[1:]:
                model = branch.build_bulb_solid()
                if model is None:
                    continue

                body += model

            vertices, faces = _utils.convert_model_to_mesh(body)
            packed, count = _utils.compute_normals(vertices, faces)

            mesh_vertices = packed[:count * 3].reshape(-1, 3)
            aabb1, aabb2 = _utils.compute_aabb(mesh_vertices)
            aabb = np.array([aabb1.as_float, aabb2.as_float], dtype=np.float32)
            obb = _utils.compute_obb(aabb1, aabb2)

            self._body_vbo = _vbo.PooledVBOHandler(vbo_id, packed, count, aabb=aabb, obb=obb)
        except Exception as exc:
            # Logged, not swallowed silently -- this is the ONLY place a
            # bug in build_bulb_solid()/the fuse/the mesh conversion would
            # ever surface; without this, a real bug here looks IDENTICAL
            # to a legitimate "bulbs don't intersect" fallback (both just
            # render the old all-primitive way) and is impossible to tell
            # apart from the live app alone.
            _logger.traceback(exc, msg=f'transition body model build failed for {vbo_id}')
            _FAILED_BODY_IDS.add(vbo_id)
            for branch in self.branches:
                branch.use_body_model(False)
            return

        for branch in self.branches:
            branch.use_body_model(bool(branch.bulb_length))

    @_check_types.do
    def apply_transform(self, position: "_point.Point", angle: "_angle.Angle") -> None:
        """Recompute every branch's WORLD-space render attributes -- call
        once whenever the owning transition's own position/angle actually
        changes (construction, ``build()``, ``_update_position``/
        ``_update_angle``); never from inside ``render()`` itself.
        """
        for branch in self.branches:
            branch.update_position(position)
            branch.update_angle(angle)

    # -- gl.vbo.VBOHandlerBase-compatible interface (see class docstring) --

    @_check_types.do
    def render_angle(self, angle: "_angle.Angle") -> "_angle.Angle":
        return angle

    def acquire(self) -> None:
        """No-op -- every actual draw goes through the globally pooled
        cylinder/sphere VBOs, which manage their own acquisition lazily."""

    def release(self) -> None:
        """No-op -- releasing here would tear down VBOs every other
        transition (and everything else using cylinder/sphere) shares."""

    @property
    def ctx(self):
        ctx = QtGui.QOpenGLContext.currentContext()
        if ctx is None:
            raise RuntimeError('context has not been acquired')

        return ctx

    @_check_types.do
    def local_mesh(self) -> tuple[np.ndarray, np.ndarray]:
        """A flattened local-space ``(vertices, faces)`` mesh combining
        every branch/hub's own real-size geometry -- used ONLY for
        ``vertices``/``local_aabb``/``local_obb`` below (AABB/OBB/
        hit-testing), never for the actual per-frame visual draw (that's
        ``render()``, one call per real piece through the pooled VBOs).
        """
        all_vertices = []
        all_faces = []
        offset = 0

        def _add(verts: np.ndarray, faces: np.ndarray) -> None:
            nonlocal offset
            all_vertices.append(verts.astype(np.float32))
            all_faces.append(faces + offset)
            offset += len(verts)

        for branch in self.branches:
            verts, faces = _cylinder.create(branch.diameter / 2.0, branch.length)
            local_angle = _angle.Angle.from_direction(branch._local_direction)  # NOQA
            verts = verts @ local_angle + branch._local_offset.as_numpy  # NOQA
            _add(verts, faces)

            if branch.bulb_scale is not None:
                if branch._has_own_bulb_offset:  # NOQA
                    bulb_local_pos = branch._local_bulb_offset  # NOQA
                    bulb_local_dir = branch._local_direction  # NOQA
                    other_local = _point.Point(
                        bulb_local_pos.x - branch.bulb_length, bulb_local_pos.y, bulb_local_pos.z)
                else:
                    bulb_local_pos = branch._local_offset  # NOQA
                    bulb_local_dir = branch._local_direction  # NOQA
                    other_local = _point.Point(*(
                        bulb_local_pos.as_numpy + bulb_local_dir * branch.bulb_length).tolist())

                verts, faces = _cylinder.create(branch.max_dia / 2.0, branch.bulb_length)
                local_angle = _angle.Angle.from_direction(bulb_local_dir)
                verts = verts @ local_angle + bulb_local_pos.as_numpy
                _add(verts, faces)

                verts, faces = _sphere.create(branch.max_dia / 2.0)
                _add(verts + bulb_local_pos.as_numpy, faces)

                verts, faces = _sphere.create(branch.max_dia / 2.0)
                _add(verts + other_local.as_numpy, faces)

        if not all_vertices:
            return np.zeros((0, 3), dtype=np.float32), np.zeros((0, 3), dtype=np.int32)

        vertices = np.concatenate(all_vertices, axis=0).astype(np.float32)
        faces = np.concatenate(all_faces, axis=0).astype(np.int32)
        return vertices, faces

    def _build_mesh(self) -> tuple[np.ndarray, int]:
        if self._mesh is None:
            vertices, faces = self.local_mesh()
            packed, count = _utils.compute_normals(vertices, faces)
            self._mesh = (packed, count)

        return self._mesh

    @property
    def vertices(self) -> np.ndarray:
        packed, count = self._build_mesh()
        return packed[:count * 3]

    @property
    def vertex_count(self) -> int:
        return self._build_mesh()[1]

    @property
    def faces(self) -> None:
        return None

    def _compute_local_bounds(self) -> None:
        if self.vertex_count == 0:
            self.local_aabb = np.zeros((2, 3), dtype=np.float32)
            self.local_obb = np.zeros((8, 3), dtype=np.float32)
            return

        p1, p2 = _utils.compute_aabb(self.vertices.reshape(-1, 3))
        self.local_aabb = np.array([p1.as_float, p2.as_float], dtype=np.float32)
        self.local_obb = _utils.compute_obb(p1, p2)

    @_check_types.do
    def render(self, shaders: "_shader_program.FacesProgram", position: "_point.Point",
               angle: "_angle.Angle", scale: "_point.Point", smooth: bool | None = True,
               material: _materials.GLMaterial | None = None,
               branch_materials: dict | None = None) -> None:
        """Draw every branch at its already-computed WORLD position (see
        ``apply_transform`` -- *position*/*angle*/*scale* are used for
        exactly one thing here: the shared body VBO below, a single
        LOCAL-space mesh with no per-instance world cache of its own,
        unlike any branch. A transition never has a real per-axis scale
        of its own (see ``objects_pegboard/transition.py``), so *scale*
        is always ``Point(1, 1, 1)`` in practice.

        *branch_materials* (``dict[int, GLMaterial]``, keyed by branch
        ``idx``) overrides the material for specific branches -- e.g.
        every branch lit up green/orange by diameter fit while dragging
        a wire/bundle end near this transition (see ``Transition.
        highlight_branch``/``branch_fits``). Any branch idx not in the
        dict draws in *material*, the caller's own default -- which
        (like *material* itself) has already been bound by
        ``BaseVar.render()`` before calling this, exactly as it does
        before any plain VBO's own ``render()``, so this method only
        ever calls ``.set(shaders)`` again when swapping to/from an
        override.
        """
        overrides = branch_materials or {}
        current_override = None

        with shaders:
            if self._body_vbo is not None:
                # Drawn first, before any per-branch override material
                # gets set below -- this single mesh can cover more than
                # one branch's own bulb at once, so it can't be
                # attributed to any ONE branch; it always draws in the
                # caller's own already-bound default material.
                self._body_vbo.render(shaders, position, angle, scale, smooth)

            for branch in self.branches:
                wanted = overrides.get(branch.idx)

                if wanted is not current_override:
                    (wanted if wanted is not None else material).set(shaders)
                    current_override = wanted

                branch.render(shaders, smooth)

            if current_override is not None:
                material.set(shaders)


class Transition(_base_3d.Base3D):
    """Represent a transition in :mod:`harness_designer.objects.objects_3d.transition`.

    UNKNOWN details are inferred from the class name and surrounding code.
    """
    parent: "_transition.Transition" = None
    db_obj: "_pjt_transition.PJTTransition" = None

    @_check_types.do
    def __init__(self, parent: "_transition.Transition",
                 db_obj: "_pjt_transition.PJTTransition") -> None:
        """Initialise the :class:`Transition` instance.

        UNKNOWN details are inferred from the callable name and signature.

        :param parent: Parent object.
        :type parent: :class:`_transition.Transition`
        :param db_obj: Database-backed object.
        :type db_obj: :class:`_pjt_transition.PJTTransition`
        """

        self._part = db_obj.part
        position = db_obj.position3d
        angle = db_obj.angle3d
        color = self._part.color.ui

        material = _materials.Rubber(color)
        branch_count = self.branch_count = self._part.branch_count

        # A plain list of this transition's own real placed
        # PJTTransitionBranch rows, indexed by catalog idx -- Branch
        # itself now owns everything an OLD, separate tip-marker object
        # used to (diameter, world tip position), so there's no longer
        # any local-vs-world position dance needed here at all; each
        # Branch computes its own WORLD tip directly via _Body.
        # apply_transform() below.
        branch_db_objs: list = [None, None, None, None, None, None]
        if branch_count >= 1:
            branch_db_objs[0] = db_obj.branch1
        if branch_count >= 2:
            branch_db_objs[1] = db_obj.branch2
        if branch_count >= 3:
            branch_db_objs[2] = db_obj.branch3
        if branch_count >= 4:
            branch_db_objs[3] = db_obj.branch4
        if branch_count >= 5:
            branch_db_objs[4] = db_obj.branch5
        if branch_count >= 6:
            branch_db_objs[5] = db_obj.branch6

        # Highlight overrides for hit_test_branch/highlight_branch below
        # -- must exist before super().__init__() is called, since that
        # eventually reaches _render_geometry(), which reads this.
        self._branch_materials: dict[int, _materials.GLMaterial] = {}

        with parent.mainframe.editor3d.context:
            self._body = _Body(self._part, branch_db_objs)
            self._body.apply_transform(position, angle)
            self._body.write_tips_to_db()

        scale = _point.Point(1.0, 1.0, 1.0)

        # _Body stands in directly as this object's own VBO -- see its
        # class docstring (the same "compound handler" pattern
        # shapes.text.Text already establishes for a multi-word string):
        # BaseVar's own render()/_compute_aabb()/_compute_obb()/
        # hit_test_step1/2/3 all talk to self._vbo generically and need no
        # Transition-specific override to draw/bound/pick this correctly
        # (only _render_geometry below is overridden, to thread
        # self._branch_materials through to _Body.render()).
        super().__init__(parent, db_obj, self._body, angle,
                         db_obj.position3d, scale, material)

    @property
    @_check_types.do
    def branches(self) -> list:
        """Every one of this transition's own ``Branch`` objects, ordered
        by catalog ``idx``. Public (unlike ``_body``) since this is the
        one piece of ``_Body`` external code is actually meant to reach
        through -- diameter fit-checking, hit-testing, per-branch
        highlighting (see :meth:`branch_fits`/:meth:`hit_test_branch`/
        :meth:`highlight_branch` below).
        """
        return self._body.branches

    @_check_types.do
    def _render_geometry(self, program: "_shader_program.FacesProgram") -> None:
        """Same as ``BaseVar._render_geometry`` (position/angle/scale/
        smooth handed straight to the VBO's own ``render()``), plus this
        transition's own current per-branch highlight overrides -- the
        one thing that override exists for.
        """
        if self._vbo is None:
            return

        angle = self._vbo.render_angle(self._angle)

        self._vbo.render(
            program, self._position, angle, self._scale, self.smooth,
            material=self.material, branch_materials=self._branch_materials)

    @_check_types.do
    def branch_fits(self, branch: "Branch", diameter: float) -> bool:
        """Whether *diameter* (a wire's OD, or a bundle's own diameter)
        fits within *branch*'s own catalog min/max -- the one compatibility
        rule every "does this branch light up" interaction (dragging a
        wire, dropping a transition onto a bundle end, dragging a
        bundle's own end) shares.
        """
        return branch.min_diameter <= diameter <= branch.max_diameter

    @_check_types.do
    def hit_test_branch(self, point: "_point.Point") -> _Union["Branch", None]:
        """The closest of this transition's own branches whose sphere hit
        area (see ``Branch.hit_test_sphere``) contains *point*, or
        ``None``. *point* is a real world-space point the caller already
        has in hand -- a dragged wire/bundle end's own current position
        (``handlers.transition_handler._find_free_bundle_end`` already
        does the equivalent distance check for bundle-end snapping, the
        same pattern). For a bare mouse position with no such point
        (screen-space hover, where depth is unknown), use
        :meth:`hit_test_branch_ray` instead -- a fixed-depth point (e.g.
        a camera focal-plane point) would not reliably line up with
        what's actually under the cursor in 3D.
        """
        best = None
        best_dist_sq = None

        for branch in self._body.branches:
            if not branch.hit_test_sphere(point):
                continue

            dist_sq = float(np.sum((point.as_numpy - branch.tip_point.as_numpy) ** 2))
            if best_dist_sq is None or dist_sq < best_dist_sq:
                best, best_dist_sq = branch, dist_sq

        return best

    @_check_types.do
    def hit_test_branch_ray(self, origin: np.ndarray, direc: np.ndarray) -> _Union["Branch", None]:
        """The closest of this transition's own branches whose sphere hit
        area (``Branch.hit_test_sphere``'s own tip_point/diameter) is
        actually intersected by the world-space ray (*origin*, *direc*,
        *direc* a unit vector) -- real ray-sphere intersection (not the
        coarse bounds-pool pass ``gl.object_picker.find_object`` uses),
        for screen-space mouse hover where the query point's depth isn't
        otherwise known. Callers get *origin*/*direc* from
        ``gl.object_picker.build_ray(mouse_pos, camera)`` -- the same
        ray-construction helper the generic canvas picker itself uses,
        reused here directly rather than duplicated.
        """
        best = None
        best_t = None

        for branch in self._body.branches:
            if branch.tip_point is None:
                continue

            center = branch.tip_point.as_numpy
            radius = branch.diameter / 2.0

            oc = origin - center
            b = float(np.dot(oc, direc))
            c = float(np.dot(oc, oc)) - radius * radius
            discriminant = b * b - c
            if discriminant < 0.0:
                continue

            root = discriminant ** 0.5
            t = -b - root
            if t < 0.0:
                t = -b + root
                if t < 0.0:
                    continue

            if best_t is None or t < best_t:
                best, best_t = branch, t

        return best

    @_check_types.do
    def highlight_branch(self, branch: "Branch", material: "_materials.GLMaterial") -> None:
        """Override *branch*'s own render color to *material* until
        :meth:`clear_branch_highlight`/:meth:`clear_branch_highlights`
        says otherwise. Takes effect on the very next ``render()`` --
        callers still need to trigger a repaint themselves (e.g.
        ``self.editor3d.Refresh()``), same as any other highlight change
        in this app.
        """
        self._branch_materials[branch.idx] = material

    @_check_types.do
    def clear_branch_highlight(self, branch: "Branch") -> None:
        """Undo :meth:`highlight_branch` for one specific *branch* --
        every other branch's own override (if any) is untouched."""
        self._branch_materials.pop(branch.idx, None)

    @_check_types.do
    def clear_branch_highlights(self) -> None:
        """Undo :meth:`highlight_branch` for every branch of this
        transition at once."""
        self._branch_materials.clear()

    @_check_types.do
    def highlight_branches_for_diameter(
        self, diameter: float, fit_material: "_materials.GLMaterial",
        no_fit_material: "_materials.GLMaterial",
        exclude: _Union["Branch", None] = None
    ) -> None:
        """Highlight every one of this transition's own branches at once,
        green/orange (or whatever *fit_material*/*no_fit_material* are)
        by whether *diameter* fits (see :meth:`branch_fits`) -- the
        "light up every compatible branch while dragging a wire/bundle
        end nearby" interaction. *exclude* (if given) is left alone
        entirely, neither highlighted nor cleared -- for a wire/bundle
        end already attached to one branch of this same transition,
        which should keep whatever state it already has.
        """
        for branch in self._body.branches:
            if branch is exclude:
                continue

            material = fit_material if self.branch_fits(branch, diameter) else no_fit_material
            self.highlight_branch(branch, material)

    @property
    @_check_types.do
    def smooth(self) -> bool:
        # getattr, not direct attribute access -- a PreviewTransition
        # subclass (ui/dialogs/transition_editor/preview.py) sets db_obj
        # to a catalog Transition, which has no `smooth` column/property
        # at all (only a placed PJTTransition does).
        smooth = self.db_obj.smooth if isinstance(self.db_obj, _pjt_transition.PJTTransition) else None
        if smooth is None:
            smooth = Config.renderer.smooth_transitions

        return smooth

    @smooth.setter
    @_check_types.do
    def smooth(self, value: bool | None) -> None:
        self._smooth = value

        try:
            self.db_obj.smooth = value
        except AttributeError:
            pass

    @_check_types.do
    def build(self) -> None:
        """(Re)build every branch's own geometry from this transition's
        current catalog/DB data (e.g. after a branch's diameter changes)
        and re-derive this object's WORLD aabb/obb from it -- no branch
        position bookkeeping needed here any more (unlike the old,
        separate tip-marker design): each ``Branch`` computes its own
        WORLD tip directly via ``_Body.apply_transform``, and
        ``write_tips_to_db`` persists it, forced, since a rebuild always
        means this transition's branches need their real placement
        re-applied.
        """
        branch_db_objs = [b.db_obj for b in self._body.branches]

        self._body.rebuild(self._part, branch_db_objs)
        self._body.apply_transform(self._position, self._angle)
        self._body.write_tips_to_db(force=True)

        # _Body.apply_transform() already refreshed local_aabb/local_obb
        # (see its own _compute_local_bounds) -- these two just re-derive
        # this object's WORLD aabb/obb from that fresh local data, exactly
        # as BaseVar.__init__ itself does once, up front (self._vbo.
        # is_dirty is always False for a _Body -- see its own docstring
        # for why that's this method's job instead).
        with self.editor3d.context:
            self._compute_aabb()
            self._compute_obb()

        self.editor3d.Refresh()

    @_check_types.do
    def _update_angle(self, angle: _angle.Angle) -> None:
        """Update the angle.

        UNKNOWN details are inferred from the callable name and signature.

        :param angle: Value for ``angle``.
        :type angle: :class:`_angle.Angle`
        """
        self._body.apply_transform(self._position, angle)
        self._body.write_tips_to_db(force=True)

        super()._update_angle(angle)

    @_check_types.do
    def _update_position(self, position: _point.Point) -> None:
        """Update the position.

        UNKNOWN details are inferred from the callable name and signature.

        :param position: Position value.
        :type position: :class:`_point.Point`
        """
        self._body.apply_transform(position, self._angle)
        self._body.write_tips_to_db(force=True)

        super()._update_position(position)

    @classmethod
    @_check_types.do
    def start_add(
        cls, mainframe: "_ui.MainFrame", part_id: bytes | None = None
    ) -> _Union["_transition.Transition", None]:
        """Bundle-snapping transition placement, ported from
        handlers.transition_handler.AddTransitionHandler -- always
        free/interactive (no housing/bundle argument, matching the
        original, which was only ever invoked from the toolbar).
        """
        from ...ui.dialogs import part_search as _part_search
        from ...ui.editor_db import transition as _trans_editor_page
        from ...add_handlers.editor_3d import transition as _add_transition
        from .. import transition as _transition_facade

        canvas = mainframe.editor3d.editor

        if part_id is None:
            part_id = mainframe.editor_db.editor.transitions.GetSelection()

        if part_id is None:
            dlg = _part_search.SearchDialog(
                mainframe, _trans_editor_page.TransitionsPage, mainframe.global_db.transitions_table,
                'Add Transition')

            if dlg.exec() == QtWidgets.QDialog.DialogCode.Accepted:
                part_id = dlg.GetValue()
            else:
                part_id = None

            dlg.deleteLater()

            if part_id is None:
                return None

        ptables = mainframe.project.ptables
        part = ptables.global_db.transitions_table[part_id]

        highlight_material = _materials.Plastic(
            _color.Color(*_config.Config.colors.add_object.bundle_highlight))

        # Preview: all branch points at the origin -- _build_model fires in
        # Transition.__init__ and positions them locally; hover repositions
        # and rebuilds the whole thing once a bundle is snapped.
        center_db = ptables.pjt_points3d_table.insert(0.0, 0.0, 0.0)
        # NOT a bare Angle() -- that leaves its euler cache uninitialized
        # (Angle.x/.y/.z/.as_euler_float all return nan "or nan when
        # UNKNOWN", by design, until an Angle is built via from_euler()/
        # has a real euler cache set some other way). pjt_transitions_
        # table.insert() immediately stringifies this angle for storage
        # (`angle3d=str(list(angle.as_euler_float))`), so a bare Angle()
        # here writes the literal text "[nan, nan, nan]" to the database
        # -- which a subsequent read (angle3d's getter uses plain eval(),
        # not ast.literal_eval/json.loads) then crashes on with
        # `NameError: name 'nan' is not defined`, since bare eval() has no
        # `nan` bound in its namespace. from_euler(0, 0, 0) has a real,
        # valid cache from the start.
        init_angle = _angle.Angle.from_euler(0.0, 0.0, 0.0)
        name = f'{part.manufacturer.name} {part.part_number}'

        transition_db = ptables.pjt_transitions_table.insert(
            part_id, name, center_db.db_id, init_angle)

        for branch_id in range(1, part.branch_count + 1):
            g_br = part.branches[branch_id - 1]
            pt_db = ptables.pjt_points3d_table.insert(0.0, 0.0, 0.0)
            ptables.pjt_transition_branches_table.insert(
                g_br.db_id, transition_db.db_id, pt_db.db_id, branch_id, float(g_br.min_dia))

            # No pjt_concentrics row created here -- a transition branch no
            # longer needs one at all (see PJTTransitionBranch.concentric/
            # .wires, made independent of the concentric-twisting tables
            # entirely). Concentric twisting is being redesigned -- not
            # every harness is concentric-twisted -- so transitions should
            # carry no attachment to it, per the user (2026-09-27).

        facade = _transition_facade.Transition(mainframe, transition_db)
        facade.obj3d.is_visible = False

        handler = _add_transition.Transition(canvas, facade, part_id, part, highlight_material)
        facade.obj3d._active_handler = handler  # NOQA
        canvas.active_handler_obj = facade.obj3d

        return facade

    @_check_types.do
    def handle_interaction(
        self, last_pos: _point.Point, current_pos: _point.Point, had_motion: bool,
        interaction_type: _interaction.MouseInteraction, clicked_object: _Union["_ObjectBase", None]
    ) -> bool:
        """Forwards to an active add-session (see start_add); falls back
        to Base3D's own generic drag/rotation handling otherwise.
        """
        from ...add_handlers.editor_3d import transition as _add_transition  # NOQA -- avoid a cycle at import time

        if isinstance(self._active_handler, _add_transition.Transition):
            # A local reference, not another read of self._active_handler
            # below -- a CANCEL can delete this object's own facade,
            # whose generic delete() sees self._active_handler is this
            # same handler and clears it right there, before this call
            # even returns (see objects_3d.wire.Wire.handle_interaction).
            handler = self._active_handler
            handled = handler(
                last_pos, current_pos, had_motion, interaction_type, clicked_object)

            if handler.is_finished and self._active_handler is handler:
                self._active_handler = None

            return handled

        return super().handle_interaction(
            last_pos, current_pos, had_motion, interaction_type, clicked_object)

    @_check_types.do
    def get_context_menu(self) -> _Union["TransitionMenu", "BranchMenu"]:
        """Return this transition's own context menu, or -- when the
        right-click that opened it landed on one of its branches' own hit
        spheres (``hit_test_branch_ray``, the same real ray-sphere test
        ``add_handlers.editor_3d.transition`` uses for hover) -- that
        branch's own, much narrower :class:`BranchMenu` instead. A branch
        is no longer its own pickable ``Base3D`` object (see this
        module's own docstring), so this is the only way left to reach a
        branch-specific menu at all.
        """
        from ...gl import object_picker as _object_picker

        canvas = self.mainframe.editor3d.editor

        click_pos = self._context_menu_click_pos
        branch = None
        if click_pos is not None:
            origin, direc = _object_picker.build_ray(click_pos, canvas.camera)
            if origin is not None:
                branch = self.hit_test_branch_ray(origin, direc)

        if branch is not None:
            return BranchMenu(canvas, self, branch)

        return TransitionMenu(canvas, self)


class TransitionMenu(QtWidgets.QMenu):
    """The whole-transition context menu -- rotate/mirror (the transition
    body as a rigid whole), delete and properties only. Per-branch
    actions (see :class:`BranchMenu`) are reached by right-clicking a
    branch specifically, not from here.
    """

    @_check_types.do
    def __init__(self, canvas: "_editor_3d.Editor3DPanel", selected: "Transition") -> None:
        """Initialise the :class:`TransitionMenu` instance.

        UNKNOWN details are inferred from the callable name and signature.

        :param canvas: Canvas instance.
        :type canvas: UNKNOWN
        :param selected: Value for ``selected``.
        :type selected: UNKNOWN
        """
        QtWidgets.QMenu.__init__(self)
        self.canvas = canvas
        self.selected = selected

        rotate_menu = _context_menus.Rotate3DMenu(canvas, selected.parent)
        self.addMenu(rotate_menu)

        mirror_menu = _context_menus.Mirror3DMenu(canvas, selected.parent)
        self.addMenu(mirror_menu)

        self.addSeparator()
        action = self.addAction('Delete')
        action.triggered.connect(self.on_delete)

        self.addSeparator()
        action = self.addAction('Properties')
        action.triggered.connect(self.on_properties)

    @_check_types.do
    def on_delete(self) -> None:
        """Delete this transition from the project."""
        _menu_ops.delete_object(self.selected)

    @_check_types.do
    def on_properties(self) -> None:
        """Show this transition's properties in the object editor."""
        _menu_ops.show_properties(self.selected)


class BranchMenu(QtWidgets.QMenu):
    """A single branch's own context menu -- just "Add Bundle" (disabled
    once the branch already has a bundle attached, see
    ``PJTTransitionBranch.bundle``). Every other right-click action on a
    transition (rotate, mirror, delete, properties) stays on the
    transition as a whole -- see :class:`TransitionMenu` -- since a
    branch has no independent identity to rotate/mirror/delete on its
    own.
    """

    @_check_types.do
    def __init__(self, canvas: "_editor_3d.Editor3DPanel", transition: "Transition", branch: "Branch") -> None:
        QtWidgets.QMenu.__init__(self)
        self.canvas = canvas
        self.transition = transition
        self.branch = branch

        action = self.addAction('Add Bundle')
        action.setEnabled(branch.db_obj is not None and branch.db_obj.bundle is None)
        action.triggered.connect(self.on_add_bundle)

    @_check_types.do
    def on_add_bundle(self) -> None:
        """Start a new bundle whose start point attaches to this branch --
        see ``objects.objects_3d.bundle.Bundle.start_add_from_branch``.
        """
        from . import bundle as _bundle_3d

        mainframe = self.transition.mainframe
        transition = self.transition.parent
        branch = self.branch

        @_check_types.do
        def _do() -> None:
            _bundle_3d.Bundle.start_add_from_branch(mainframe, transition, branch)

        QtCore.QTimer.singleShot(0, _do)
