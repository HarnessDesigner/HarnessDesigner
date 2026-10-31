# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

"""Peg-board model of ONE wire routed through ONE bundle, as plain geometry.

No database, no UI, no project imports -- numbers in, numbers out -- so every
rule here can be run and checked offline (``diagnostics/bundle_wire_check.py``).

The assembly (all positions are peg-board ``(x, z)``)::

    A ~~~~ G_a --stub-- E_a ======= bundle ======= E_b --stub-- G_b ~~~~ B

* ``E_a``/``E_b`` -- the bundle's two ends (:class:`BundleModel`). The bundle is
  a rope of fixed ``length``; its ends are ``free`` (movable) or anchored.
* ``G_a``/``G_b`` -- the wire's guard stubs. A stub has a fixed length
  (``guard_distance``) and leaves its bundle end along that end's outward
  direction. A stub has NO position of its own: it is always derived from its
  bundle end, so it can only move when the bundle end moves.
* ``A``/``B`` -- the wire's two ends (:class:`WireModel`); ``free`` ones can be
  pulled, anchored ones (a terminal) cannot.
* The wire's *free length* ``F`` is what is left of the wire beyond the stubs
  and the bundle. It is shared by the two stretches ``A..G_a`` and ``G_b..B``;
  how it is split between them is the wire's ``split`` (slack on either side).

:meth:`Assembly.plan` answers "what has to move, and in what order" when one
wire end (``held``, the one the user is dragging) is already at its target, or
when nothing is held (a 3D change, a bundle drag):

1. **slide** -- a stretch that needs more length takes the slack of the other
   one (the wire slides through the bundle). Nothing moves.
2. **pull the opposite end** -- no slack left: the opposite wire end is pulled
   in toward its stub, up to the stub's tip.
3. **pull the bundle** -- the opposite end is at its stub tip: the bundle (and
   the stub and wire end riding on it) is dragged toward the held end. The
   bundle's other end follows once its own length is taut.
4. **clamp the held end** -- nothing is left to move: the held end is held back
   at the limit.

The result is a :class:`MovePlan` listing each step and the final positions.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field


Vec = tuple[float, float]

TOL = 1e-6


def _sub(a: Vec, b: Vec) -> Vec:
    return a[0] - b[0], a[1] - b[1]


def _add(a: Vec, b: Vec) -> Vec:
    return a[0] + b[0], a[1] + b[1]


def _scale(a: Vec, k: float) -> Vec:
    return a[0] * k, a[1] * k


def dist(a: Vec, b: Vec) -> float:
    return math.hypot(a[0] - b[0], a[1] - b[1])


def _unit(a: Vec) -> Vec:
    length = math.hypot(a[0], a[1])
    if length < 1e-12:
        return 0.0, 0.0
    return a[0] / length, a[1] / length


def _toward(frm: Vec, target: Vec, amount: float) -> Vec:
    """*frm* moved *amount* straight toward *target* (never past it)."""
    d = dist(frm, target)
    if d < 1e-12:
        return frm
    return _add(frm, _scale(_unit(_sub(target, frm)), min(amount, d)))


@dataclass
class BundleModel:
    """The bundle: two ends, a fixed length, an outward direction at each end
    and the guard distance every stub leaving it has."""

    ends: list[Vec]
    length: float
    free: tuple[bool, bool]
    directions: tuple[Vec, Vec]
    guard_distance: float | tuple[float, float]  # one value, or one per end (0 = no stub)

    def guard(self, end_index: int, ends: list[Vec] | None = None) -> Vec:
        """The guard stub tip of bundle end *end_index* (derived, never stored)."""
        e = (ends or self.ends)[end_index]
        g = self.guard_distance
        if isinstance(g, tuple):
            g = g[end_index]
        return _add(e, _scale(self.directions[end_index], g))


@dataclass
class WireModel:
    """The wire: its two ends, which bundle end its ``a`` side leaves from,
    the free length shared by its two stretches and the current split."""

    a: Vec
    b: Vec
    a_free: bool
    b_free: bool
    free_length: float
    split: tuple[float, float]
    a_end: int = 0  # bundle end index behind A's stub; B uses the other one


@dataclass
class Step:
    kind: str       # 'slide' | 'pull_end' | 'pull_bundle' | 'clamp_held'
    who: str        # 'a' | 'b' | 'bundle'
    amount: float
    note: str = ''


@dataclass
class MovePlan:
    feasible: bool
    steps: list[Step] = field(default_factory=list)
    a: Vec = (0.0, 0.0)
    b: Vec = (0.0, 0.0)
    ends: list[Vec] = field(default_factory=list)
    guards: tuple[Vec, Vec] = ((0.0, 0.0), (0.0, 0.0))   # (G_a, G_b)
    split: tuple[float, float] = (0.0, 0.0)              # (A stretch, B stretch)
    reason: str = ''

    def describe(self) -> str:
        if not self.feasible:
            return f'INFEASIBLE ({self.reason})'
        return ' -> '.join(f'{s.kind}[{s.who}]{s.amount:.2f}' for s in self.steps) or 'nothing moves'


class Assembly:
    """One wire through one bundle; :meth:`plan` is the only entry point."""

    def __init__(self, wire: WireModel, bundle: BundleModel):
        self.wire = wire
        self.bundle = bundle

    # ------------------------------------------------------------------

    def _allocate(self, ds: tuple[float, float]) -> tuple[tuple[float, float], float]:
        """Share the free length between the two stretches: one that has to
        stretch takes the slack of the other (the wire slides through the
        bundle); whatever cannot be taken is the returned deficit."""
        current = self.wire.split
        alloc = [max(current[0], ds[0]), max(current[1], ds[1])]
        excess = sum(alloc) - self.wire.free_length

        if excess > TOL:
            slack = [
                (i, alloc[i] - ds[i]) for i in (0, 1)
                if ds[i] <= current[i] and alloc[i] - ds[i] > TOL]
            avail = sum(s for _, s in slack)
            if avail > 0.0:
                take = min(excess, avail)
                for i, s in slack:
                    alloc[i] -= take * s / avail
                excess -= take

        return (alloc[0], alloc[1]), max(excess, 0.0)

    # ------------------------------------------------------------------

    def plan(self, held: str | None = None) -> MovePlan:
        """What has to move so the assembly is valid again.

        :param held: ``'a'``/``'b'`` -- the wire end the user is dragging (it
            is already at its target and is moved back only as a last
            resort); ``None`` -- no wire end is held (3D change, bundle drag).
        """
        w, bd = self.wire, self.bundle
        end_of = {'a': w.a_end, 'b': 1 - w.a_end}
        free = {'a': w.a_free, 'b': w.b_free}
        pos = {'a': w.a, 'b': w.b}
        ends = list(bd.ends)
        steps: list[Step] = []

        def guard(side: str) -> Vec:
            return bd.guard(end_of[side], ends)

        def ds() -> tuple[float, float]:
            return dist(pos['a'], guard('a')), dist(pos['b'], guard('b'))

        d = ds()
        alloc, deficit = self._allocate(d)

        if deficit <= TOL:
            if alloc != tuple(w.split):
                steps.append(Step('slide', 'bundle', abs(alloc[0] - w.split[0]), 'slack moved through the bundle'))
            return self._result(True, steps, pos, ends, alloc)

        # ---- slack is used up: something has to give ---------------------
        if held is None:
            for side in ('a', 'b'):
                if deficit <= TOL or not free[side]:
                    continue
                take = min(deficit, dist(pos[side], guard(side)))
                if take > TOL:
                    pos[side] = _toward(pos[side], guard(side), take)
                    steps.append(Step('pull_end', side, take))
                    alloc, deficit = self._allocate(ds())

            if deficit > TOL:
                return MovePlan(False, steps, reason='no free wire end can absorb the shortfall')
            return self._result(True, steps, pos, ends, alloc)

        opp = 'b' if held == 'a' else 'a'

        # 2. pull the opposite end in, up to its stub tip
        if free[opp]:
            take = min(deficit, dist(pos[opp], guard(opp)))
            if take > TOL:
                pos[opp] = _toward(pos[opp], guard(opp), take)
                steps.append(Step('pull_end', opp, take, 'opposite end pulled through the bundle'))
                alloc, deficit = self._allocate(ds())

        if deficit <= TOL:
            return self._result(True, steps, pos, ends, alloc)

        # 3. drag the bundle toward the held end (the opposite end rides on its stub)
        eh = end_of[held]
        eo = 1 - eh
        heading = _unit(_sub(pos[held], guard(held)))

        def pulled(x: float) -> list[Vec] | None:
            new_ends = list(ends)
            new_ends[eh] = _add(ends[eh], _scale(heading, x))
            if dist(new_ends[eh], ends[eo]) > bd.length + TOL:
                if not bd.free[eo]:
                    return None
                new_ends[eo] = _toward(new_ends[eh], ends[eo], bd.length)
            return new_ends

        def shortfall(x: float) -> float | None:
            """How far over the free length the wire would be after pulling
            the bundle by *x* (negative = fits); None if the bundle cannot."""
            new_ends = pulled(x)
            if new_ends is None:
                return None
            g_held = bd.guard(eh, new_ends)
            g_opp = bd.guard(eo, new_ends)
            o_pos = g_opp if free[opp] else pos[opp]
            return dist(pos[held], g_held) + dist(o_pos, g_opp) - w.free_length

        # largest pull the bundle itself allows (its far end follows if free);
        # an anchored held-side bundle end cannot be pulled at all
        x_max = dist(pos[held], guard(held)) if bd.free[eh] else 0.0
        if pulled(x_max) is None:
            lo_x, hi_x = 0.0, x_max
            for _ in range(60):
                mid = (lo_x + hi_x) / 2.0
                if pulled(mid) is None:
                    hi_x = mid
                else:
                    lo_x = mid
            x_max = lo_x

        # smallest pull that makes the wire fit; if even x_max is not enough,
        # pull that far and clamp the held end below
        s_max = shortfall(x_max)
        if s_max is None or s_max > TOL:
            s_zero = shortfall(0.0)
            best = x_max if (s_max is not None and s_zero is not None and s_max < s_zero - TOL) else 0.0
        else:
            lo_x, hi_x = 0.0, x_max
            for _ in range(60):
                mid = (lo_x + hi_x) / 2.0
                s_mid = shortfall(mid)
                if s_mid is not None and s_mid <= TOL:
                    hi_x = mid
                else:
                    lo_x = mid
            best = hi_x

        new_ends = pulled(best)
        if new_ends is not None and best > 1e-4:
            ends = new_ends
            steps.append(Step('pull_bundle', 'bundle', best, 'bundle dragged toward the held end'))
            if free[opp]:
                pos[opp] = guard(opp)

        # 4. still too long: clamp the held end back at the limit
        d = ds()
        alloc, deficit = self._allocate(d)
        if deficit > TOL and not free[held]:
            return MovePlan(False, steps, reason='held end cannot be moved back')

        if deficit > TOL:
            g_held = guard(held)
            limit = max(w.free_length - dist(pos[opp], guard(opp)), 0.0)
            clamped = _add(g_held, _scale(_unit(_sub(pos[held], g_held)), limit))
            steps.append(Step('clamp_held', held, dist(pos[held], clamped), 'nothing left to pull'))
            pos[held] = clamped
            alloc, deficit = self._allocate(ds())

        if deficit > TOL:
            return MovePlan(False, steps, reason='could not satisfy the free length')

        return self._result(True, steps, pos, ends, alloc)

    # ------------------------------------------------------------------

    def _result(self, feasible: bool, steps: list[Step], pos: dict, ends: list[Vec],
                alloc: tuple[float, float]) -> MovePlan:
        bd, w = self.bundle, self.wire
        return MovePlan(
            feasible, steps, pos['a'], pos['b'], ends,
            (bd.guard(w.a_end, ends), bd.guard(1 - w.a_end, ends)), alloc)
