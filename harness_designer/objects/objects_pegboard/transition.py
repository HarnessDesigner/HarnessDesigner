# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

from typing import TYPE_CHECKING, Union as _Union

import numpy as np
import build123d
import math
from PySide6.QtWidgets import QMenu

from . import base_pegboard as _base_pegboard
from ...shapes import cylinder as _cylinder
from ...shapes import sphere as _sphere
from ...gl import vbo as _vbo
from ...gl import materials as _materials
from ...geometry import point as _point
from ...geometry import angle as _angle
from ... import utils as _utils
from ... import logger as _logger
from ... import check_types as _check_types
from ... import config as _config


if TYPE_CHECKING:
    from ...database.global_db import transition as _g_transition
    from ...database.global_db import transition_branch as _g_transition_branch
    from ...database.project_db import pjt_transition as _pjt_transition
    from ...database.project_db import pjt_transition_branch as _pjt_transition_branch
    from .. import transition as _transition
    from ...gl.shaders import program as _shader_program


Config = _config.Config.editor_pegboard

_ZERO_ANGLE = _angle.Angle.from_euler(0.0, 0.0, 0.0)

# Part numbers whose bulb pieces have already been tried and failed to
# fuse into one single build123d solid this session -- see _PegBody.
# _build_body_model. Kept in its own set (not imported from
# objects_3d.transition) per this file's own established convention of
# duplicating this apparatus rather than sharing it -- even though the
# ACTUAL pooled VBO the two views build (see _build_body_model's own
# vbo_id) is now the exact same one, deliberately, so a failure
# recorded by either view really does mean the same thing for both.
_FAILED_BODY_IDS: set[str] = set()


@_check_types.do
def _branch_direction(angle: "_angle.Angle") -> np.ndarray:
    """Identical to ``objects_3d.transition._branch_direction`` --
    duplicated, not imported, per the user's own steer (2026-09-27) that
    this whole apparatus belongs directly in each view's own file rather
    than shared. No peg-board-specific flatten here (or anywhere else in
    this file, 2026-09-29) -- see this module's own updated docstring at
    the top of ``Transition`` for where that now lives instead.
    """
    direction = np.array([1.0, 0.0, 0.0], dtype=np.float32) @ angle
    direction = np.asarray(direction, dtype=np.float32)
    norm = float(np.linalg.norm(direction))
    if norm > 1e-9:
        direction /= norm

    return direction


