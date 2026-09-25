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

from typing import TYPE_CHECKING, Union as _Union

import os as _os
import re as _re
import statistics as _statistics

import numpy as np

from ..geometry import point as _point
from .. import check_types as _check_types


if TYPE_CHECKING:
    from .. import ui as _ui
    from ..database.global_db import terminal as _global_terminal
    from ..database.global_db import housing as _global_housing
    from ..database.global_db import model3d as _global_model3d
    from ..database.project_db import pjt_cavity as _pjt_cavity
    from ..database.project_db import pjt_terminal as _pjt_terminal


_BLADE_SIZE_TOKEN_RE = _re.compile(r'\d+\.\d+')

# Same directory objects.objects_3d.terminal.Terminal.__init__ builds its
# own _GENERIC_MODEL_PATH from (one level up here, since this module lives
# directly under harness_designer/ rather than harness_designer/objects/
# objects_3d/) -- used to recognize a shared generic-model stand-in so its
# own OBB is never mistaken for a specific terminal's real measured size.
_GENERIC_MODEL_PATH = _os.path.abspath(_os.path.join(_os.path.dirname(__file__), '..', 'models'))


@_check_types.do
def _terminal_extent(part: "_global_terminal.Terminal",
                      pjt_cavity: _Union["_pjt_cavity.PJTCavity", None]) -> tuple[float, float]:
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
def _female_terminal_position(part: "_global_terminal.Terminal",
                               pjt_cavity: "_pjt_cavity.PJTCavity") -> tuple[float, float, float]:
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
def _male_terminal_position(part: "_global_terminal.Terminal",
                             pjt_cavity: "_pjt_cavity.PJTCavity") -> tuple[float, float, float]:
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
def _female_terminal_position_pegboard(part: "_global_terminal.Terminal",
                                        pjt_cavity: "_pjt_cavity.PJTCavity") -> tuple[float, float, float]:
    """
    Peg-board equivalent of :func:`_female_terminal_position` -- same
    local Z offset (``_terminal_extent`` is a pure measurement of the
    terminal part's own canonical-frame geometry, unrelated to which
    view it's being placed in, so it's reused as-is), rotated/translated
    by the cavity's own ``angle_pegboard``/``position_pegboard`` instead
    of ``angle3d``/``position3d``.
    """

    cav_length = float(pjt_cavity.part.length)
    front_z, _ = _terminal_extent(part, pjt_cavity)

    z_offset = cav_length / 2.0 - front_z

    pos = _point.Point(0.0, 0.0, z_offset)
    pos @= pjt_cavity.angle_pegboard
    pos += pjt_cavity.position_pegboard

    return pos.as_float


@_check_types.do
def _male_terminal_position_pegboard(part: "_global_terminal.Terminal",
                                      pjt_cavity: "_pjt_cavity.PJTCavity") -> tuple[float, float, float]:
    """Peg-board equivalent of :func:`_male_terminal_position` -- see
    :func:`_female_terminal_position_pegboard`.
    """

    cav_length = float(pjt_cavity.part.length)
    front_z, back_z = _terminal_extent(part, pjt_cavity)
    length = front_z - back_z

    z_offset = cav_length / 2.0 - front_z + length / 3.0

    pos = _point.Point(0.0, 0.0, z_offset)
    pos @= pjt_cavity.angle_pegboard
    pos += pjt_cavity.position_pegboard

    return pos.as_float


@_check_types.do
def free_end_direction(end_point: _point.Point, neighbor_point: _point.Point) -> tuple[float, float, float]:
    """Unit vector from *neighbor_point* (the next point in along a wire's
    path) toward *end_point* (the wire's free end) -- the way a terminal
    crimped onto that end faces (its +Z/front points away from the wire).
    Falls back to +Z when the two coincide.
    """
    ex, ey, ez = end_point.as_float
    nx, ny, nz = neighbor_point.as_float

    dx, dy, dz = ex - nx, ey - ny, ez - nz
    length = float(np.linalg.norm((dx, dy, dz)))

    if length < 1e-8:
        return 0.0, 0.0, 1.0

    return dx / length, dy / length, dz / length


@_check_types.do
def free_end_position(part: "_global_terminal.Terminal", end_point: _point.Point,
                      direction: tuple[float, float, float]) -> tuple[float, float, float]:
    """
    Return the position for a terminal that is not in a cavity, crimped
    onto a wire's free end: its back (wire-side) face center lands on
    *end_point* and its front faces *direction* (see
    :func:`free_end_direction`). The terminal's own angle must already be
    the rotation of +Z onto *direction*.
    """
    _, back_z = _terminal_extent(part, None)

    x, y, z = end_point.as_float
    dx, dy, dz = direction

    return x - dx * back_z, y - dy * back_z, z - dz * back_z


