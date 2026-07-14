# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

"""
Peg board anchor collection -- Phase 1 static top-down layout.

Walks the currently open project's housings, splices, transitions, and
bare (not-yet-seated) terminals and builds one :class:`PegboardAnchor` per
placed part that already has a live 3D scene object. Each anchor reuses
the exact same VBO/material/scale the 3D editor renders with (see
``gl.canvas_pegboard.canvas.Canvas._render_objects``) -- nothing is
re-tessellated or duplicated for the peg board.

Position is the real 3D scene position's (X, Z) components projected
straight down onto the board -- no persistence, no user-driven layout yet
(that is a later phase, backed by the ``pjt_pegboard_*`` tables). Rotation
is the "lay it flat" quaternion computed by
:mod:`harness_designer.gl.canvas_pegboard.flatten`, derived purely from
each part's own local OBB, independent of its current as-mounted 3D
angle.
"""

from dataclasses import dataclass
from typing import TYPE_CHECKING

from .. import vbo as _vbo
from .. import materials as _materials
from ...geometry import point as _point
from ...geometry.angle import quaternion as _quaternion
from . import flatten as _flatten


if TYPE_CHECKING:
    from ...objects import project as _project
    from ...objects import object_base as _object_base


@dataclass
class PegboardAnchor:
    """One renderable placed part on the peg board.

    Carries everything ``Canvas._render_objects`` needs to draw it under
    the schematic2d shader, without needing to reach back into the
    project/DB layer at render time. Also carries a back-reference to the
    placed part's :class:`~harness_designer.objects.object_base.ObjectBase`
    wrapper (``obj``) and an axis-aligned XZ hit-test footprint
    (``half_width``/``half_depth``) so
    ``gl.canvas_pegboard.mouse_handler.MouseHandlerPegBoard`` can resolve a
    top-down click to the object it hit and drive the same
    ``ObjectBase.set_selected()``-based cross-editor selection sync every
    other editor already participates in.
    """

    obj: "_object_base.ObjectBase"
    vbo: "_vbo.VBOHandlerBase"
    material: "_materials.GLMaterial"
    scale: "_point.Point"
    smooth: bool
    x: float
    z: float
    rotation: "_quaternion.Quaternion"
    half_width: float
    half_depth: float


def _footprint(obj3d, scale: "_point.Point") -> tuple[float, float]:
    """Compute an axis-aligned XZ hit-test footprint for one placed part.

    Derived from the part's live 3D scene object's local AABB
    (``obj3d._vbo.local_aabb``), scaled by its current 3D scale -- the same
    inputs ``objects.objects3d.base3d.Base3D._compute_aabb`` uses for its
    own (rotation-aware) world AABB. This is deliberately axis-aligned and
    ignores the peg board's own "lay it flat" rotation -- good enough for
    hit-testing a top-down click, not full OBB precision.

    :param obj3d: The placed part's live 3D scene object.
    :type obj3d: :class:`harness_designer.objects.objects3d.base3d.Base3D`
    :param scale: The part's current 3D scale.
    :type scale: :class:`_point.Point`
    :returns: ``(half_width, half_depth)`` in world units (mm).
    :rtype: tuple[float, float]
    """
    local_min = obj3d._vbo.local_aabb[0]  # NOQA
    local_max = obj3d._vbo.local_aabb[1]  # NOQA

    sx, _, sz = scale.as_float

    half_width = float(local_max[0] - local_min[0]) * abs(sx) / 2.0
    half_depth = float(local_max[2] - local_min[2]) * abs(sz) / 2.0

    return half_width, half_depth


def _housing_anchors(project: "_project.Project") -> list["PegboardAnchor"]:
    """Collect one anchor per placed housing.

    Skips rows whose live 3D object hasn't been built yet, and rows whose
    part has no ``Model3D`` (nothing to derive a flatten rotation from).
    """
    anchors = []

    for row in project.ptables.pjt_housings_table:
        obj = row.get_object()
        if obj is None:
            continue

        obj3d = obj.obj3d
        if obj3d is None or obj3d._vbo is None:  # NOQA
            continue

        part = row.part
        model3d = None if part is None else part.model3d
        if model3d is None:
            continue

        pos = row.position3d
        rotation = _flatten.flatten_quaternion_for_model3d(
            obj3d._vbo.local_obb, model3d.forward_up)  # NOQA
        half_width, half_depth = _footprint(obj3d, obj3d.scale)

        anchors.append(PegboardAnchor(
            obj=obj,
            vbo=obj3d._vbo,  # NOQA
            material=obj3d.material,
            scale=obj3d.scale,
            smooth=getattr(obj3d, 'smooth', False),
            x=float(pos.x),
            z=float(pos.z),
            rotation=rotation,
            half_width=half_width,
            half_depth=half_depth,
        ))

    return anchors