class _PegBranch:
    """Peg-board equivalent of ``objects_3d.transition.Branch`` -- see
    that class's own docstring for the general shape (geometry cache AND
    real identity in one object, no separate pickable ``Base3D`` object
    of its own, ``Transition`` below owns all real per-branch
    interaction). Duplicated directly rather than imported/shared, same
    as ``_branch_direction`` above.

    No peg-board-specific geometry transform anywhere in this class
    (2026-09-29, corrected from an earlier pass that baked a fixed
    -90-about-X "flatten" into every local point/direction here) -- this
    branch's own LOCAL data is built exactly like the 3D view's
    ``Branch``, in the SAME native/catalog orientation. The peg-board's
    own correct-for-viewing rotation comes entirely from
    ``pjt_transitions.angle_pegboard``/``quat_pegboard``'s own DATABASE
    DEFAULT (see ``database/create_database/transitions.py``), which is
    a -90-about-X quaternion, not identity, for exactly this reason --
    every branch/hub piece is positioned by the SAME ``update_position``/
    ``update_angle``/``_refresh_world`` pipeline as the 3D view, fed
    whatever ``angle_pegboard`` actually holds, and that value already
    IS the needed rotation from the moment a transition is first placed.
    The peg-board's own rotation control only ever writes Y (see
    ``Transition``'s own docstring below), so this X component is never
    touched again after that first default. VBOs (including the shared
    build123d body -- see ``_PegBody._build_body_model``) are pooled by
    id across BOTH views, so this class's geometry must match the 3D
    view's ``Branch`` exactly, not just visually -- any transform
    difference between the two would corrupt whichever view resolves
    the shared pool entry second.
    """

    @_check_types.do
    def __init__(self, catalog_branch: "_g_transition_branch.TransitionBranch",
                 db_obj: "_pjt_transition_branch.PJTTransitionBranch | None" = None) -> None:
        self.idx = catalog_branch.idx
        self.catalog_branch = catalog_branch
        self.db_obj = db_obj

        self.length = catalog_branch.length
        self.bulb_length = catalog_branch.bulb_length
        self.max_dia = catalog_branch.max_dia

        self._local_offset = catalog_branch.offset.copy()
        self._local_direction = _branch_direction(catalog_branch.angle)

        bulb_offset = catalog_branch.bulb_offset
        # `is not None` is the right (and only) check -- see
        # objects_3d.transition.Branch.__init__'s own comment on why a
        # stored `[0, 0, 0]` is NOT the same thing as NULL.
        self._has_own_bulb_offset = bool(self.bulb_length and bulb_offset is not None)

        if self._has_own_bulb_offset:
            self._local_bulb_offset = bulb_offset.copy()
        else:
            self._local_bulb_offset = None

        self.local_tip = _point.Point(*(
            self._local_offset.as_numpy + self._local_direction * self.length).tolist())

        self._use_body_model = False

        self.diameter: float | None = None
        self.branch_scale: "_point.Point | None" = None
        self.bulb_scale: "_point.Point | None" = None
        self.bulb_sphere_scale: "_point.Point | None" = None

        self._position: "_point.Point" = _point.Point(0.0, 0.0, 0.0)
        self._angle: "_angle.Angle" = _angle.Angle.from_euler(0.0, 0.0, 0.0)
        self.branch_start: "_point.Point | None" = None
        self.branch_angle: "_angle.Angle | None" = None
        self.tip_point: "_point.Point | None" = None
        self.bulb_start: "_point.Point | None" = None
        self.bulb_angle: "_angle.Angle | None" = None
        self.bulb_end: "_point.Point | None" = None
        self.bulb_start_sphere: "_point.Point | None" = None

        if db_obj is not None and db_obj.diameter is not None:
            seed_diameter = db_obj.diameter
        else:
            seed_diameter = catalog_branch.min_dia

        self.update_diameter(seed_diameter)

    @property
    @_check_types.do
    def min_diameter(self) -> float:
        return self.catalog_branch.min_dia

    @property
    @_check_types.do
    def max_diameter(self) -> float:
        return self.catalog_branch.max_dia

    @_check_types.do
    def set_diameter(self, diameter: float) -> None:
        """See ``objects_3d.transition.Branch.set_diameter``'s own
        docstring -- diameter is a single shared column
        (``PJTTransitionBranch.diameter``), so this and the 3D view's
        own ``set_diameter`` write through to the exact same row."""
        if self.db_obj is not None:
            self.db_obj.diameter = diameter

        self.update_diameter(diameter)

    @_check_types.do
    def update_diameter(self, diameter: float) -> None:
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
        """See ``objects_3d.transition.Branch.use_body_model``'s own
        docstring."""
        if value == self._use_body_model:
            return

        self._use_body_model = value
        self._refresh_world()

    @_check_types.do
    def update_position(self, position: "_point.Point") -> None:
        self._position = position
        self._refresh_world()

    @_check_types.do
    def update_angle(self, angle: "_angle.Angle") -> None:
        self._angle = angle
        self._refresh_world()

    def _refresh_world(self) -> None:
        """See ``objects_3d.transition.Branch._refresh_world``'s own
        docstring for why this always rebuilds fresh from local data
        rather than composing two ``Angle`` objects."""
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

        self.tip_point = _point.Point(*(
            world_start.as_numpy + world_direction * self.length).tolist())

        if not self.bulb_length:
            self.bulb_start = None
            self.bulb_angle = None
            self.bulb_end = None
            self.bulb_start_sphere = None
            return

        self.bulb_angle = self.branch_angle

        # Identical to objects_3d.transition.Branch._refresh_world's own
        # cap_shift -- no peg-board-specific transform here (2026-09-29).
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
            trimmed_length = self.length - float(
                np.dot(self.bulb_end.as_numpy - world_start.as_numpy, world_direction))
            trimmed_length = max(trimmed_length, 0.0)

            self.branch_start = self.bulb_end.copy()
            self.branch_scale = _point.Point(self.diameter, self.diameter, trimmed_length)

    @_check_types.do
    def render(self, program: "_shader_program.FacesProgram", smooth: bool | None) -> None:
        cyl = _cylinder.create_vbo()
        cyl.render(program, self.branch_start, self.branch_angle, self.branch_scale, smooth)

        if self._use_body_model:
            return

        if self.bulb_scale is not None:
            cyl.render(program, self.bulb_start, self.bulb_angle, self.bulb_scale, smooth)

            sph = _sphere.create_vbo()
            sph.render(program, self.bulb_end, _ZERO_ANGLE, self.bulb_sphere_scale, smooth)

            if self.bulb_start_sphere is not None:
                sph.render(program, self.bulb_start_sphere, _ZERO_ANGLE, self.bulb_sphere_scale, smooth)

    @_check_types.do
    def write_tip_to_db(self, force: bool = False) -> None:
        """See ``objects_3d.transition.Branch.write_tip_to_db``'s own
        docstring -- writes ``db_obj.position_pegboard`` (this branch's
        OWN independent peg-board point, via
        ``PositionPegboardMixin`` -- NOT ``position3d``, which is the 3D
        view's own point on this exact same row)."""
        if self.db_obj is None or self.tip_point is None:
            return

        pos = self.db_obj.position_pegboard
        if pos.as_float == (0.0, 0.0, 0.0) or force:
            with pos:
                pos.x = self.tip_point.x
                pos.y = self.tip_point.y
                pos.z = self.tip_point.z

    @_check_types.do
    def hit_test_sphere(self, point: "_point.Point") -> bool:
        """See ``objects_3d.transition.Branch.hit_test_sphere``'s own
        docstring."""
        if self.tip_point is None:
            return False

        radius = self.diameter / 2.0
        dist_sq = float(np.sum((point.as_numpy - self.tip_point.as_numpy) ** 2))
        return dist_sq <= radius * radius

    @_check_types.do
    def build_bulb_solid(self) -> build123d.Solid | build123d.Compound | None:
        """Byte-for-byte identical to ``objects_3d.transition.Branch.
        build_bulb_solid`` -- builds in this branch's own native/catalog
        orientation. Not a coincidence: the mesh this produces (via
        ``_PegBody._build_body_model``) is pooled under the EXACT SAME
        VBO id the 3D view's own body uses, and rendered with whatever
        angle the caller passes in (``angle_pegboard``, which defaults
        to the needed -90-about-X rotation at the database level -- see
        ``Transition``'s own docstring below) -- so this method must
        never diverge from the 3D view's own version."""
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
            pl = build123d.Plane(origin=offset.as_float, z_dir=(1, 0, 0))

            sphere = pl * build123d.Sphere(max_dia / 2.0)

            model += sphere

            r = math.radians(angle.z)
            pos = _point.Point(round(bulb_len * math.cos(r), 6),
                               round(bulb_len * math.sin(r), 6),
                               0.0) + offset

            pl = build123d.Plane(origin=pos.as_float, z_dir=(1, 0, 0))

            sphere = pl * build123d.Sphere(max_dia / 2.0).rotate(
                build123d.Axis(origin=(0, 0, 0), direction=(1, 0, 0)), angle.z)

            model += sphere

        return model


