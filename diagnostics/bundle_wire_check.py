# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

"""Offline check of ``handlers/bundle_wire_model.py`` (no app, no GUI).

    python diagnostics/bundle_wire_check.py

Runs the named scenarios (printing each :class:`MovePlan`) and then a few
thousand random assemblies, asserting the invariants every feasible plan must
keep: the bundle never gets longer than its length, a stub keeps its length and
its bundle end's direction, the wire never ends up longer than its free length,
and a held end only moves in the final clamp step.
"""

import importlib.util
import math
import os
import random
import sys

_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'harness_designer', 'handlers',
                     'bundle_wire_model.py')
_spec = importlib.util.spec_from_file_location('bundle_wire_model', _PATH)
m = importlib.util.module_from_spec(_spec)
sys.modules['bundle_wire_model'] = m  # dataclasses needs the module registered
_spec.loader.exec_module(m)

TOL = 1e-4


def build(a, b, a_free=True, b_free=True, e_free=(True, True), split=(22.0, 22.0), free_length=44.0,
          bundle_length=20.0, e0=(0.0, 0.0), e1=(20.0, 0.0), g=5.0):
    bundle = m.BundleModel([e0, e1], bundle_length, e_free, ((-1.0, 0.0), (1.0, 0.0)), g)
    wire = m.WireModel(a, b, a_free, b_free, free_length, split, a_end=0)
    return m.Assembly(wire, bundle)


def check(asm, plan, held):
    """Invariants every FEASIBLE plan keeps. Returns an error string or ''."""
    if not plan.feasible:
        return ''

    w, bd = asm.wire, asm.bundle
    e0, e1 = plan.ends
    if m.dist(e0, e1) > bd.length + TOL:
        return f'bundle longer than its length: {m.dist(e0, e1):.4f} > {bd.length}'

    for i, (end, orig) in enumerate(zip(plan.ends, bd.ends)):
        if not bd.free[i] and m.dist(end, orig) > TOL:
            return f'anchored bundle end {i} moved'

    ga, gb = plan.guards
    for guard, idx in ((ga, w.a_end), (gb, 1 - w.a_end)):
        stub = (guard[0] - plan.ends[idx][0], guard[1] - plan.ends[idx][1])
        if abs(math.hypot(*stub) - bd.guard_distance) > TOL:
            return 'stub length changed'
        if m.dist((stub[0] / bd.guard_distance, stub[1] / bd.guard_distance), bd.directions[idx]) > TOL:
            return 'stub not in line with its bundle end'

    da, db = m.dist(plan.a, ga), m.dist(plan.b, gb)
    if da > plan.split[0] + TOL or db > plan.split[1] + TOL:
        return f'stretch longer than its allotted length: d=({da:.3f},{db:.3f}) split={plan.split}'
    if sum(plan.split) > w.free_length + TOL:
        return f'wire longer than its free length: {sum(plan.split):.3f} > {w.free_length}'

    if not w.a_free and m.dist(plan.a, w.a) > TOL:
        return 'anchored wire end A moved'
    if not w.b_free and m.dist(plan.b, w.b) > TOL:
        return 'anchored wire end B moved'

    if held == 'a' and m.dist(plan.a, w.a) > TOL and not any(s.kind == 'clamp_held' for s in plan.steps):
        return 'held end A moved without a clamp step'
    if held == 'b' and m.dist(plan.b, w.b) > TOL and not any(s.kind == 'clamp_held' for s in plan.steps):
        return 'held end B moved without a clamp step'
    return ''


def scenario(name, asm, held):
    plan = asm.plan(held)
    err = check(asm, plan, held)
    print(f'{name}\n    {plan.describe()}')
    if plan.feasible:
        print(f'    A={plan.a[0]:.1f},{plan.a[1]:.1f} B={plan.b[0]:.1f},{plan.b[1]:.1f} '
              f'E0={plan.ends[0][0]:.1f} E1={plan.ends[1][0]:.1f} split=({plan.split[0]:.1f},{plan.split[1]:.1f})')
    if err:
        print('    FAIL:', err)
    return plan, err


