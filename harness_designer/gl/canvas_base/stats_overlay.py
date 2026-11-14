# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

import time

from PySide6 import QtCore
from PySide6 import QtWidgets

from ... import check_types as _check_types


class LoopMonitor:
    """How much of the time the GUI thread's event loop is busy.

    Qt's event dispatcher emits ``awake`` when the loop wakes up and
    ``aboutToBlock`` when it runs out of work and waits for the next OS
    event, so the time between the two is busy time (handlers, painting,
    and anything that blocks inside one, such as a GL flush) and the rest is
    idle. Busy near 100% means something on the main thread is the limit;
    low means the loop is waiting for events the OS is slow to deliver.

    Only created while the HUD is on, on the GUI thread, via
    :func:`loop_monitor`. The two slots run on every loop iteration so they
    are deliberately minimal (no ``check_types`` wrapper).
    """

    def __init__(self):
        self._busy = 0.0
        self._awake_at: float | None = time.perf_counter()

        dispatcher = QtCore.QAbstractEventDispatcher.instance()
        dispatcher.awake.connect(self._on_awake)
        dispatcher.aboutToBlock.connect(self._on_about_to_block)

    def _on_awake(self) -> None:
        # ``awake`` can be emitted several times between two
        # ``aboutToBlock`` (once per pass through the message pump, and by
        # nested loops). Only the first one starts a busy stretch -- moving
        # the start forward on a later one discards busy time that has not
        # been banked yet, which made the figure read ~0% and even go
        # negative.
        if self._awake_at is None:
            self._awake_at = time.perf_counter()

    def _on_about_to_block(self) -> None:
        awake_at = self._awake_at
        if awake_at is not None:
            self._busy += time.perf_counter() - awake_at
            self._awake_at = None

    def stop(self) -> None:
        """Disconnect from the dispatcher; the monitor is not used after."""
        dispatcher = QtCore.QAbstractEventDispatcher.instance()

        try:
            dispatcher.awake.disconnect(self._on_awake)
            dispatcher.aboutToBlock.disconnect(self._on_about_to_block)
        except (RuntimeError, TypeError):
            pass

    def busy_seconds(self) -> float:
        """Total busy seconds so far, including the stretch in progress."""
        busy = self._busy

        awake_at = self._awake_at
        if awake_at is not None:
            busy += time.perf_counter() - awake_at

        return busy


class EventProfiler(QtCore.QObject):
    """Where the GUI thread's time goes, by receiver class and event type.

    An application-wide event filter timestamps every event as Qt starts to
    deliver it; while the loop is saturated (``LoopMonitor`` near 100%) the
    time until the NEXT event starts is what the earlier one cost, handlers,
    painting and native calls such as the window flush included. Nested
    events split their parent's time, so read it as a ranking, not exact
    numbers. Every ``_REPORT_EVERY`` seconds the top entries go to the log.

    Opt-in because it runs Python for every event in the application: only
    created while ``Config.debug.performance.profile_events`` is on (see
    :func:`event_profiler`).
    """

    _REPORT_EVERY = 2.0
    _TOP = 10

    def __init__(self):
        super().__init__()

        self._prev_key: str | None = None
        self._prev_time = 0.0
        self._cost: dict[str, list[float]] = {}
        self._window_start = time.perf_counter()
        self._reporting = False

        QtCore.QCoreApplication.instance().installEventFilter(self)

    def eventFilter(self, obj: QtCore.QObject, event: QtCore.QEvent) -> bool:
        if self._reporting:
            return False

        now = time.perf_counter()

        prev_key = self._prev_key
        if prev_key is not None:
            entry = self._cost.get(prev_key)
            if entry is None:
                entry = [0.0, 0.0, 0.0]
                self._cost[prev_key] = entry

            elapsed = now - self._prev_time
            entry[0] += 1.0
            entry[1] += elapsed
            if elapsed > entry[2]:
                entry[2] = elapsed

        event_type = event.type()
        self._prev_key = (
            f'{type(obj).__name__}:{getattr(event_type, "name", event_type)}')
        self._prev_time = now

        if now - self._window_start >= self._REPORT_EVERY:
            self._report(now)

        return False

    def _report(self, now: float) -> None:
        from ... import logger as _logger

        window = now - self._window_start
        ranked = sorted(
            self._cost.items(), key=lambda item: item[1][1], reverse=True)

        lines = [f'Event loop profile over {window:.1f}s '
                 f'(share of time, count, avg ms, max ms):']

        for key, (count, total, worst) in ranked[:self._TOP]:
            lines.append(
                f'    {total * 100.0 / window:5.1f}%  {int(count):6d}  '
                f'{total * 1000.0 / count:7.2f}  {worst * 1000.0:7.2f}  {key}')

        self._reporting = True
        try:
            _logger.info('\n'.join(lines))
        finally:
            self._reporting = False

        self._cost = {}
        self._window_start = now
        self._prev_key = None


_event_profiler: EventProfiler | None = None


