# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

"""Live benchmark for 3D wire drawing, switched by ``Config.debug.rendering3d.wire_benchmark``.

While the switch is on, every 3D wire draw is timed on the CPU (``time.perf_counter``) and on the GPU (a ``GL_TIME_ELAPSED``
query around the draw), together with the draw calls and vertices it submitted, and a summary of the last
:data:`REPORT_SECONDS` is written to the log. Drag a wire around while it is on and read the log (the Log Viewer shows it).

What the summary holds, per canvas:

* the frame rate, and how many wires were drawn per frame by the plain path (a cylinder per segment plus a helix mesh for a
  stripe) and by the GPU path (the faces program's twist mode, ``Config.debug.rendering3d.gpu_single_wires``);
* wire CPU time per frame (mean, 95th percentile, worst) -- the time spent inside ``Wire.render``;
* wire GPU time per frame (mean, worst) -- the sum of the wires' own timer queries -- and the GPU time of the whole object pass;
* draw calls and vertices submitted per frame;
* geometry updates (``Wire._update_position`` while a point is dragged), plan rebuilds (``Wire._twist_segments``) and stripe
  mesh rebuilds (``WireStripe._ensure_stripe_capacity``), each a count with its total and worst time;
* what the NVIDIA driver reports over the window (through ``nvapi``, sampled once a second on a background thread): the GPU,
  frame buffer and video engine load, the power state, the graphics and memory clocks, the temperature, the clock-throttle
  reasons, VRAM in use and VRAM evicted. A GPU that is nearly idle drops to a low power state and slow clocks, which makes a
  millisecond reading there larger than the same work would cost under load: read the clocks beside the timings.

The CPU numbers are for the code as it runs from source: ``check_types.do`` wraps nearly every call, so they are higher than
a compiled build's.

The hooks (:meth:`WireBenchmark.wire_begin`, ``wire_end`` and ``add_draw``) are called per wire per frame, so they are not
wrapped in ``check_types.do``: the wrapper's own cost would land inside the numbers being measured.
"""

import collections
import ctypes
import threading
import time

from OpenGL import GL

from .. import config as _config
from .. import logger as _logger
from .. import check_types as _check_types


_debug_config = _config.Config.debug.rendering3d

# Seconds of frames each log summary covers.
REPORT_SECONDS = 2.0

# Seconds between two reads of the driver's load figures.
LOAD_SAMPLE_SECONDS = 1.0

# A frame's GPU queries are read this many frames after they were issued, so the read never stalls the pipeline; a frame still
# not finished when more than this many are waiting is dropped.
_MAX_PENDING_FRAMES = 8

_NS_PER_MS = 1000000.0


class _Window:
    """What one canvas has measured since its last summary."""

    def __init__(self):
        self.started = time.perf_counter()
        self.frames = 0
        self.wire_frames = 0
        self.plain_wires = 0
        self.gpu_wires = 0
        self.draws = 0
        self.vertices = 0
        self.cpu_frames: list[float] = []
        self.gpu_wire_frames: list[float] = []
        self.gpu_pass_frames: list[float] = []


class _Events:
    """Work done outside the draw that the wires cause: geometry updates, plan rebuilds and stripe mesh rebuilds."""

    def __init__(self):
        self.geometry: list[float] = []
        self.plans: list[float] = []
        self.stripe_rebuilds: list[float] = []


