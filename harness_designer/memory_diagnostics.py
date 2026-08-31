# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

"""Opt-in live memory diagnostics, gated entirely by
``Config.debug.memory.enabled``.

Call :func:`start` once, early in application startup (before anything
memory-heavy happens, so ``tracemalloc`` catches it) -- it is a no-op when
the config toggle is off. Call :func:`stop` on shutdown; also a no-op if
never started.

When enabled, a background thread listens on a localhost-only socket
(``multiprocessing.connection.Listener``, ``Config.debug.memory.listener_port``)
for one-word text commands and replies with a formatted text report:

======================  =============================================================
Command                 Report
======================  =============================================================
``"tracemalloc"``       Current Python (+ numpy, which registers its own
                         ``tracemalloc`` domain) allocations, grouped by the line that
                         made them, ranked by currently-live bytes.
``"objects"``           A live census of every object ``gc`` is tracking right now
                         (via :mod:`pympler`), grouped by type, ranked by total bytes.
``"growth"``            Object-count delta by type since the *previous* ``"growth"``
                         call this session (via :mod:`objgraph`) -- the fastest way to
                         see what is still climbing.
``"gpu"``               Raw vendor backends, NVIDIA and AMD side by side regardless
                         of which is actually installed (``nvapi``/``pyamd_adl``) --
                         useful for comparing what each SDK reports on its own.
                         Catches GPU memory growth (e.g. DWM/compositor) that
                         never shows up in a Python object census at all.
``"gpu_growth"``        The real pipeline (:meth:`.gpu.GPU.detect`, exactly what the
                         app itself would see) for ``vram_use`` and a few correlating
                         fields (temp, engine utilization, fan, clocks), diffed against
                         the *previous* ``"gpu_growth"`` call this session -- same idea
                         as ``"growth"``, but for GPU memory instead of Python object
                         counts. Call it more than once, with real time passed, to see
                         whether VRAM usage is actually climbing.
``"displays"``          Graphics-pipeline dump: every physical display connector,
                         what's plugged into it, link/connection status, monitor
                         name and resolution/refresh (from EDID/current mode), and
                         raw EDID byte count -- for whichever GPU vendor(s) are
                         present.
``"caches"``            Sizes of this application's own known long-lived caches (VBO
                         mesh arenas, etc) that don't show up cleanly in a generic
                         object census.
``"stacks"``            Every live thread's current Python call stack. A snapshot in
                         time, not a diff -- for "what is thread X actually doing right
                         now" (stuck in a loop, blocked on I/O, holding a local
                         reference to something huge), not for tracking growth.
``"rss"``               OS-reported process memory (working set/RSS, private/committed
                         bytes) alongside what ``tracemalloc`` can actually see. The gap
                         between them is memory none of the other commands can explain
                         at all: native buffers (Qt, OpenGL client-side staging,
                         C-extension ``malloc``s that bypass ``PyMem``). Start here when
                         a reported total is much bigger than "growth"/"tracemalloc"
                         show -- it says whether the missing memory is even in the
                         Python heap.
``"heap_snapshot"``     Like ``"tracemalloc"``, but saved to a timestamped file under
                         ``Config.debug.memory.snapshot_dir`` instead of only reported
                         in-session -- so two snapshots taken arbitrarily far apart
                         (including across a process restart) can be diffed later with
                         ``diagnostics/compare_snapshots.py``, not just "vs the last
                         call this session" the way ``"growth"`` is limited to.
======================  =============================================================

Example client call (see ``diagnostics/query_memory.py`` for a full CLI)::

    from multiprocessing.connection import Client

    with Client(('localhost', 47441), authkey=_AUTHKEY) as conn:
        conn.send('objects')
        print(conn.recv())
"""

import threading
import tracemalloc
from multiprocessing.connection import Listener

from . import config as _config
from . import logger as _logger
from . import check_types as _check_types

Config = _config.Config

# Not a security boundary (this only ever binds to localhost) -- just the
# shared secret multiprocessing.connection's handshake requires on both ends.
_AUTHKEY = b'harness_designer-memory-diagnostics'


@_check_types.do
def _format_tracemalloc(top_n: int = 30) -> str:
    if not tracemalloc.is_tracing():
        return ('tracemalloc is not running -- Config.debug.memory.enabled '
                'was False when the process started')

    snapshot = tracemalloc.take_snapshot()
    stats = snapshot.statistics('lineno')

    lines = [f'TRACEMALLOC -- top {top_n} allocation sites by current live size:']
    for stat in stats[:top_n]:
        lines.append(f'  {stat}')

    total = sum(stat.size for stat in stats)
    lines.append(f'-- total traced: {total / 1024 / 1024:.2f} MB across '
                 f'{len(stats)} distinct locations')

    return '\n'.join(lines)