class _PegBody:
    """Peg-board equivalent of ``objects_3d.transition._Body`` -- a
    transition's whole body, standing in as this view's own ``self._vbo``.
    Deliberately its OWN, independent PYTHON OBJECT from the 3D view's
    ``_Body`` (never shared) -- since each branch's own render() draws
    from already-cached WORLD attributes rather than the *position*/
    *angle* arguments ``BaseVar._render_geometry`` passes it, one shared
    ``_Body`` instance could only ever be correctly positioned for ONE
    of the two views at a time. See TRANSITION_DESIGN.md for the full
    history here.

    The build123d BODY MESH itself (``_build_body_model``'s own
    ``self._body_vbo``) is a different story: that IS shared with the
    3D view, deliberately, via the ordinary VBO pool (same id, same
    ``PooledVBOHandler`` entry) -- see that method's own docstring.

    No separate hub sphere (removed 2026-09-28, matching the 3D view's
    own removal -- see TRANSITION_DESIGN.md section 8.9/8.11).
    """

    is_dirty = False

    @_check_types.do
    def __init__(self, part: "_g_transition.Transition", branch_db_objs: list) -> None:
        self.branches: list[_PegBranch] = []
        self._mesh: tuple[np.ndarray, int] | None = None
        self.local_aabb = np.zeros((2, 3), dtype=np.float32)
        self.local_obb = np.zeros((8, 3), dtype=np.float32)

        # The whole-transition build123d "body" -- see
        # objects_3d.transition._Body's own docstring -- pooled under
        # the EXACT SAME id the 3D view uses (part_number + ':transition'
        # -- see _build_body_model), since it's the exact same mesh in
        # the exact same (native/catalog) orientation; whichever view
        # builds it first, the other just resolves the same pool entry.
        self._body_vbo: _vbo.PooledVBOHandler | None = None

        self.rebuild(part, branch_db_objs)

    @_check_types.do
    def rebuild(self, part: "_g_transition.Transition", branch_db_objs: list) -> None:
        """See ``objects_3d.transition._Body.rebuild``'s own docstring --
        *branch_db_objs* is a plain list (indexed by catalog ``idx``) of
        this transition's own real placed ``PJTTransitionBranch`` rows
        (``None`` for a preview transition with no placed rows at all).
        Built independently from the 3D view's own branch list -- each
        view owns its own ``_PegBranch``/``Branch`` instances, reading
        the SAME underlying database rows.
        """
        self.branches = []
        self._mesh = None

        for catalog_branch in part.branches:
            db_obj = branch_db_objs[catalog_branch.idx]
            self.branches.append(_PegBranch(catalog_branch, db_obj))

        self._build_body_model(part)

        self._compute_local_bounds()

    @_check_types.do
    def write_tips_to_db(self, force: bool = False) -> None:
        """See ``objects_3d.transition._Body.write_tips_to_db``'s own
        docstring -- persists into each branch's own
        ``position_pegboard``, not ``position3d``."""
        for branch in self.branches:
            branch.write_tip_to_db(force=force)

    @_check_types.do
    def _build_body_model(self, part: "_g_transition.Transition") -> None:
        """See ``objects_3d.transition._Body._build_body_model``'s own
        docstring for the general design (pooled by part number, no
        explicit ``is_valid``/``len(solids()) == 1`` check, relies on
        ``convert_model_to_mesh`` raising on a ``ShapeList``).

        No peg-board-specific transform here at all (2026-09-29,
        corrected from an earlier pass that rotated the fused body -90
        degrees about X before meshing) -- ``vbo_id`` is deliberately
        the EXACT SAME id ``objects_3d.transition._Body.
        _build_body_model`` uses (``part_number + ':transition'``, no
        peg-board-specific suffix), because VBOs are pooled globally
        across every view/context in this app, not per-view: the 3D
        view and the peg-board view share the literal same
        ``PooledVBOHandler`` entry for a given part number. Whichever
        view happens to place/load that part number first builds the
        mesh (in native/catalog orientation, same as the 3D view); the
        other resolves the same pool entry on the very next
        ``vbo_id in _vbo.PooledVBOHandler`` check and never rebuilds it.
        The correct-for-viewing rotation comes entirely from whatever
        angle this body is RENDERED with (``angle_pegboard``, defaulted
        at the database level -- see ``Transition``'s own docstring),
        never from the mesh itself.
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
            _logger.traceback(exc, msg=f'pegboard transition body model build failed for {vbo_id}')
            _FAILED_BODY_IDS.add(vbo_id)
            for branch in self.branches:
                branch.use_body_model(False)
            return

        for branch in self.branches:
            branch.use_body_model(bool(branch.bulb_length))

    @_check_types.do
    def apply_transform(self, position: "_point.Point", angle: "_angle.Angle") -> None:
        for branch in self.branches:
            branch.update_position(position)
            branch.update_angle(angle)

    @_check_types.do
    def render_angle(self, angle: "_angle.Angle") -> "_angle.Angle":
        return angle

    def acquire(self) -> None:
        """No-op -- see ``objects_3d.transition._Body.acquire``."""

    def release(self) -> None:
        """No-op -- see ``objects_3d.transition._Body.release``."""

    @property
    def ctx(self):
        from PySide6.QtGui import QOpenGLContext

        ctx = QOpenGLContext.currentContext()
        if ctx is None:
            raise RuntimeError('context has not been acquired')

        return ctx

    @_check_types.do
    def local_mesh(self) -> tuple[np.ndarray, np.ndarray]:
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
    def faces(self):
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
               material: "_materials.GLMaterial | None" = None,
               branch_materials: dict | None = None) -> None:
        """See ``objects_3d.transition._Body.render``'s own docstring."""
        overrides = branch_materials or {}
        current_override = None

        with shaders:
            if self._body_vbo is not None:
                self._body_vbo.render(shaders, position, angle, scale, smooth)

            for branch in self.branches:
                wanted = overrides.get(branch.idx)

                if wanted is not current_override:
                    (wanted if wanted is not None else material).set(shaders)
                    current_override = wanted

                branch.render(shaders, smooth)

            if current_override is not None:
                material.set(shaders)


