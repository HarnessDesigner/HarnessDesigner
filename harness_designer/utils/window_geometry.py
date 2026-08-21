# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

"""Multi-monitor-safe window centering, shared by every borderless window
that centers itself over another rectangle (a parent window, or -- for the
splash screen, which opens before the mainframe window exists -- the
mainframe's own remembered position/size).
"""

from PySide6 import QtCore
from PySide6 import QtGui
from PySide6 import QtWidgets

from .. import check_types as _check_types


@_check_types.do
def safe_center(target_rect: QtCore.QRect,
                 candidate_size: tuple[int, int]) -> QtCore.QPoint:
    """Return the screen point to center a *candidate_size* window on,
    given it would ideally be centered on *target_rect*.

    Centers directly on *target_rect* whenever the resulting window would
    be fully covered by the union of every connected display's own
    available area -- even if that means straddling two adjacent
    monitors, which is still fully on-screen and shouldn't trigger the
    fallback below. Otherwise falls back to the center of whichever
    single display overlaps *target_rect* the most (e.g. *target_rect*
    belongs to a display that's since been disconnected, or was dragged
    mostly off of every display) -- centering there instead of leaving
    the window centered on a now-largely-off-screen rectangle it can't
    be moved back from (borderless/frameless windows have no title bar
    to drag).

    :param target_rect: Rectangle to center over.
    :type target_rect: :class:`QtCore.QRect`
    :param candidate_size: ``(width, height)`` of the window being
        positioned.
    :type candidate_size: tuple[int, int]
    :returns: Point to center the window on.
    :rtype: :class:`QtCore.QPoint`
    """

    screens = QtWidgets.QApplication.screens()
    primary = QtWidgets.QApplication.primaryScreen()

    if not screens or primary is None:
        return target_rect.center()

    w, h = candidate_size
    candidate = QtCore.QRect(0, 0, w, h)
    candidate.moveCenter(target_rect.center())

    # Union of every display's own available area -- if *candidate* isn't
    # fully contained in it, some part of the window would render off of
    # every display at once.
    union = QtGui.QRegion()
    for screen in screens:
        union += QtGui.QRegion(screen.availableGeometry())

    if QtGui.QRegion(candidate).subtracted(union).isEmpty():
        return target_rect.center()

    target_screen = primary
    best_area = -1

    for screen in screens:
        overlap = screen.availableGeometry().intersected(target_rect)
        area = overlap.width() * overlap.height()

        if area > best_area:
            best_area = area
            target_screen = screen

    return target_screen.availableGeometry().center()