@_check_types.do
def _format_objects(top_n: int = 30) -> str:
    from pympler import muppy, summary

    all_objects = muppy.get_objects()
    rows = summary.summarize(all_objects)
    rows.sort(key=lambda row: row[2], reverse=True)

    lines = [f'OBJECT CENSUS (pympler, {len(all_objects)} objects tracked) -- '
             f'top {top_n} types by total size:']
    for type_name, count, total_size in rows[:top_n]:
        lines.append(f'  {total_size / 1024 / 1024:10.2f} MB  {count:8d}x  {type_name}')

    return '\n'.join(lines)


@_check_types.do
def _format_growth(top_n: int = 30) -> str:
    import objgraph

    growth = objgraph.growth(limit=top_n)
    if not growth:
        return ('no object-count growth since the last "growth" call '
                '(or this is the first call this session)')

    lines = ['OBJECT GROWTH since the last "growth" call:']
    for type_name, count, delta in growth:
        lines.append(f'  {delta:+8d}  {count:8d}x  {type_name}')

    return '\n'.join(lines)


@_check_types.do
def _format_backend(backend, label: str) -> list[str]:
    from .gpu.backend_base import GPUBackend

    lines = [f'{label}:']
    found = False
    for name in GPUBackend.ATTRIBUTE_NAMES:
        value = getattr(backend, name, None)
        if value is not None:
            found = True
            lines.append(f'  {name}: {value}')

    if not found:
        lines.append('  no adapter found / nothing collected')

    return lines


@_check_types.do
def _format_gpu() -> str:
    from .gpu.nvidia import NvidiaBackend
    from .gpu.amd import AMDBackend

    lines = _format_backend(NvidiaBackend(), 'NVIDIA (via nvapi)')
    lines.append('')
    lines.extend(_format_backend(AMDBackend(), 'AMD (via pyamd_adl)'))

    return '\n'.join(lines)


_GPU_GROWTH_FIELDS = (
    'vram_size', 'vram_use', 'gpu_temp', 'gpu_engine', 'memory_engine',
    'fan_speed', 'fan_speed_rpm', 'soc_clock', 'memory_clock',
)

# (field values dict, time.time()) from the previous "gpu_growth" call this
# session, or None before the first call -- same idea as objgraph.growth()'s
# own internal baseline for the "growth" command, just hand-rolled here
# since nothing external tracks GPU state across calls the way objgraph
# tracks object counts.
_last_gpu_snapshot = None


def _make_gpu_detector():
    """Build the :class:`QtCore.QObject`-based helper that lets
    :func:`_format_gpu_growth` run :meth:`.gpu.GPU.detect` on the thread
    that actually owns a live GL context.

    ``GPU.detect()`` starts with ``gpu_vendor.get()``, which calls
    ``glGetString(GL_VENDOR)`` -- and OpenGL contexts are thread-local, so
    that call only sees a real vendor when it runs on the same thread the
    context was made current on (the app's main/UI thread). The diagnostics
    listener is its own separate background thread (see
    :class:`_MemoryDiagnosticsListener`) and never has a context current on
    it at all, so calling ``GPU.detect()`` directly from there always falls
    through to ``GPU._fallback()``'s hardcoded 4 GiB/2 GiB guess -- silently,
    since ``GPU_UNKNOWN`` is a normal, expected value from
    ``gpu_vendor.get()``, not an error.

    A QObject's thread affinity is the thread that constructed it (unless
    explicitly moved), and this is only ever called from :func:`start`,
    which only ever runs on the main/UI thread (see ``MainFrame.__init__``)
    -- so the returned instance is safe to target with a
    ``BlockingQueuedConnection`` from any other thread.
    """
    from PySide6 import QtCore

    class _MainThreadGPUDetector(QtCore.QObject):

        def __init__(self):
            super().__init__()
            self._result = None

        @QtCore.Slot()
        def _run_detect(self):
            from .gpu import GPU

            gpu = GPU()
            gpu.detect()
            self._result = gpu

        def detect_blocking(self):
            """Run ``GPU.detect()`` on this object's own (main/UI) thread
            and return the populated :class:`.gpu.GPU` instance, blocking
            the calling thread until it's done.

            Calling this from this object's own thread would deadlock a
            ``BlockingQueuedConnection`` (it waits for that thread's event
            loop to process the call, but the calling thread *is* that
            event loop, already blocked here) -- not a real risk in
            practice, since this is only ever called from the diagnostics
            listener's own separate background thread, but guarded anyway.
            """
            if QtCore.QThread.currentThread() is self.thread():
                self._run_detect()
            else:
                QtCore.QMetaObject.invokeMethod(
                    self, '_run_detect', QtCore.Qt.ConnectionType.BlockingQueuedConnection)

            return self._result

    return _MainThreadGPUDetector()


