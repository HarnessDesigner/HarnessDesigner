# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

"""The object the page's capture hook talks to.

It is registered on a ``QWebChannel`` under the name the hook expects
(:data:`~harness_designer.scraping.capture_hook.BRIDGE_NAME`). Anything
page JavaScript can reach it can call, so each slot treats its arguments
as untrusted: reports are parsed and validated by
:func:`~harness_designer.scraping.capture_model.parse_record`, and these
slots are the only thing the page can call.
"""

from PySide6 import QtCore

from ...scraping import capture_model as _capture_model
from ... import check_types as _check_types


class CaptureBridge(QtCore.QObject):
    """:ivar captured: A request finished (``CapturedRequest``).
    :ivar pageSourceReceived: The page was downloaded again (url, text).
    """

    captured = QtCore.Signal(object)
    pageSourceReceived = QtCore.Signal(str, str)

    @_check_types.do
    def __init__(self, parent: QtCore.QObject | None = None) -> None:
        super().__init__(parent)
        self._counter = 0

    @QtCore.Slot(str)
    @_check_types.do
    def record(self, text: str) -> None:
        request = _capture_model.parse_record(text, self._counter + 1)
        if request is None:
            return

        self._counter += 1
        self.captured.emit(request)

    @QtCore.Slot(str, str)
    @_check_types.do
    def pageSource(self, url: str, text: str) -> None:  # NOQA -- the name the page's script calls
        self.pageSourceReceived.emit(url, text)
