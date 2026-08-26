# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

"""Terminal-placement geometry helpers, reused by
``objects.objects_3d.terminal.Terminal.start_add``/``add_handlers.
editor_3d.terminal``/``add_handlers.editor_schematic.terminal`` (see
those modules for the actual interactive placement sessions, which
replaced this module's own former ``AddTerminalHandler``) and by
``objects.objects_3d.terminal.Terminal._set_model`` (repositioning once
a first-time model download completes -- see :func:`reposition_from_model`
at the bottom of this module).
"""

import numpy as np

from ..geometry import point as _point
from .. import check_types as _check_types

@_check_types.do
def _terminal_extent(part, pjt_cavity) -> tuple[float, float]:
    """
    Return (front_z, back_z): the canonical-frame Z distance from *part*'s
    own local origin (position3d, where a placed terminal's position3d
    ends up) to its front (mating-side, +Z) and back (wire-side, -Z) faces.

    Not assumed symmetric -- front_z isn't necessarily -back_z. A real
    converted model's own local origin isn't guaranteed to sit exactly at
    its geometric center (wherever the original CAD file's author put it),
    so front/back need to be read directly off the OBB rather than derived
    from a single "length" magnitude split down the middle.

    Prefers the converted 3D model's own measured extents. model3d.obb is
    the model's raw, un-rotated, un-translated OBB -- Base3D._set_model()
    bakes model3d.angle3d/position3d into obb/aabb (and the packed vertex
    data) before ever using them for anything, so this mirrors that exact
    step. Once baked, canonical +Z is always forward by definition (what
    the one-time PartOrientationDialog rotation exists to guarantee), so
    no per-part axis lookup (forward_up) is needed here at all. Safe to
    mutate obb in place -- model3d.obb's getter returns a fresh array on
    every access, never a cached/shared one.

    When no model is available yet (still downloading/unassigned): falls
    back to a symmetric split of the terminal part's own recorded length
    (Terminal.effective_size, half the cavity's length when the terminal
    itself is missing any of its own three measurements) -- the best
    guess available without real geometry.
    """

    model3d = part.model3d
    if model3d is not None and model3d.obb is not None:
        obb = model3d.obb.astype(np.float64)
        obb @= model3d.angle3d
        obb += model3d.position3d

        z = obb[:, 2]
        return float(z.max()), float(z.min())

    if pjt_cavity is not None:
        _, _, length = part.effective_size(pjt_cavity.part)
    else:
        length = float(part.length)

    return length / 2.0, -length / 2.0


@_check_types.do
def _female_terminal_position(part, pjt_cavity):
    """
    Return the female-terminal position: the FRONT of the terminal pin
    (not its center) lands on the cavity's front (mating-side) face.

    A terminal is a rigid child of its cavity, exactly like a cavity is
    a rigid child of its housing (see database.project_db.pjt_cavity.
    PJTCavitiesTable.insert, whose own position3d = c_position3d @
    h_angle3d + h_position3d -- rotate the LOCAL offset by the PARENT's
    angle, then translate by the PARENT's own already-correct world
    position; never re-derive the parent's own position from further up
    the chain). This mirrors that exactly one level down: our local Z
    offset, rotated by the cavity's own world angle3d, translated by the
    cavity's own world position3d. Confirmed the right parent to build
    from (not the housing) by PJTHousing._update_angle3d, which moves a
    cavity's terminal rigidly along with it on every housing move/rotate
    and sets the terminal's own angle3d to exactly mirror the cavity's --
    i.e. the rest of the system already treats "terminal rides rigidly
    with its cavity" as the invariant; this is just the initial-placement
    formula catching up to match it.

    Sign note: this is the CAVITY's own local Z, not the terminal
    part-model convention -- Cavity3D.apply_analysis builds a cavity's
    OBB with local +Z along the terminal surface's own outward normal
    (corners 4-7, the terminal/forward face, sit at +length/2), so a
    cavity's front (mating) face is +cav_length/2, its back (wire-side)
    face -cav_length/2. A terminal, once given the cavity's own angle3d
    (set_angle_from_cavity), shares that exact same +Z-is-forward frame.
    """

    cav_length = float(pjt_cavity.part.length)
    front_z, _ = _terminal_extent(part, pjt_cavity)

    z_offset = cav_length / 2.0 - front_z

    pos = _point.Point(0.0, 0.0, z_offset)
    pos @= pjt_cavity.angle3d
    pos += pjt_cavity.position3d

    return pos.as_float


@_check_types.do
def _male_terminal_position(part, pjt_cavity):
    """
    Return the male-terminal position: the point 1/3 of the pin's own
    length back from its front face lands on the cavity's front
    (mating-side) face. See _female_terminal_position.
    """

    cav_length = float(pjt_cavity.part.length)
    front_z, back_z = _terminal_extent(part, pjt_cavity)
    length = front_z - back_z

    z_offset = cav_length / 2.0 - front_z + length / 3.0

    pos = _point.Point(0.0, 0.0, z_offset)
    pos @= pjt_cavity.angle3d
    pos += pjt_cavity.position3d

    return pos.as_float


@_check_types.do
def _resolve_is_male(part, g_housing=None) -> bool:
    """
    Return True when *part* should be positioned/treated as male.

    Priority: the terminal part's own gender, then *g_housing*'s gender
    (when supplied), then default to male so a missing gender is
    visually obvious rather than silently guessed.
    """

    term_gender = (part.gender.name or '').strip().lower()
    if term_gender in ('male', 'female'):
        return term_gender == 'male'

    if g_housing is not None:
        housing_gender = (g_housing.gender.name or '').strip().lower()
        if housing_gender in ('male', 'female'):
            return housing_gender == 'male'

    return True


@_check_types.do
def reposition_from_model(pjt_terminal) -> None:
    """
    Recompute *pjt_terminal*'s position3d now that its 3D model has
    finished converting for the first time.

    The initial placement (objects.objects_3d.terminal.Terminal.start_add)
    fell back to Terminal.effective_size / the terminal's own catalog dimensions
    since no model was available yet, which can be a meaningfully
    different size than the real, converted model -- see
    objects.objects_3d.terminal.Terminal._set_model, which calls this
    only the first time a given terminal's model finishes downloading
    (never on a later reload, where the model is already cached and the
    position is already correct/possibly user-adjusted since).

    No-op for a terminal not yet placed in a cavity (floating preview) --
    nothing to reposition relative to yet.
    """

    pjt_cavity = pjt_terminal.cavity
    if pjt_cavity is None:
        return

    part = pjt_terminal.part
    is_male = _resolve_is_male(part, pjt_cavity.housing.part)

    if is_male:
        x, y, z = _male_terminal_position(part, pjt_cavity)
    else:
        x, y, z = _female_terminal_position(part, pjt_cavity)

    position = pjt_terminal.position3d
    with position:
        position.x = x
        position.y = y
        position.z = z