# Built by start() (main/UI thread only) so it picks up that thread's
# affinity -- None until then, or after stop(). See _make_gpu_detector()'s
# own docstring for why this indirection exists at all.
_gpu_detector = None


@_check_types.do
def _format_gpu_growth() -> str:
    """GPU state over time -- the real pipeline (:meth:`.gpu.GPU.detect`,
    exactly what the app itself would see: vendor detection via the live GL
    context, the vendor SDK, the GL/table-based gap-fill, then the OpenCL/
    hardcoded last-resort fallback), diffed against the *previous*
    ``"gpu_growth"`` call this session -- same idea as ``"growth"``, but for
    ``vram_use`` and a few correlating fields (temp, engine utilization,
    fan, clocks) instead of Python object counts. Call it more than once,
    with real time (and whatever you're testing) passed between calls, to
    see whether VRAM usage is actually climbing rather than just what it
    happens to be right now.
    """
    global _last_gpu_snapshot

    import time

    if _gpu_detector is not None:
        # Marshaled onto the main/UI thread -- see _make_gpu_detector().
        gpu = _gpu_detector.detect_blocking()
    else:
        # No detector built (e.g. this handler called outside the normal
        # start()/listener flow) -- best effort on whatever thread this
        # runs on, same as before the marshaling fix.
        from .gpu import GPU

        gpu = GPU()
        gpu.detect()

    current = {}
    for name in _GPU_GROWTH_FIELDS:
        value = getattr(gpu, name).value
        current[name] = None if value == 'Unknown' else value

    now = time.time()

    lines = ['GPU STATE (via GPU.detect()):']
    for name in _GPU_GROWTH_FIELDS:
        lines.append(f'  {name}: {current[name]}')

    lines.append('')
    if _last_gpu_snapshot is None:
        lines.append('(first "gpu_growth" call this session -- no delta yet, '
                     'call again later to see the trend)')
    else:
        prev, prev_time = _last_gpu_snapshot
        lines.append(f'DELTA since last call ({now - prev_time:.1f}s ago):')
        for name in _GPU_GROWTH_FIELDS:
            old_value = prev.get(name)
            new_value = current[name]
            if isinstance(old_value, (int, float)) and isinstance(new_value, (int, float)):
                delta = new_value - old_value
                if name in ('vram_size', 'vram_use'):
                    lines.append(f'  {name}: {delta:+} bytes ({delta / 1024 / 1024:+.2f} MB)')
                else:
                    lines.append(f'  {name}: {delta:+}')
            else:
                lines.append(f'  {name}: (not numeric on one side, no delta)')

    _last_gpu_snapshot = (current, now)

    return '\n'.join(lines)


@_check_types.do
def _format_one_display(info) -> list[str]:
    lines = [f'  [{info.index}] connector_type={info.connector_type!r} '
             f'is_connected={info.is_connected} is_active={info.is_active}']
    if info.monitor_name is not None:
        lines.append(f'      monitor: {info.monitor_name}')
    if info.resolution is not None:
        width, height, refresh_hz = info.resolution
        lines.append(f'      resolution: {width}x{height} @ {refresh_hz:.2f}Hz')
    if info.edid_data is not None:
        lines.append(f'      edid: {len(info.edid_data)} bytes')

    return lines


@_check_types.do
def _format_displays() -> str:
    from .gpu.nvidia import NvidiaBackend
    from .gpu.amd import AMDBackend

    lines = ['NVIDIA displays (via nvapi):']
    nv_displays = NvidiaBackend().displays
    if not nv_displays:
        lines.append('  none found')
    for info in nv_displays:
        lines.extend(_format_one_display(info))

    lines.append('')
    lines.append('AMD displays (via pyamd_adl):')
    amd_displays = AMDBackend().displays
    if not amd_displays:
        lines.append('  none found')
    for info in amd_displays:
        lines.extend(_format_one_display(info))

    return '\n'.join(lines)