@_check_types.do
def _resolve_is_male(part: "_global_terminal.Terminal",
                      g_housing: _Union["_global_housing.Housing", None] = None) -> bool:
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
def reposition_from_model(pjt_terminal: "_pjt_terminal.PJTTerminal") -> None:
    """
    Recompute *pjt_terminal*'s position3d and position_pegboard now that
    its 3D model is available (finished converting for the first time, or
    was only just assigned by ``objects.objects_3d.terminal.Terminal.
    __init__`` after the initial placement was already computed).

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
    part = pjt_terminal.part

    if pjt_cavity is None:
        # Crimped onto a free wire end (see free_end_position): keep the
        # back face where it already is (the terminal's own wire_position
        # points, which don't move with position3d/position_pegboard) and
        # re-derive where the body sits from the real model's extent.
        _, back_z = _terminal_extent(part, None)

        if pjt_terminal.wire_position3d_id_raw is not None:
            pos = _point.Point(0.0, 0.0, -back_z)
            pos @= pjt_terminal.angle3d
            pos += pjt_terminal.wire_position3d

            position = pjt_terminal.position3d
            position += pos - position

        if pjt_terminal.wire_position_pegboard_id_raw is not None:
            pos = _point.Point(0.0, 0.0, -back_z)
            pos @= pjt_terminal.angle_pegboard
            pos += pjt_terminal.wire_position_pegboard

            position = pjt_terminal.position_pegboard
            position += pos - position

        return

    is_male = _resolve_is_male(part, pjt_cavity.housing.part)

    if is_male:
        x, y, z = _male_terminal_position(part, pjt_cavity)
        px, py, pz = _male_terminal_position_pegboard(part, pjt_cavity)
    else:
        x, y, z = _female_terminal_position(part, pjt_cavity)
        px, py, pz = _female_terminal_position_pegboard(part, pjt_cavity)

    position = pjt_terminal.position3d
    with position:
        position.x = x
        position.y = y
        position.z = z

    pegboard_position = pjt_terminal.position_pegboard
    with pegboard_position:
        pegboard_position.x = px
        pegboard_position.y = py
        pegboard_position.z = pz


@_check_types.do
def _is_generic_model(model3d: "_global_model3d.Model3D") -> bool:
    """True when *model3d* is one of the shared generic stand-ins
    ``objects.objects_3d.terminal.Terminal.__init__`` assigns to a
    terminal missing its own real manufacturer model (e.g. ``'generic
    terminal male 2.8.stp'``, ``'deutsch terminal male solid.stl'``) --
    NOT a specific part's own real model.

    That assignment writes straight to the part's own ``model3d_id``,
    the same as a real per-part model download would -- so a later
    ``part.model3d`` lookup can't otherwise tell the two apart. It
    matters here because ``Models3DTable.insert`` get-or-creates by
    file path (see its own docstring): every terminal that ever fell
    back to, say, ``'generic terminal male 2.8.stp'`` shares the
    EXACT SAME ``Model3D`` row and therefore the exact same measured
    OBB/size -- treating that as this specific terminal's own real
    dimensions would be wrong, not just imprecise; it's sized however
    the generic STP file's own author happened to model it, unrelated
    to this part's actual length.
    """
    path = model3d.path
    if not path:
        return False

    return _os.path.dirname(_os.path.abspath(path)) == _GENERIC_MODEL_PATH


@_check_types.do
def _extract_blade_size_from_description(description: str | None) -> float | None:
    """Best-guess blade_size parsed from *description*'s own leading
    text, for a terminal catalog row that was never given one directly.

    A decimal number (must contain a ``.`` -- a bare integer is never
    genuinely a blade size in this catalog, see below) found in the
    FIRST TWO whitespace/comma/paren-delimited tokens of the
    description, within a plausible blade-size range (0.1-15.0mm).

    Checked against every terminal that already has a real blade_size
    (2026-08-26, by manufacturer): Aptiv (927/969, 95.7%) and Bosch
    (63/64, 98.4%) lead their descriptions with the terminal size
    (e.g. ``'1.2 Female CTS Locking Lance SN Terminal...'``,
    ``'SICMA 2.8 Female Clean Body...'``) and this extracts it almost
    perfectly (the one Aptiv "miss" was 6.3 vs. a stored 6.35 -- a
    rounding difference, not a real error). TE Connectivity and AMP
    (~87% of the whole catalog) format descriptions differently
    (leading with plating/contact type, e.g. ``'Gold (Au), Pin
    Contact, ...'``) and this returns None for every single one of
    their ~1500 entries checked -- no false positives -- rather than
    guessing wrong, because their occasional bare leading numbers
    (MIL-spec "Contact Size" codes like 16/20, not physical sizes) are
    excluded by requiring a decimal point.
    """
    if not description:
        return None

    tokens = _re.split(r'[\s,()]+', description.strip())[:2]

    for token in tokens:
        if _BLADE_SIZE_TOKEN_RE.fullmatch(token):
            value = float(token)
            if 0.1 <= value <= 15.0:
                return value

    return None


@_check_types.do
def estimate_dimensions(mainframe: "_ui.MainFrame",
                         part: "_global_terminal.Terminal") -> tuple[dict, dict]:
    """Return ``(estimates, suggested)`` for *part* (a catalog terminal
    missing one or more of its own recorded dimensions) -- for the
    placeholder/analog shape shown until a real or generic 3D model
    replaces it (objects.objects_3d.terminal.Terminal.__init__/
    _set_model); nothing downstream ever depends on these for real
    geometry.

    ``estimates`` (``ui.dialogs.dimensions_dialog.ensure_dimensions``'s
    own *estimates* param) comes from data already trusted -- the
    terminal's own real, already-converted 3D model when one is
    available; failing that, a recorded blade_size, or a cavity
    already in the project this terminal fits -- and is applied
    silently, without ever needing the user to look at it.

    ``suggested`` is a value :func:`_extract_blade_size_from_description`
    only *guessed* at (blade_size was never actually recorded) -- it
    still pre-fills the width/height fields, but the dialog is always
    shown for it rather than applied silently, since it's a parse of
    free-text, not a real catalog value: the user still has to look at
    it and either accept or correct it before it's trusted.

    width/height/length: the terminal's own real 3D model, when one is
    already converted (``model3d.obb`` populated -- see
    database.global_db.model3d.Model3D.size, which reports ``(0, 0, 0)``
    for a model that hasn't finished converting yet) takes priority
    over everything else here -- actual measured geometry beats any of
    the guesses below. A model still mid-conversion (or none assigned
    at all) is indistinguishable from "not available yet" here on
    purpose: this only ever needs to run once, synchronously, at
    add-time -- Terminal._set_model's own existing correction (this
    same model.size, applied once the async conversion callback fires)
    is what fixes things up for a terminal added before its model had
    finished converting.

    Width/height otherwise fall back to the terminal's own blade_size
    when recorded (checked against the catalog directly, 2026-08-26: of
    201 terminals with a complete blade_size/length/width/height, 192
    (95.5%) already have width == height == blade_size exactly -- not a
    physical law, just the existing convention for how this catalog's
    own terminals get filled in when real dimensions aren't otherwise
    known, so matching it is at least consistent with the rest of the
    data), and beyond that to a *suggested* (not silently trusted) value
    from :func:`_extract_blade_size_from_description`.

    Length otherwise falls back to 3/4 of the length of a cavity,
    already in the current project, that this terminal is compatible
    with (see database.global_db.cavity.Cavity.compat_terminals) --
    median across every such cavity found, in case more than one
    housing in the project takes this terminal. Deliberately NOT
    derived from any catalog-wide length/blade_size ratio -- checked
    the same 201-row sample and it spans two orders of magnitude
    (length/blade_size from 2.0 to 32.2 even restricted to the 9 rows
    where width/height were genuinely measured, not just copied from
    blade_size), so no single ratio is trustworthy. A cavity this
    terminal will actually sit in is real context instead of a guess,
    and length only ever drives the placeholder's own display size,
    never anything functional.
    """
    estimates = {}
    suggested = {}

    model3d = part.model3d
    if model3d is not None and not _is_generic_model(model3d):
        model_width, model_height, model_length = model3d.size
        if model_width > 0.0 and model_height > 0.0 and model_length > 0.0:
            estimates['width'] = model_width
            estimates['height'] = model_height
            estimates['length'] = model_length
            return estimates, suggested

    blade_size = part.blade_size
    if blade_size:
        estimates['width'] = blade_size
        estimates['height'] = blade_size
    elif part.width <= 0.0 or part.height <= 0.0:
        guessed_blade_size = _extract_blade_size_from_description(part.description)
        if guessed_blade_size:
            suggested['width'] = guessed_blade_size
            suggested['height'] = guessed_blade_size

    part_number = part.part_number
    lengths = []

    for cavity in mainframe.project.cavities:
        g_cavity = cavity.db_obj.part
        if any(t.part_number == part_number for t in g_cavity.compat_terminals):
            lengths.append(float(g_cavity.length) * 0.75)

    if lengths:
        estimates['length'] = _statistics.median(lengths)

    return estimates, suggested