def run_scenarios():
    errors = []

    def run(name, asm, held, expect=None):
        plan, err = scenario(name, asm, held)
        if err:
            errors.append((name, err))
        if expect is not None:
            kinds = [s.kind for s in plan.steps]
            if kinds != expect:
                errors.append((name, f'expected steps {expect}, got {kinds}'))
        return plan

    # B guard tip is at x=25; A guard tip at x=-5. A 10 from its stub, B at 30 from its.
    run('1 slide: B dragged out, A has slack', build((-15.0, 0.0), (55.0, 0.0)), 'b', ['slide'])
    run('2 opposite end pulled: slack gone, B dragged further', build((-15.0, 0.0), (66.0, 0.0)), 'b', ['pull_end'])
    p = run('3 bundle dragged too: B far out, A free',
            build((-15.0, 0.0), (85.0, 0.0)), 'b', ['pull_end', 'pull_bundle'])
    if p.feasible and p.ends[0][0] <= 0.0:
        errors.append(('3', 'bundle did not move toward B'))
    run('4 A anchored (terminal): B far out', build((-15.0, 0.0), (85.0, 0.0), a_free=False), 'b')
    run('5 bundle far end anchored: B far out', build((-15.0, 0.0), (85.0, 0.0), e_free=(False, True)), 'b')
    run('6 no wire end held, wire too long for its length',
        build((-25.0, 0.0), (65.0, 0.0), free_length=44.0), None)
    run('7 nothing to do', build((-15.0, 0.0), (35.0, 0.0), split=(10.0, 10.0), free_length=44.0), 'b', [])
    run('8 held A dragged out', build((-60.0, 0.0), (35.0, 0.0)), 'a')
    return errors


def run_random(count=5000, seed=7):
    rng = random.Random(seed)
    errors = []
    infeasible = 0

    for _ in range(count):
        length = rng.uniform(5.0, 60.0)
        g = rng.uniform(1.0, 8.0)
        free_length = rng.uniform(5.0, 120.0)
        e0 = (rng.uniform(-20, 20), rng.uniform(-20, 20))
        ang = rng.uniform(0, 2 * math.pi)
        span = rng.uniform(0.0, length)
        e1 = (e0[0] + span * math.cos(ang), e0[1] + span * math.sin(ang))

        direction = _unit_pair(e0, e1)
        bundle = m.BundleModel([e0, e1], length, (rng.random() < 0.7, rng.random() < 0.7), direction, g)

        # wire ends placed so the starting state is valid; then the held one is dragged anywhere
        ga, gb = bundle.guard(0), bundle.guard(1)
        a = (ga[0] + rng.uniform(-60, 60), ga[1] + rng.uniform(-60, 60))
        b = (gb[0] + rng.uniform(-60, 60), gb[1] + rng.uniform(-60, 60))
        da, db = m.dist(a, ga), m.dist(b, gb)
        split = (max(da, rng.uniform(0, free_length)), 0.0)
        split = (min(split[0], free_length), 0.0)
        split = (split[0], max(free_length - split[0], 0.0))

        wire = m.WireModel(a, b, rng.random() < 0.7, rng.random() < 0.7, free_length, split, a_end=0)
        asm = m.Assembly(wire, bundle)
        held = rng.choice([side for side, is_free in (('a', wire.a_free), ('b', wire.b_free)) if is_free] + [None])

        plan = asm.plan(held)
        if not plan.feasible:
            infeasible += 1
            continue

        # allocation invariants only apply when the start state was itself valid
        err = check(asm, plan, held)
        if err and 'longer than its allotted' not in err and 'free length' not in err:
            errors.append(('random', err))
        elif err and da + db <= free_length + TOL and split[0] >= da - TOL and split[1] >= db - TOL:
            errors.append(('random', err))

    print(f'random: {count} cases, {infeasible} infeasible, {len(errors)} errors')
    return errors


def _unit_pair(e0, e1):
    d = (e1[0] - e0[0], e1[1] - e0[1])
    n = math.hypot(*d) or 1.0
    u = (d[0] / n, d[1] / n)
    return (-u[0], -u[1]), u


if __name__ == '__main__':
    all_errors = run_scenarios() + run_random()
    if all_errors:
        print('\nFAILURES:')
        for name, err in all_errors[:20]:
            print(f'  {name}: {err}')
        sys.exit(1)
    print('\nALL OK')