class _GPULoad:
    """What the NVIDIA driver says the GPU is doing, read through ``nvapi`` on a background thread.

    One read of ``nvapi``'s ``performance_monitor`` builds the whole power-state table, so it is read once a second, not per
    frame. A reading ``nvapi`` cannot give on this driver or card stays ``None``; no vendor but NVIDIA is supported here.
    """

    def __init__(self):
        self._thread: threading.Thread | None = None
        self._stop = threading.Event()
        self._lock = threading.Lock()
        self._failed: set[str] = set()
        self._reset()

    def _reset(self) -> None:
        self._samples = 0
        self._gpu_load: list[int] = []
        self._memory_load: list[int] = []
        self._video_load: list[int] = []
        self._pstate: str | None = None
        self._graphics_mhz: list[float] = []
        self._memory_mhz: list[float] = []
        self._temperature: int | None = None
        self._throttle = 0
        self._vram_used: int | None = None
        self._evictions_first: int | None = None
        self._evictions_last: int | None = None

    @property
    def running(self) -> bool:
        return self._thread is not None

    @_check_types.do
    def start(self) -> None:
        if self._thread is not None:
            return

        self._stop.clear()
        self._thread = threading.Thread(target=self._run, name='Wire Benchmark GPU Load', daemon=True)
        self._thread.start()

    @_check_types.do
    def stop(self) -> None:
        if self._thread is None:
            return

        self._stop.set()
        self._thread.join(timeout=3.0)
        self._thread = None

        with self._lock:
            self._reset()

    @_check_types.do
    def _note_failure(self, name: str, err: Exception) -> None:
        """Log a reading that failed once, not once a second."""
        if name in self._failed:
            return

        self._failed.add(name)
        _logger.traceback(err, f'wire benchmark: nvapi reading "{name}" failed, it will be left out')

    @_check_types.do
    def _open_gpu(self) -> object | None:
        """The first physical GPU nvapi finds, the way ``gpu.nvidia.backend.NvidiaBackend`` picks it."""
        try:
            import nvapi

            for logical_gpu in nvapi.GPUs():
                for physical_gpu in logical_gpu.physical_gpus:
                    return physical_gpu
        except Exception as err:  # NOQA
            _logger.traceback(err, 'wire benchmark: nvapi is not available, the GPU load is not sampled')

        return None

    @_check_types.do
    def _run(self) -> None:
        gpu = self._open_gpu()

        if gpu is None:
            return

        while not self._stop.wait(LOAD_SAMPLE_SECONDS):
            try:
                self._sample(gpu)
            except Exception as err:  # NOQA
                self._note_failure('sample', err)

    @_check_types.do
    def _sample(self, gpu: object) -> None:
        # each reading is its own try: a driver that has no answer for one still gives the others
        utilization = None
        pstate = None
        clocks = None
        temperature = None
        throttle = None
        free_kb = None
        total_kb = None
        evictions = None

        try:
            utilization = gpu.performance_monitor.get('utilization')  # NOQA
        except Exception as err:  # NOQA
            self._note_failure('utilization', err)

        try:
            pstate = str(gpu.current_pstate)  # NOQA
        except Exception as err:  # NOQA
            self._note_failure('pstate', err)

        try:
            clocks = gpu.clock_frequencies.current  # NOQA
        except Exception as err:  # NOQA
            self._note_failure('clocks', err)

        try:
            sensors = gpu.thermal_sensors  # NOQA

            if sensors:
                temperature = sensors[0].current_temp
        except Exception as err:  # NOQA
            self._note_failure('temperature', err)

        try:
            throttle = int(gpu.perf_decrease_info)  # NOQA
        except Exception as err:  # NOQA
            self._note_failure('throttle', err)

        try:
            free_kb = gpu.current_available_dedicated_memory  # NOQA
            total_kb = gpu.dedicated_memory  # NOQA
        except Exception as err:  # NOQA
            self._note_failure('vram', err)

        try:
            evictions = int(gpu.dedicated_memory_eviction_count)  # NOQA
        except Exception as err:  # NOQA
            self._note_failure('evictions', err)

        with self._lock:
            self._samples += 1

            if utilization:
                if len(utilization) > 0 and utilization[0] is not None:
                    self._gpu_load.append(utilization[0])
                if len(utilization) > 1 and utilization[1] is not None:
                    self._memory_load.append(utilization[1])
                if len(utilization) > 2 and utilization[2] is not None:
                    self._video_load.append(utilization[2])

            if pstate is not None:
                self._pstate = pstate

            if clocks is not None:
                if clocks.graphics is not None:
                    self._graphics_mhz.append(clocks.graphics / 1000.0)
                if clocks.memory is not None:
                    self._memory_mhz.append(clocks.memory / 1000.0)

            if temperature is not None:
                self._temperature = temperature

            if throttle is not None:
                self._throttle |= throttle

            if free_kb is not None and total_kb is not None:
                self._vram_used = (total_kb - free_kb) * 1024

            if evictions is not None:
                if self._evictions_first is None:
                    self._evictions_first = evictions

                self._evictions_last = evictions

    @_check_types.do
    def summary(self) -> str:
        """The readings since the last call, as the lines of the log summary, and start a new window."""
        with self._lock:
            samples = self._samples

            if samples == 0:
                self._reset()
                return '  GPU load (nvapi): no reading yet'

            parts = []

            if self._gpu_load:
                parts.append(f'GPU {sum(self._gpu_load) / len(self._gpu_load):.0f}% (peak {max(self._gpu_load)}%)')
            if self._memory_load:
                parts.append(f'frame buffer {sum(self._memory_load) / len(self._memory_load):.0f}% '
                             f'(peak {max(self._memory_load)}%)')
            if self._video_load:
                parts.append(f'video {sum(self._video_load) / len(self._video_load):.0f}%')
            if self._pstate is not None:
                parts.append(f'power state {self._pstate}')
            if self._graphics_mhz:
                parts.append(f'graphics clock {sum(self._graphics_mhz) / len(self._graphics_mhz):.0f} MHz '
                             f'(low {min(self._graphics_mhz):.0f})')
            if self._memory_mhz:
                parts.append(f'memory clock {sum(self._memory_mhz) / len(self._memory_mhz):.0f} MHz')
            if self._temperature is not None:
                parts.append(f'{self._temperature} C')

            parts.append(f'throttle flags 0x{self._throttle:X}')

            if self._vram_used is not None:
                parts.append(f'VRAM in use {self._vram_used / 1073741824:.2f} GiB')
            if self._evictions_first is not None:
                parts.append(f'VRAM evictions {self._evictions_last - self._evictions_first}')

            line = f'  GPU load (nvapi, {samples} reads): ' + ' | '.join(parts)
            self._reset()

        return line