@_check_types.do
def _format_caches() -> str:
    lines = ['KNOWN APPLICATION CACHE SIZES:']

    try:
        from .gl.vbo import VBOSingleton, PooledVBOHandler

        lines.append(f'  VBOSingleton._instances: {len(VBOSingleton._instances)}')
        lines.append(f'  VBOSingleton._primitives: {len(VBOSingleton._primitives)}')

        for index, arena in enumerate(PooledVBOHandler._model_arenas):
            metrics = arena.debug_metrics()
            lines.append(
                f'  model_arena[{index}]: buffer_id={metrics["buffer_id"]} '
                f'used={metrics["used_vertices"]}/{metrics["capacity_vertices"]} vertices '
                f'allocations={metrics["allocation_count"]} '
                f'fragmentation={metrics["fragmentation"]:.3f}')
    except Exception as err:  # NOQA
        lines.append(f'  VBO cache inspection failed: {err!r}')

    return '\n'.join(lines)


def _fmt_bytes(value):
    if value is None:
        return 'Unknown'
    return f'{value:,} bytes ({value / 1024 / 1024:.2f} MB)'


@_check_types.do
def _format_stacks() -> str:
    """Every live thread's current Python call stack -- a snapshot in time,
    not a diff. For "what is thread X actually doing right now" (stuck in a
    loop, blocked on I/O, holding a local reference to something huge),
    not for tracking growth -- see ``"growth"``/``"gpu_growth"``/
    ``"heap_snapshot"`` for that.
    """
    import sys
    import traceback

    frames = sys._current_frames()  # NOQA -- deliberate use of the private API
    names = {t.ident: t.name for t in threading.enumerate()}

    lines = [f'THREAD STACKS -- {len(frames)} live threads:']
    for thread_id, frame in frames.items():
        name = names.get(thread_id, f'thread-{thread_id}')
        lines.append('')
        lines.append(f'=== {name} (id={thread_id}) ===')
        lines.extend(line.rstrip() for line in traceback.format_stack(frame))

    return '\n'.join(lines)


@_check_types.do
def _format_rss() -> str:
    """OS-reported process memory (:mod:`.process_memory`) alongside what
    ``tracemalloc`` can actually see. The gap between "private/committed"
    and "tracemalloc traced" is memory none of this module's other commands
    can explain at all -- native buffers (Qt, OpenGL client-side staging,
    C-extension ``malloc``s that bypass ``PyMem``). Start here when a
    reported total (Task Manager, ``gpu_growth``'s VRAM figure) is much
    bigger than ``"growth"``/``"tracemalloc"`` show -- it says whether the
    missing memory is even in the Python heap to begin with.
    """
    from . import process_memory

    rss, private = process_memory.get_process_memory()
    traced = tracemalloc.get_traced_memory()[0] if tracemalloc.is_tracing() else None

    lines = ['PROCESS MEMORY BREAKDOWN:']
    lines.append(f'  RSS (working set):   {_fmt_bytes(rss)}')
    lines.append(f'  Private/committed:   {_fmt_bytes(private)}')
    lines.append(f'  tracemalloc traced:  {_fmt_bytes(traced)}')

    if private is not None and traced is not None:
        untracked = private - traced
        lines.append('')
        lines.append(f'  UNTRACKED (private - traced): {_fmt_bytes(untracked)}')
        lines.append('  -- memory the OS charges to this process that tracemalloc has')
        lines.append('     no visibility into at all. If this is most of the total,')
        lines.append('     look at "caches"/"gpu_growth" and native allocators next,')
        lines.append('     not "tracemalloc"/"growth" -- those only see the Python heap.')
    elif traced is None:
        lines.append('')
        lines.append('  (tracemalloc is not running -- Config.debug.memory.enabled was')
        lines.append('   False when the process started, so no Python-heap comparison')
        lines.append('   figure is available)')
    else:
        lines.append('')
        lines.append('  (OS-reported process memory unavailable on this platform)')

    return '\n'.join(lines)


@_check_types.do
def _format_heap_snapshot() -> str:
    """Like ``"tracemalloc"``, but saved to a timestamped file under
    ``Config.debug.memory.snapshot_dir`` instead of only ever reported
    in-session -- so two snapshots taken arbitrarily far apart (including
    across a process restart) can be diffed later with
    ``diagnostics/compare_snapshots.py``, unlike ``"growth"``, which only
    ever compares against this session's own in-memory state.
    """
    if not tracemalloc.is_tracing():
        return ('tracemalloc is not running -- Config.debug.memory.enabled '
                'was False when the process started')

    import os
    import time

    snapshot = tracemalloc.take_snapshot()

    snapshot_dir = Config.debug.memory.snapshot_dir
    os.makedirs(snapshot_dir, exist_ok=True)
    filename = f'heap_{time.strftime("%Y%m%d_%H%M%S")}.snapshot'
    path = os.path.join(snapshot_dir, filename)
    snapshot.dump(path)

    stats = snapshot.statistics('lineno')
    total = sum(stat.size for stat in stats)

    lines = [f'HEAP SNAPSHOT saved to {path}']
    lines.append(f'-- {total / 1024 / 1024:.2f} MB traced across {len(stats)} locations')
    lines.append('')
    lines.append('top 15 allocation sites in this snapshot:')
    for stat in stats[:15]:
        lines.append(f'  {stat}')
    lines.append('')
    lines.append('diff two saved snapshots with:')
    lines.append('  python diagnostics/compare_snapshots.py <old.snapshot> <new.snapshot>')

    return '\n'.join(lines)