def _splice_anchors(project: "_project.Project") -> list["PegboardAnchor"]:
    """Collect one anchor per placed splice.

    ``StartStopPosition3DMixin`` means a splice has no single
    ``position3d`` -- the start/stop midpoint is used as the anchor
    position instead. This is a deliberate, acknowledged Phase-1
    simplification (not an attempt to reverse-engineer the exact 3D mesh
    placement offset ``objects.objects3d.splice`` uses) -- good enough for
    a default static layout.
    """
    anchors = []

    for row in project.ptables.pjt_splices_table:
        obj = row.get_object()
        if obj is None:
            continue

        obj3d = obj.obj3d
        if obj3d is None or obj3d._vbo is None:  # NOQA
            continue

        part = row.part
        model3d = None if part is None else part.model3d
        if model3d is None:
            continue

        p1 = row.start_position3d
        p2 = row.stop_position3d
        x = float(p1.x + p2.x) / 2.0
        z = float(p1.z + p2.z) / 2.0

        rotation = _flatten.flatten_quaternion_for_model3d(
            obj3d._vbo.local_obb, model3d.forward_up)  # NOQA
        half_width, half_depth = _footprint(obj3d, obj3d.scale)

        anchors.append(PegboardAnchor(
            obj=obj,
            vbo=obj3d._vbo,  # NOQA
            material=obj3d.material,
            scale=obj3d.scale,
            smooth=getattr(obj3d, 'smooth', False),
            x=x,
            z=z,
            rotation=rotation,
            half_width=half_width,
            half_depth=half_depth,
        ))

    return anchors


def _transition_anchors(project: "_project.Project") -> list["PegboardAnchor"]:
    """Collect one anchor per placed transition.

    Transitions have no ``Model3D``/OBB of their own -- their OBB comes
    from their own live ``obj3d._vbo.local_obb``, freshly computed from the
    procedurally-generated mesh, so
    :func:`~harness_designer.gl.canvas_pegboard.flatten.flatten_quaternion_for_transition`
    is used instead of the ``Model3D``-based helper.
    """
    anchors = []

    for row in project.ptables.pjt_transitions_table:
        obj = row.get_object()
        if obj is None:
            continue

        obj3d = obj.obj3d
        if obj3d is None or obj3d._vbo is None:  # NOQA
            continue

        pos = row.position3d
        rotation = _flatten.flatten_quaternion_for_transition(obj3d._vbo.local_obb)  # NOQA
        half_width, half_depth = _footprint(obj3d, obj3d.scale)

        anchors.append(PegboardAnchor(
            obj=obj,
            vbo=obj3d._vbo,  # NOQA
            material=obj3d.material,
            scale=obj3d.scale,
            smooth=getattr(obj3d, 'smooth', False),
            x=float(pos.x),
            z=float(pos.z),
            rotation=rotation,
            half_width=half_width,
            half_depth=half_depth,
        ))

    return anchors


def _bare_terminal_anchors(project: "_project.Project") -> list["PegboardAnchor"]:
    """Collect one anchor per placed terminal that is not seated in any
    cavity.

    ``cavity_id`` is nullable on ``pjt_terminals`` -- ``None`` means "bare
    terminal not seated in any housing". Seated terminals are visually
    covered by their housing and are skipped.
    """
    anchors = []

    for row in project.ptables.pjt_terminals_table:
        if row.cavity_id is not None:
            continue

        obj = row.get_object()
        if obj is None:
            continue

        obj3d = obj.obj3d
        if obj3d is None or obj3d._vbo is None:  # NOQA
            continue

        part = row.part
        model3d = None if part is None else part.model3d
        if model3d is None:
            continue

        pos = row.position3d
        rotation = _flatten.flatten_quaternion_for_model3d(
            obj3d._vbo.local_obb, model3d.forward_up)  # NOQA
        half_width, half_depth = _footprint(obj3d, obj3d.scale)

        anchors.append(PegboardAnchor(
            obj=obj,
            vbo=obj3d._vbo,  # NOQA
            material=obj3d.material,
            scale=obj3d.scale,
            smooth=getattr(obj3d, 'smooth', False),
            x=float(pos.x),
            z=float(pos.z),
            rotation=rotation,
            half_width=half_width,
            half_depth=half_depth,
        ))

    return anchors


def build_anchors(project: "_project.Project") -> list["PegboardAnchor"]:
    """Build the full Phase-1 static peg board anchor list for *project*.

    Walks housings, splices, transitions, and bare (not cavity-seated)
    terminals. Any row whose live 3D scene object hasn't been built yet
    (``get_object()`` returns ``None``) is skipped defensively -- this can
    legitimately happen while a project is still loading.

    :param project: The currently open project (``mainframe.project``).
    :type project: :class:`harness_designer.objects.project.Project`
    :returns: One :class:`PegboardAnchor` per renderable placed part.
    :rtype: list[:class:`PegboardAnchor`]
    """
    anchors = []
    anchors.extend(_housing_anchors(project))
    anchors.extend(_splice_anchors(project))
    anchors.extend(_transition_anchors(project))
    anchors.extend(_bare_terminal_anchors(project))

    return anchors
