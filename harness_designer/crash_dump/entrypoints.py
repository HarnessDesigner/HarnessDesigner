"""Public, app-facing entry points.

``run.py``'s fatal-exception hook and ``canvas_base.py``'s per-object
render-failure handler call straight into ``dump_state_on_fatal_exception``
and ``dump_render_failure`` respectively -- the same two names the old,
single-file ``crash_dump.py`` module exposed, so neither call site needed
to change when this was promoted to a package. ``dump_visible_objects`` is
a third, newer entry point: a deliberate, user-triggered (keyboard
shortcut) snapshot of whatever a canvas actually drew last frame, rather
than something tied to an error at all.

Both are deliberately exception-safe themselves, independent of whatever
the call site does: a broken diagnostic must never mask -- or, worse,
propagate past -- the real error it was trying to describe. That matters
most for the fatal path, which runs moments before the process aborts
outright, but ``canvas_base.py``'s render-failure call sites don't all
wrap this call in their own try/except either, so the guard has to live
here.
"""
from __future__ import annotations

import os
import time
import traceback
from datetime import datetime

from .walker import dump_to_html

FATAL_SEVERITY = 1
RENDER_FAILURE_SEVERITY = 2
MANUAL_DUMP_SEVERITY = 1

# A render failure can repeat every frame once something is persistently
# broken about one object -- this is the narrow, rate-limited dump that
# case needs (the fatal dump is one-shot by nature: the process is about
# to abort). Keyed by id(view_obj), which is fine for a cooldown cache
# specifically: the rare case of an id being reused by an unrelated object
# during the cooldown window just costs one skipped dump, not a
# correctness problem the way reusing ids *within* a single dump's own
# $ref dedup would be.
_RENDER_FAILURE_COOLDOWN_SECONDS = 30.0
_render_failure_last_dump: dict[int, float] = {}


def dump_state_on_fatal_exception(exc_type, exc_value, exc_tb) -> None:
    try:
        _dump_state_on_fatal_exception(exc_type, exc_value, exc_tb)
    except Exception:  # NOQA -- a broken diagnostic must never mask the real exception
        pass


def dump_render_failure(view_obj, exc: Exception) -> None:
    try:
        _dump_render_failure(view_obj, exc)
    except Exception:  # NOQA -- a broken diagnostic must never mask the real exception
        pass


def dump_visible_objects(view_objects, canvas_label: str) -> None:
    try:
        _dump_visible_objects(view_objects, canvas_label)
    except Exception:  # NOQA -- a broken diagnostic must never mask anything
        pass


def _dump_state_on_fatal_exception(exc_type, exc_value, exc_tb) -> None:
    import harness_designer as _hd

    roots = [root for root in (_hd._app, _hd._mainframe) if root is not None]
    if not roots:
        return

    stamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    path = os.path.join(_log_dir(), f'crash_dump_{stamp}.html')
    formatted_traceback = ''.join(traceback.format_exception(exc_type, exc_value, exc_tb))
    _dump_with_write_suppression(lambda: dump_to_html(
        roots,
        trigger_severity=FATAL_SEVERITY,
        dump_kind='fatal',
        path=path,
        exception={'type': exc_type.__name__, 'message': str(exc_value), 'traceback': formatted_traceback},
    ))


def _dump_render_failure(view_obj, exc: Exception) -> None:
    now = time.monotonic()
    obj_id = id(view_obj)
    last_dump_time = _render_failure_last_dump.get(obj_id)
    if last_dump_time is not None and (now - last_dump_time) < _RENDER_FAILURE_COOLDOWN_SECONDS:
        return
    _render_failure_last_dump[obj_id] = now
    _prune_stale_cooldowns(now)

    stamp = datetime.now().strftime('%Y%m%d_%H%M%S_%f')
    path = os.path.join(_log_dir(), f'render_failure_{type(view_obj).__name__}_{stamp}.html')
    formatted_traceback = ''.join(traceback.format_exception(type(exc), exc, exc.__traceback__))
    _dump_with_write_suppression(lambda: dump_to_html(
        [view_obj],
        trigger_severity=RENDER_FAILURE_SEVERITY,
        dump_kind='render_failure',
        path=path,
        exception={'type': type(exc).__name__, 'message': str(exc), 'traceback': formatted_traceback},
    ))


def _dump_visible_objects(view_objects, canvas_label: str) -> None:
    if not view_objects:
        return

    stamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    path = os.path.join(_log_dir(), f'manual_dump_{canvas_label}_{stamp}.html')
    _dump_with_write_suppression(lambda: dump_to_html(
        list(view_objects),
        trigger_severity=MANUAL_DUMP_SEVERITY,
        dump_kind='manual',
        path=path,
    ))


def _prune_stale_cooldowns(now: float) -> None:
    stale_ids = [
        obj_id for obj_id, last_dump_time in _render_failure_last_dump.items()
        if (now - last_dump_time) >= _RENDER_FAILURE_COOLDOWN_SECONDS
    ]
    for obj_id in stale_ids:
        del _render_failure_last_dump[obj_id]


def _dump_with_write_suppression(dump_callable) -> None:
    """Run ``dump_callable`` (a zero-arg closure that performs the actual
    walk/write) inside the current project's write-suppressing gesture,
    if a project is actually open -- some lazily-created-on-read columns
    (e.g. ``PJTSplice.branch_position3d_id``) insert a database row as a
    side effect of a plain attribute read, which a passive diagnostic
    dump must never do for real. ``gesture()`` nests safely (only the
    outermost exit commits/flushes), so this is safe even if a drag/
    rotate gesture happens to already be open when a render failure
    fires mid-gesture.
    """
    project = _current_project()
    if project is None:
        dump_callable()
        return

    with project.gesture():
        dump_callable()


def _current_project():
    try:
        import harness_designer as _hd
    except Exception:
        return None

    mainframe = getattr(_hd, '_mainframe', None)
    if mainframe is None:
        return None

    # The backing field, never the public `project` property -- that
    # property lazily OPENS a project (a UI-interactive flow) as a side
    # effect of merely being read when none is open yet, which a crash
    # dump must never trigger.
    return getattr(mainframe, '_project', None)


def _log_dir() -> str:
    from ..utils import paths as _paths

    log_dir = os.path.join(_paths.get_appdata(), 'log')
    os.makedirs(log_dir, exist_ok=True)
    return log_dir