_HANDLERS = {
    'tracemalloc': _format_tracemalloc,
    'objects': _format_objects,
    'growth': _format_growth,
    'gpu': _format_gpu,
    'gpu_growth': _format_gpu_growth,
    'displays': _format_displays,
    'caches': _format_caches,
    'stacks': _format_stacks,
    'rss': _format_rss,
    'heap_snapshot': _format_heap_snapshot,
}


class _MemoryDiagnosticsListener(threading.Thread):

    @_check_types.do
    def __init__(self, port: int):
        super().__init__(name='Memory Diagnostics Listener', daemon=True)
        self._port = port
        self._listener: Listener | None = None
        self._exit_event = threading.Event()

    def run(self):
        try:
            self._listener = Listener(('localhost', self._port), authkey=_AUTHKEY)
        except OSError as err:
            _logger.error(f'memory diagnostics listener failed to bind port '
                          f'{self._port}: {err!r}')
            return

        while not self._exit_event.is_set():
            try:
                conn = self._listener.accept()
            except OSError:
                break

            try:
                command = conn.recv()
                handler = _HANDLERS.get(command)
                if handler is None:
                    conn.send(f'unknown command {command!r} -- known commands: '
                             f'{sorted(_HANDLERS)}')
                else:
                    conn.send(handler())
            except EOFError:
                pass
            except Exception as err:  # NOQA
                try:
                    conn.send(f'error handling command: {err!r}')
                except Exception:  # NOQA
                    pass
            finally:
                conn.close()

    @_check_types.do
    def stop(self):
        self._exit_event.set()
        if self._listener is not None:
            self._listener.close()
        self.join(5.0)


_listener_thread: _MemoryDiagnosticsListener | None = None


@_check_types.do
def start():
    """Start memory diagnostics if ``Config.debug.memory.enabled`` is True.

    No-op if disabled or already started. Safe to call unconditionally at
    startup -- call as early as possible so ``tracemalloc`` captures
    allocations from the start of the session.
    """
    global _listener_thread, _gpu_detector

    if not Config.debug.memory.enabled:
        return

    if _listener_thread is not None:
        return

    if not tracemalloc.is_tracing():
        tracemalloc.start(Config.debug.memory.tracemalloc_frames)

    # Must be built here, on whichever thread calls start() -- see
    # _make_gpu_detector()'s own docstring. start() is only ever called
    # from MainFrame.__init__, i.e. the main/UI thread that owns the real
    # GL context "gpu_growth" needs.
    _gpu_detector = _make_gpu_detector()

    # A GPU.detect() call marshaled cross-thread (i.e. exactly what a real
    # "gpu_growth" query does) has a one-time cost of 40-60s the first time
    # ANY background thread calls it in this process -- measured directly
    # against a real NVIDIA card; a same-thread call never pays it at all.
    # This looks like Windows COM/RPC proxy-channel setup (nvapi uses COM
    # internally) rather than anything nvapi- or driver-specific -- once
    # paid, later calls from a *different* thread than the one that paid it
    # are still fast (under 1s), so the cost is tied to the process, not to
    # which thread asks. Pay it here, once, in the background, during
    # startup -- instead of silently freezing the main/UI thread for up to
    # a minute the first time a developer actually runs "gpu_growth".
    threading.Thread(
        target=_gpu_detector.detect_blocking,
        name='GPU Detector Warmup', daemon=True).start()

    _listener_thread = _MemoryDiagnosticsListener(Config.debug.memory.listener_port)
    _listener_thread.start()

    _logger.info('memory diagnostics listener started on '
                f'localhost:{Config.debug.memory.listener_port}')


@_check_types.do
def stop():
    """Stop the memory diagnostics listener, if running. Safe to call
    unconditionally at shutdown.
    """
    global _listener_thread, _gpu_detector

    if _listener_thread is not None:
        _listener_thread.stop()
        _listener_thread = None
        _gpu_detector = None

        if tracemalloc.is_tracing():
            tracemalloc.stop()