def event_profiler(enabled: bool) -> None:
    """Start or stop the :class:`EventProfiler` to match *enabled* (the
    ``Config.debug.performance.profile_events`` setting).

    Stopping removes its event filter and drops it, so while the setting is
    off nothing is timestamped or collected. Called from
    ``CanvasBase._update_stats`` (picks up the saved setting at startup) and
    from the Debug Settings dialog (applies a change at once).
    """
    global _event_profiler

    if enabled:
        if _event_profiler is None:
            _event_profiler = EventProfiler()
    elif _event_profiler is not None:
        QtCore.QCoreApplication.instance().removeEventFilter(_event_profiler)
        _event_profiler = None


_loop_monitor: LoopMonitor | None = None


def release_loop_monitor() -> None:
    """Stop and drop the shared :class:`LoopMonitor` if there is one (the
    HUD is off, nothing reads it); :func:`loop_monitor` makes a new one."""
    global _loop_monitor

    if _loop_monitor is not None:
        _loop_monitor.stop()
        _loop_monitor = None


def loop_monitor() -> LoopMonitor:
    """The shared :class:`LoopMonitor`, created on first use."""
    global _loop_monitor

    if _loop_monitor is None:
        _loop_monitor = LoopMonitor()

    return _loop_monitor


class StatsOverlay(QtWidgets.QLabel):
    """Frame rate and object count HUD in the upper right corner of a canvas.

    Shown when ``Config.debug.performance.show_stats`` is on;
    ``CanvasBase`` creates it on the first frame it is wanted and feeds it
    from ``paintGL`` a couple of times a second (setting the text on every
    frame would cost more than it measures).

    Parented to the canvas WRAPPER (``CanvasWindowBase``), not to the inner
    GL widget: the inner widget is a fixed, deliberately oversized "virtual
    canvas" that the wrapper clips down to the visible size, so positioning
    against its own width would put this outside the visible area. Same
    pattern as ``part_orientation.MeshStatsOverlay``.
    """

    @_check_types.do
    def __init__(self, canvas_wrapper: QtWidgets.QWidget):
        super().__init__(canvas_wrapper)

        self.setStyleSheet(
            'color: white; background-color: rgba(0, 0, 0, 140); '
            'padding: 4px; font-family: monospace;')

        self.setAlignment(QtCore.Qt.AlignmentFlag.AlignRight)
        self.setAttribute(
            QtCore.Qt.WidgetAttribute.WA_TransparentForMouseEvents)

        canvas_wrapper.installEventFilter(self)
        self.set_stats(None, 0)
        self.show()
        self.raise_()

    @_check_types.do
    def set_stats(self, fps: float | None, objects: int,
                  paint_ms: float | None = None,
                  repaint_ms: float | None = None,
                  mouse_rate: float | None = None,
                  mouse_ms: float | None = None,
                  loop_busy: float | None = None,
                  avg_fps: float | None = None) -> None:
        """
        :param fps: Frames per second, ``None`` while it is not known yet.
        :param objects: Number of objects drawn in the last frame.
        :param paint_ms: Average milliseconds spent inside ``paintGL`` per
            frame, ``None`` while it is not known yet.
        :param repaint_ms: Average milliseconds a synchronous ``repaint()``
            call takes (``paintGL`` plus Qt's resolve and window flush),
            ``None`` if no repaint() call was made in the window.
        :param mouse_rate: Mouse/wheel events per second reaching the
            canvas, ``None`` if there were none in the window.
        :param mouse_ms: Average milliseconds the canvas's mouse handler
            takes per event, ``None`` if there were none in the window.
        :param loop_busy: Fraction (0-1) of the window the GUI thread's
            event loop was busy rather than waiting, see
            :class:`LoopMonitor`; ``None`` while it is not known yet.
        :param avg_fps: Mean of the per-frame rate over the last few frames
            (a FIFO of the most recent ones, see ``_STATS_AVG_SAMPLES`` in
            ``canvas_base``); ``None`` while there are no samples.
        """
        if fps is None:
            fps_text = '--'
        else:
            fps_text = f'{fps:.1f}'

        if paint_ms is None:
            paint_text = '--'
        else:
            paint_text = f'{paint_ms:.1f} ms'

        if repaint_ms is None:
            repaint_text = '--'
        else:
            repaint_text = f'{repaint_ms:.1f} ms'

        if mouse_rate is None or mouse_ms is None:
            mouse_text = '--'
        else:
            mouse_text = f'{mouse_rate:.0f}/s, {mouse_ms:.1f} ms'

        if loop_busy is None:
            busy_text = '--'
        else:
            busy_text = f'{loop_busy * 100.0:.0f}%'

        if avg_fps is None:
            avg_text = '--'
        else:
            avg_text = f'{avg_fps:.1f}'

        self.setText(
            f'FPS: {fps_text}\nAvg FPS: {avg_text}\nPaint: {paint_text}\n'
            f'Repaint: {repaint_text}\nMouse: {mouse_text}\n'
            f'Loop busy: {busy_text}\nObjects: {objects}')
        self.adjustSize()
        self._reposition()

    @_check_types.do
    def _reposition(self) -> None:
        wrapper = self.parentWidget()
        if wrapper is None:
            return

        self.move(wrapper.width() - self.width() - 10, 10)

    @_check_types.do
    def eventFilter(self, obj: QtCore.QObject, event: QtCore.QEvent) -> bool:
        if event.type() == QtCore.QEvent.Type.Resize:
            self._reposition()

        return False
