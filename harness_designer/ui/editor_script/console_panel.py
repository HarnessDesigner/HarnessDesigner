# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

"""The Console tab: what the scripts that have been run print, one run at a
time, and the Stop for the run being shown.

Several runs may be alive at once (a second script is how a stuck first one is
released), so the panel keeps a list of them. It keeps collecting a run's
output after the run has ended, because the threads a script started can still
be printing.

Stop raises ``SystemExit`` in the script's thread (``scraping/runner.py``). If
the script is still running :data:`STOP_WARNING_SECONDS` later it is waiting at
the operating system level, out of Stop's reach, and the panel says so through
:attr:`ConsolePanel.stopIgnored`; showing the warning is the owner's job.
"""

import time

from PySide6 import QtCore
from PySide6 import QtGui
from PySide6 import QtWidgets

from ..widgets import wrap_label as _wrap_label
from ...scraping import runner as _runner
from ... import check_types as _check_types

# How long after Stop a script may keep running before the user is told Stop did not reach it.
STOP_WARNING_SECONDS = 2.0

_TICK_MILLISECONDS = 100

# The most text kept per run (the end of the output is kept) and the most lines shown.
MAX_SHOWN_CHARS = 1_000_000
_MAX_LINES = 20_000


class ConsolePanel(QtWidgets.QWidget):
    """:ivar stopIgnored: A run was still going :data:`STOP_WARNING_SECONDS`
        after Stop was sent to it (the :class:`~harness_designer.scraping.runner.ScriptRun`).
    :ivar activityChanged: Whether the run being shown is running (Stop
        should be available).
    :ivar messageRaised: Something short for the editor's message line.
    """

    stopIgnored = QtCore.Signal(object)
    activityChanged = QtCore.Signal(bool)
    messageRaised = QtCore.Signal(str)

    @_check_types.do
    def __init__(self, runner: _runner.Runner, parent: QtWidgets.QWidget | None = None) -> None:
        super().__init__(parent)
        self._runner = runner
        self._texts: dict[int, str] = {}
        self._labels: dict[int, str] = {}
        self._stop_sent: dict[int, float] = {}
        self._warned: set[int] = set()
        self._active = False

        self._runs = QtWidgets.QComboBox(self)
        self._runs.setSizeAdjustPolicy(QtWidgets.QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon)
        self._runs.setMinimumContentsLength(24)
        self._status = _wrap_label.WrapLabel('', self)
        self._clear = QtWidgets.QPushButton('Clear finished', self)
        self._clear.setToolTip('Forget the runs that have ended.')

        self._output = QtWidgets.QPlainTextEdit(self)
        self._output.setReadOnly(True)
        self._output.setMaximumBlockCount(_MAX_LINES)
        self._output.setLineWrapMode(QtWidgets.QPlainTextEdit.LineWrapMode.NoWrap)
        self._output.setPlaceholderText('What a script prints appears here. Run (F5) runs the script in the editor.')
        mono = QtGui.QFont('Consolas', 10)
        mono.setStyleHint(QtGui.QFont.StyleHint.Monospace)
        self._output.setFont(mono)

        top = QtWidgets.QHBoxLayout()
        top.addWidget(self._runs, 1)
        top.addWidget(self._clear)

        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.addLayout(top)
        layout.addWidget(self._status)
        layout.addWidget(self._output, 1)

        self._runs.currentIndexChanged.connect(self._selection_changed)
        self._clear.clicked.connect(self.clear_finished)

        # Always on, shown or not: output and Stop warnings must not wait for the tab to be visible.
        self._timer = QtCore.QTimer(self)
        self._timer.setInterval(_TICK_MILLISECONDS)
        self._timer.timeout.connect(self._tick)
        self._timer.start()
        self._refresh_status()

    # -- public ---------------------------------------------------------------------

    @_check_types.do
    def selected_run(self) -> _runner.ScriptRun | None:
        number = self._runs.currentData()
        if number is None:
            return None

        for run in self._runner.runs():
            if run.number == number:
                return run

        return None

    @_check_types.do
    def show_run(self, run: _runner.ScriptRun) -> None:
        """Make *run* (just started) the one shown."""
        self._tick()
        index = self._runs.findData(run.number)
        if index >= 0:
            self._runs.setCurrentIndex(index)

    @_check_types.do
    def text_of(self, run: _runner.ScriptRun) -> str:
        """Everything the console has collected from *run* so far."""
        self._collect(run)
        return self._texts.get(run.number, '')

    @_check_types.do
    def stop_selected(self) -> bool:
        """Send Stop to the run being shown. Returns whether it was sent."""
        run = self.selected_run()
        if run is None or run.status() != _runner.RUNNING:
            self.messageRaised.emit('There is no running script to stop.')
            return False

        try:
            sent = run.request_stop()
        except RuntimeError as problem:
            self.messageRaised.emit(str(problem))
            return False

        if not sent:
            self.messageRaised.emit('That script has already ended.')
            return False

        self._stop_sent[run.number] = time.monotonic()
        self._warned.discard(run.number)
        self._refresh_status()
        return True

    @_check_types.do
    def clear_finished(self) -> None:
        for run in self._runner.runs():
            self._runner.forget(run)

        self._tick()

    @_check_types.do
    def shutdown(self) -> None:
        """The application is closing: send Stop to every live run (without waiting for any of them)."""
        self._timer.stop()
        self._runner.stop_all()

    # -- the timer ---------------------------------------------------------------------

    @_check_types.do
    def _tick(self) -> None:
        runs = self._runner.runs()
        self._sync(runs)
        for run in runs:
            self._collect(run)

        self._check_stops(runs)
        self._refresh_status()

    @_check_types.do
    def _sync(self, runs: list[_runner.ScriptRun]) -> None:
        """Keep the list of runs (and the texts kept for them) in step with the runner."""
        numbers = {run.number for run in runs}
        selected_before = self._runs.currentData()

        self._runs.blockSignals(True)
        for index in range(self._runs.count() - 1, -1, -1):
            if self._runs.itemData(index) not in numbers:
                self._runs.removeItem(index)

        for run in runs:
            label = self._label_of(run)
            index = self._runs.findData(run.number)
            if index < 0:
                self._runs.addItem(label, run.number)
                self._labels[run.number] = label
            elif self._labels.get(run.number) != label:
                self._runs.setItemText(index, label)
                self._labels[run.number] = label

        self._runs.blockSignals(False)

        for number in list(self._texts):
            if number not in numbers:
                del self._texts[number]
                self._labels.pop(number, None)

        if self._runs.currentData() != selected_before:
            self._selection_changed()

    @_check_types.do
    def _label_of(self, run: _runner.ScriptRun) -> str:
        return f'#{run.number}  {run.label}  -  {run.status()}'

    @_check_types.do
    def _collect(self, run: _runner.ScriptRun) -> None:
        text, dropped = run.output.take()
        if dropped:
            text = f'\n[{dropped:,} characters of output were dropped: the console could not keep up]\n' + text

        if not text:
            return

        kept = self._texts.get(run.number, '') + text
        trimmed = len(kept) > MAX_SHOWN_CHARS
        if trimmed:
            kept = kept[-MAX_SHOWN_CHARS:]

        self._texts[run.number] = kept

        current = self.selected_run()
        if current is None or current.number != run.number:
            return

        if trimmed:
            self._show_selected()
        else:
            self._append_shown(text)

    @_check_types.do
    def _check_stops(self, runs: list[_runner.ScriptRun]) -> None:
        now = time.monotonic()
        by_number = {run.number: run for run in runs}
        for number, sent in list(self._stop_sent.items()):
            run = by_number.get(number)
            if run is None or run.status() != _runner.RUNNING:
                del self._stop_sent[number]
                self._warned.discard(number)
                continue

            if number not in self._warned and now - sent >= STOP_WARNING_SECONDS:
                self._warned.add(number)
                self.stopIgnored.emit(run)

    # -- showing a run -------------------------------------------------------------------

    @_check_types.do
    def _selection_changed(self, *_args: tuple[object]) -> None:
        self._show_selected()
        self._refresh_status()

    @_check_types.do
    def _show_selected(self) -> None:
        run = self.selected_run()
        text = ''
        if run is not None:
            text = self._texts.get(run.number, '')

        self._output.setPlainText(text)
        bar = self._output.verticalScrollBar()
        bar.setValue(bar.maximum())

    @_check_types.do
    def _append_shown(self, text: str) -> None:
        bar = self._output.verticalScrollBar()
        at_end = bar.value() >= bar.maximum() - 4

        # Through our own cursor, so the user's selection in the output is left alone.
        cursor = QtGui.QTextCursor(self._output.document())
        cursor.movePosition(QtGui.QTextCursor.MoveOperation.End)
        cursor.insertText(text)

        if at_end:
            bar.setValue(bar.maximum())

    @_check_types.do
    def _refresh_status(self) -> None:
        run = self.selected_run()
        active = run is not None and run.status() == _runner.RUNNING
        if active != self._active:
            self._active = active
            self.activityChanged.emit(active)

        if run is None:
            self._status.setText('Nothing has been run yet.')
            return

        status = run.status()
        seconds = run.elapsed()
        if status == _runner.RUNNING and run.number in self._warned:
            text = ('Stop was sent, but the script is still running: it is waiting at the operating system '
                    'level, out of Stop\'s reach.')
        elif status == _runner.RUNNING and run.number in self._stop_sent:
            text = f'Stopping... ({seconds:.0f} s)'
        elif status == _runner.RUNNING:
            text = f'Running ({seconds:.0f} s)'
        elif status == _runner.FAILED:
            text = f'Failed after {seconds:.1f} s'
        elif status == _runner.STOPPED:
            text = f'Stopped after {seconds:.1f} s'
        else:
            text = f'Finished in {seconds:.1f} s'

        self._status.setText(text)