def _mean(values: list[float]) -> float:
    if not values:
        return 0.0

    return sum(values) / len(values)


def _percentile(values: list[float], fraction: float) -> float:
    if not values:
        return 0.0

    ordered = sorted(values)
    return ordered[min(len(ordered) - 1, int(len(ordered) * fraction))]


def _max(values: list[float]) -> float:
    if not values:
        return 0.0

    return max(values)


class WireBenchmark:
    """The one collector, :data:`BENCH`. See the module docstring for what it measures and how it is hooked in."""

    def __init__(self):
        self._windows: dict[str, _Window] = {}
        self._window: _Window | None = None
        self._events = _Events()
        self._load = _GPULoad()

        # a wire is being timed between wire_begin and wire_end
        self._recording = False
        self._wire_query = 0
        self._wire_started = 0.0
        self._wire_is_gpu = False

        # the frame being drawn
        self._frame_open = False
        self._frame_cpu = 0.0
        self._frame_wires = 0
        self._frame_draws = 0
        self._frame_vertices = 0
        self._frame_start_query = 0
        self._frame_queries: list[int] = []

        self._free_queries: list[int] = []
        self._pending: collections.deque = collections.deque()

        # set when a GL call of ours failed: the benchmark stops collecting until it is switched off and on again
        self._broken = False

    @property
    def recording(self) -> bool:
        """Whether a wire is being timed right now (the draw code only counts draws while it is)."""
        return self._recording

    # ---- GL queries ----------------------------------------------------------------------------------------------------

    def _take_query(self) -> int:
        if not self._free_queries:
            self._free_queries.extend(int(q) for q in GL.glGenQueries(32))

        return self._free_queries.pop()

    def _release_queries(self, queries: list[int]) -> None:
        self._free_queries.extend(queries)

    @staticmethod
    def _timestamp(query: int) -> int:
        value = ctypes.c_uint64()
        GL.glGetQueryObjectui64v(query, GL.GL_QUERY_RESULT, ctypes.byref(value))
        return value.value

    def _collect_finished(self) -> None:
        """Read every pending frame whose queries the GPU has finished, oldest first."""
        while self._pending:
            window, start_query, wire_queries, end_query, wire_count = self._pending[0]

            if not GL.glGetQueryObjectiv(end_query, GL.GL_QUERY_RESULT_AVAILABLE):
                if len(self._pending) <= _MAX_PENDING_FRAMES:
                    return

                # too far behind to wait for: drop it
                self._pending.popleft()
                self._release_queries([start_query] + wire_queries + [end_query])
                continue

            self._pending.popleft()

            wire_ns = 0

            for query in wire_queries:
                wire_ns += int(GL.glGetQueryObjectuiv(query, GL.GL_QUERY_RESULT))

            pass_ns = self._timestamp(end_query) - self._timestamp(start_query)

            window.gpu_wire_frames.append(wire_ns / _NS_PER_MS)
            window.gpu_pass_frames.append(pass_ns / _NS_PER_MS)

            self._release_queries([start_query] + wire_queries + [end_query])

    # ---- frame hooks (CanvasBase._draw_scene) ---------------------------------------------------------------------------

    def frame_begin(self, canvas_name: str) -> None:
        """Called first in a canvas's ``_draw_scene``; does nothing while the switch is off."""
        if not _debug_config.wire_benchmark:
            # the common case, once per frame: only do real work on the frame after the switch went off
            if self._windows or self._broken or self._load.running:
                self._stop_if_running()

            return

        if self._broken:
            return

        try:
            if not self._load.running:
                self._load.start()

            window = self._windows.get(canvas_name)

            if window is None:
                window = _Window()
                self._windows[canvas_name] = window

            self._window = window
            self._frame_open = True
            self._frame_cpu = 0.0
            self._frame_wires = 0
            self._frame_draws = 0
            self._frame_vertices = 0
            self._frame_queries = []

            self._frame_start_query = self._take_query()
            GL.glQueryCounter(self._frame_start_query, GL.GL_TIMESTAMP)
        except Exception as err:  # NOQA
            self._fail(err)

    def frame_end(self, canvas_name: str) -> None:
        """Called last in a canvas's ``_draw_scene``; writes the summary when :data:`REPORT_SECONDS` have passed."""
        if not self._frame_open:
            return

        self._frame_open = False

        try:
            window = self._window
            window.frames += 1

            end_query = self._take_query()
            GL.glQueryCounter(end_query, GL.GL_TIMESTAMP)
            self._pending.append((window, self._frame_start_query, self._frame_queries, end_query, self._frame_wires))

            if self._frame_wires:
                window.wire_frames += 1
                window.draws += self._frame_draws
                window.vertices += self._frame_vertices
                window.cpu_frames.append(self._frame_cpu * 1000.0)

            self._collect_finished()

            if time.perf_counter() - window.started >= REPORT_SECONDS:
                self._report(canvas_name, window)
                self._windows[canvas_name] = _Window()
        except Exception as err:  # NOQA
            self._fail(err)

    # ---- wire hooks (objects_3d.wire.Wire.render) -----------------------------------------------------------------------

    def wire_begin(self, gpu_path: bool) -> None:
        """Start timing one wire. *gpu_path* is True when it is drawn through the faces program's twist mode."""
        if not self._frame_open or self._broken:
            return

        try:
            self._wire_query = self._take_query()
            self._wire_is_gpu = gpu_path

            GL.glBeginQuery(GL.GL_TIME_ELAPSED, self._wire_query)
            self._recording = True
            self._wire_started = time.perf_counter()
        except Exception as err:  # NOQA
            self._fail(err)

    def add_draw(self, vertices: int) -> None:
        """Count one draw call of *vertices* vertices for the wire being timed."""
        self._frame_draws += 1
        self._frame_vertices += vertices

    def wire_end(self) -> None:
        """Stop timing the wire :meth:`wire_begin` started."""
        if not self._recording:
            return

        elapsed = time.perf_counter() - self._wire_started
        self._recording = False

        try:
            GL.glEndQuery(GL.GL_TIME_ELAPSED)
            self._frame_queries.append(self._wire_query)
            self._frame_cpu += elapsed
            self._frame_wires += 1

            if self._wire_is_gpu:
                self._window.gpu_wires += 1
            else:
                self._window.plain_wires += 1
        except Exception as err:  # NOQA
            self._fail(err)

    # ---- work outside the draw ------------------------------------------------------------------------------------------

    def geometry(self, seconds: float) -> None:
        """One ``Wire._update_position`` (a point of a wire moved) took *seconds*."""
        self._events.geometry.append(seconds * 1000.0)

    def plan(self, seconds: float) -> None:
        """One ``Wire._twist_segments`` rebuild took *seconds*."""
        self._events.plans.append(seconds * 1000.0)

    def stripe_rebuild(self, seconds: float) -> None:
        """The shared stripe helix mesh was rebuilt, which took *seconds*."""
        self._events.stripe_rebuilds.append(seconds * 1000.0)

    # ---- reporting ------------------------------------------------------------------------------------------------------

    @_check_types.do
    def _stop_if_running(self) -> None:
        """The switch went off: stop the sampler and forget everything collected."""
        self._broken = False

        if not self._load.running and not self._windows:
            return

        self._load.stop()
        self._windows.clear()
        self._events = _Events()
        self._window = None
        self._frame_open = False
        self._recording = False

        for window, start_query, wire_queries, end_query, _count in self._pending:
            self._release_queries([start_query] + wire_queries + [end_query])

        self._pending.clear()

    @_check_types.do
    def _fail(self, err: Exception) -> None:
        """Something in the collector raised: say so once and stop collecting until the switch is cycled."""
        self._broken = True
        self._frame_open = False
        self._recording = False
        _logger.traceback(err, 'wire benchmark failed and has stopped; switch it off and on to restart it')

    @staticmethod
    def _timing_line(label: str, values: list[float], unit: str) -> str:
        if not values:
            return f'  {label}: none'

        return (f'  {label}: n {len(values)}, total {sum(values):.2f} {unit}, mean {_mean(values):.3f}, '
                f'worst {_max(values):.3f}')

    @_check_types.do
    def _report(self, canvas_name: str, window: _Window) -> None:
        elapsed = max(time.perf_counter() - window.started, 1e-9)
        events = self._events
        self._events = _Events()

        if window.wire_frames == 0 and not events.geometry:
            self._load.summary()
            return

        wire_frames = max(window.wire_frames, 1)
        wires_per_frame = (window.plain_wires + window.gpu_wires) / wire_frames

        lines = [
            f'[wire benchmark: {canvas_name}] {window.frames} frames in {elapsed:.1f} s ({window.frames / elapsed:.0f} fps), '
            f'{window.wire_frames} with wires',
            f'  wires per frame {wires_per_frame:.1f} (plain path {window.plain_wires / wire_frames:.1f}, '
            f'GPU path {window.gpu_wires / wire_frames:.1f})',
            f'  wire CPU ms per frame: mean {_mean(window.cpu_frames):.3f}, 95th {_percentile(window.cpu_frames, 0.95):.3f}, '
            f'worst {_max(window.cpu_frames):.3f}',
            f'  wire GPU ms per frame: mean {_mean(window.gpu_wire_frames):.3f}, worst {_max(window.gpu_wire_frames):.3f} '
            f'({len(window.gpu_wire_frames)} frames read back)',
            f'  whole object pass GPU ms per frame: mean {_mean(window.gpu_pass_frames):.3f}, '
            f'worst {_max(window.gpu_pass_frames):.3f}',
            f'  per frame: {window.draws / wire_frames:.0f} draw calls, {window.vertices / wire_frames:,.0f} vertices',
            self._timing_line('geometry updates (a wire point moved), ms', events.geometry, 'ms'),
            self._timing_line('plan rebuilds (twist segments), ms', events.plans, 'ms'),
            self._timing_line('stripe mesh rebuilds, ms', events.stripe_rebuilds, 'ms'),
            self._load.summary(),
        ]

        _logger.info('\n'.join(lines))


BENCH = WireBenchmark()