class Transition(_base_pegboard.BasePegboard):
    """
    Peg Board Editor representation of a transition -- own independent
    ``_PegBody`` PYTHON OBJECT, never the 3D view's own (see
    ``_PegBody``'s own docstring for why the two can't be shared), but
    the build123d body MESH it wraps IS the exact same pooled VBO the 3D
    view uses (again, see ``_PegBody``'s own docstring).

    Renders correctly flat on the peg-board with no per-branch/per-piece
    transform anywhere in this file (2026-09-29, corrected from an
    earlier pass that baked a fixed rotation into local branch data and
    a separate whole-body build123d rotation) -- instead,
    ``pjt_transitions.angle_pegboard``/``quat_pegboard`` DEFAULT to a
    -90-degree-about-X rotation at the schema level (see
    ``database/create_database/transitions.py``), not identity like
    every other pegboard-placed table's own default. Every branch is
    positioned by the exact same ``update_position``/``update_angle``/
    ``_refresh_world`` pipeline the 3D view uses, fed whatever
    ``angle_pegboard`` actually holds -- since that default already IS
    the needed rotation from the moment a transition is first placed,
    nothing here needs to compute or apply it separately. The
    peg-board's own rotation control only ever writes Y (never X), so
    this default is never overwritten once set.
    """
    db_obj: "_pjt_transition.PJTTransition"

    @_check_types.do
    def __init__(self, parent: "_transition.Transition",
                 db_obj: "_pjt_transition.PJTTransition"):
        """Initialise the :class:`Transition` instance.

        :param parent: Parent object.
        :type parent: :class:`_transition.Transition`
        :param db_obj: Database-backed object.
        :type db_obj: :class:`_pjt_transition.PJTTransition`
        """
        self._part = db_obj.part
        branch_count = self._part.branch_count

        # Built directly from db_obj.branch1..branch6 -- the SAME
        # PJTTransitionBranch rows the 3D view's own Transition.__init__
        # reads, but this view constructs its OWN independent _PegBranch
        # objects from them rather than reusing the 3D view's Branch
        # instances (see _PegBody's own docstring for why the two bodies
        # can never be shared).
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

        # scale/material are built fresh here, never borrowed from
        # obj3d -- see objects_pegboard.housing.Housing.__init__'s own
        # comment on why. A transition has no Scale3DMixin (no single
        # physical size stored for it), so scale falls back to identity;
        # material is rebuilt from the catalog part's own color, mirroring
        # objects_3d.transition.Transition.__init__'s own construction.
        scale = _point.Point(1.0, 1.0, 1.0)
        angle = db_obj.angle_pegboard
        position = db_obj.position_pegboard

        # Highlight overrides -- see objects_3d.transition.Transition.
        # __init__'s own comment; must exist before super().__init__(),
        # which eventually reaches _render_geometry() below.
        self._branch_materials: dict[int, _materials.GLMaterial] = {}

        with parent.mainframe.editor_pegboard.context:
            self._body = _PegBody(self._part, branch_db_objs)
            self._body.apply_transform(position, angle)
            self._body.write_tips_to_db()

        super().__init__(
            parent, db_obj,
            vbo=self._body,
            angle=angle,
            position=position,
            scale=scale,
            material=_materials.Rubber(self._part.color.ui),
        )

        # Identity key for gl.canvas_pegboard's bundle-graph matching --
        # keyed by this transition's own peg-board point, not its 3D one
        # (see housing.py's own comment on why).
        self.point3d_id = db_obj.position_pegboard_id

        if self._position.x == 0.0 and self._position.z == 0.0:
            pos3d = db_obj.position3d
            self._position.x = float(pos3d.x)
            self._position.z = float(pos3d.z)
            self._body.apply_transform(self._position, self._angle)
            self._body.write_tips_to_db(force=True)

    @property
    @_check_types.do
    def branches(self) -> list:
        """See ``objects_3d.transition.Transition.branches``'s own
        docstring -- this view's OWN ``_PegBranch`` objects, not the 3D
        view's."""
        return self._body.branches

    @_check_types.do
    def _render_geometry(self, program: "_shader_program.FacesProgram") -> None:
        """See ``objects_3d.transition.Transition._render_geometry``'s
        own docstring."""
        if self._vbo is None:
            return

        angle = self._vbo.render_angle(self._angle)

        self._vbo.render(
            program, self._position, angle, self._scale, self.smooth,
            material=self.material, branch_materials=self._branch_materials)

    @_check_types.do
    def branch_fits(self, branch: "_PegBranch", diameter: float) -> bool:
        """See ``objects_3d.transition.Transition.branch_fits``'s own
        docstring."""
        return branch.min_diameter <= diameter <= branch.max_diameter

    @_check_types.do
    def hit_test_branch(self, point: "_point.Point") -> _Union["_PegBranch", None]:
        """See ``objects_3d.transition.Transition.hit_test_branch``'s own
        docstring."""
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
    def hit_test_branch_ray(self, origin: np.ndarray, direc: np.ndarray) -> _Union["_PegBranch", None]:
        """See ``objects_3d.transition.Transition.hit_test_branch_ray``'s
        own docstring."""
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
    def highlight_branch(self, branch: "_PegBranch", material: "_materials.GLMaterial") -> None:
        """See ``objects_3d.transition.Transition.highlight_branch``'s
        own docstring."""
        self._branch_materials[branch.idx] = material

    @_check_types.do
    def clear_branch_highlight(self, branch: "_PegBranch") -> None:
        """See ``objects_3d.transition.Transition.clear_branch_highlight``'s
        own docstring."""
        self._branch_materials.pop(branch.idx, None)

    @_check_types.do
    def clear_branch_highlights(self) -> None:
        """See
        ``objects_3d.transition.Transition.clear_branch_highlights``'s
        own docstring."""
        self._branch_materials.clear()

    @_check_types.do
    def highlight_branches_for_diameter(
        self, diameter: float, fit_material: "_materials.GLMaterial",
        no_fit_material: "_materials.GLMaterial",
        exclude: _Union["_PegBranch", None] = None
    ) -> None:
        """See
        ``objects_3d.transition.Transition.highlight_branches_for_diameter``'s
        own docstring."""
        for branch in self._body.branches:
            if branch is exclude:
                continue

            material = fit_material if self.branch_fits(branch, diameter) else no_fit_material
            self.highlight_branch(branch, material)

    @_check_types.do
    def _update_angle(self, angle: "_angle.Angle") -> None:
        self._body.apply_transform(self._position, angle)
        self._body.write_tips_to_db(force=True)
        super()._update_angle(angle)

    @_check_types.do
    def _update_position(self, position: "_point.Point") -> None:
        self._body.apply_transform(position, self._angle)
        self._body.write_tips_to_db(force=True)
        super()._update_position(position)

    @_check_types.do
    def build(self) -> None:
        """See ``objects_3d.transition.Transition.build``'s own docstring
        -- replaces the earlier ``rebuild()`` (renamed for consistency;
        it had no callers of its own before this, per its own previous
        docstring, so nothing else needed updating for the rename).
        Rebuilds this view's OWN branches directly from
        ``db_obj.branch1..branch6`` -- no longer fed from the 3D view's
        own branch list at all (each view is now fully independent, per
        ``_PegBody``'s own docstring).
        """
        db_obj = self.db_obj
        branch_count = self._part.branch_count

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

        with self.mainframe.editor_pegboard.context:
            self._body.rebuild(self._part, branch_db_objs)
            self._body.apply_transform(self._position, self._angle)
            self._body.write_tips_to_db(force=True)

    @property
    @_check_types.do
    def smooth(self) -> bool:
        smooth = self.db_obj.smooth
        if smooth is None:
            smooth = Config.renderer.smooth_transitions

        return smooth

    @smooth.setter
    def smooth(self, value: bool | None):
        self._smooth = value

        try:
            self.db_obj.smooth = value
        except AttributeError:
            pass

    @_check_types.do
    def get_context_menu(self):
        """Return this transition's own right-click context menu (see
        ``ui/mainframe.py``'s ``_on_obj_right_click_pegboard``).
        """
        return TransitionMenu(self.pegboard.editor, self)


class TransitionMenu(QMenu):
    """Right-click menu for a pegboard Transition."""

    @_check_types.do
    def __init__(self, canvas, selected: "Transition"):
        QMenu.__init__(self)
        self.canvas = canvas
        self.selected = selected

        action = self.addAction('Show Table')
        action.setEnabled(not self.selected.has_visible_table())
        action.triggered.connect(self.on_show_table)

        self.addSeparator()
        action = self.addAction('Select')
        action.triggered.connect(self.on_select)

        self.addSeparator()
        action = self.addAction('Delete')
        action.triggered.connect(self.on_delete)

        self.addSeparator()
        action = self.addAction('Properties')
        action.triggered.connect(self.on_properties)

    @_check_types.do
    def on_show_table(self):
        """Show this transition's own peg-board wire table -- creating
        it the first time, or just re-showing it (see
        ``BasePegboard.show_table``).
        """
        self.selected.show_table()

    @_check_types.do
    def on_select(self):
        """Make this transition the active selection."""
        from ...objects.objects_3d import menu_ops as _menu_ops
        _menu_ops.select_object_for_object(self.selected.parent.mainframe, self.selected.parent)

    @_check_types.do
    def on_delete(self):
        """Delete this transition from the project."""
        from ...objects.objects_3d import menu_ops as _menu_ops
        _menu_ops.delete_object(self.selected)

    @_check_types.do
    def on_properties(self):
        """Show this transition's properties in the object editor."""
        from ...objects.objects_3d import menu_ops as _menu_ops
        _menu_ops.show_properties_for_object(self.selected.parent.mainframe, self.selected.parent)
