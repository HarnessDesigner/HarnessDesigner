# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

import contextlib

from PySide6 import QtCore, QtGui

from ... import check_types as _check_types


@contextlib.contextmanager
def painting(device: QtGui.QPaintDevice):
    """A QPainter on *device* that is always ended. A painter still active when its device is destroyed makes Qt abort
    the whole process ("Cannot destroy paint device that is being painted"), and that is exactly what happens when
    anything raises between creating the painter and ending it: the exception's frame is torn down and frees the
    device first.
    """
    painter = QtGui.QPainter(device)

    try:
        yield painter
    finally:
        painter.end()


# Row height used for wire / housing renders
ROW_H = 48   # px  (set once; must match verticalHeader default section size)


# ---------------------------------------------------------------------------
# ── Housing / connector image renderer ───────────────────────────────────
# ---------------------------------------------------------------------------

# A QPixmap may only be made and used on the GUI thread, but the circuit table is built on a worker thread. So the
# connector pictures are drawn as QImage, which is safe anywhere, and the *_pixmap functions turn them into a QPixmap
# for callers that are on the GUI thread.
@_check_types.do
def scale_housing_image(src: QtGui.QImage, height: int = ROW_H) -> QtGui.QImage:
    """Scale a housing image to fit within a cell, preserving aspect ratio. Safe on any thread."""

    if src is None or src.isNull():
        return QtGui.QImage()

    return src.scaledToHeight(
        height - 6, QtCore.Qt.TransformationMode.SmoothTransformation)


@_check_types.do
def scale_housing_pixmap(src: QtGui.QPixmap, height: int = ROW_H) -> QtGui.QPixmap:
    """Scale a housing image to fit within a cell, preserving aspect ratio. GUI thread only."""

    if src is None or src.isNull():
        return QtGui.QPixmap()

    return QtGui.QPixmap.fromImage(scale_housing_image(src.toImage(), height))


@_check_types.do
def placeholder_connector_pixmap(name: str, height: int = ROW_H) -> QtGui.QPixmap:
    """The connector symbol of :func:`placeholder_connector_image` as a QPixmap. GUI thread only."""

    return QtGui.QPixmap.fromImage(placeholder_connector_image(name, height))


@_check_types.do
def placeholder_connector_image(name: str, height: int = ROW_H) -> QtGui.QImage:
    """
    Draw a minimal schematic connector symbol when no photo is available.
    Shows a rectangular housing outline with pin cavities. Safe on any thread.
    """
    w = max(height + 20, 64)
    h = height - 4
    px = QtGui.QImage(w, h, QtGui.QImage.Format.Format_ARGB32_Premultiplied)
    px.fill(QtCore.Qt.GlobalColor.transparent)

    with painting(px) as p:
        p.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing, True)

        body_rect = QtCore.QRectF(2, 2, w - 14, h - 4)
        latch_rect = QtCore.QRectF(w - 14, h * 0.3, 12, h * 0.4)

        # Body
        body_g = QtGui.QLinearGradient(0, 0, 0, h)
        body_g.setColorAt(0.0, QtGui.QColor("#4a4a52"))
        body_g.setColorAt(1.0, QtGui.QColor("#28282e"))
        p.setBrush(QtGui.QBrush(body_g))
        p.setPen(QtGui.QPen(QtGui.QColor("#666"), 1.0))
        p.drawRoundedRect(body_rect, 3, 3)

        # Latch tab
        p.setBrush(QtGui.QBrush(QtGui.QColor("#5a5a64")))
        p.drawRoundedRect(latch_rect, 2, 2)

        # Pin cavities (3 representative holes)
        pin_size = min(h * 0.18, 8.0)
        n_pins = 3
        spacing = (body_rect.height() - 8) / n_pins
        for i in range(n_pins):
            y = body_rect.top() + 4 + i * spacing + spacing * 0.2
            cavity = QtCore.QRectF(body_rect.left() + 4, y, pin_size * 1.6, pin_size)
            p.setBrush(QtGui.QBrush(QtGui.QColor("#111")))
            p.setPen(QtGui.QPen(QtGui.QColor("#333"), 0.5))
            p.drawRoundedRect(cavity, 1, 1)

        # Label
        if name:
            p.setPen(QtGui.QColor("#aaa"))
            f = QtGui.QFont("monospace", 6)
            f.setBold(True)
            p.setFont(f)
            label = name[:10] + ("…" if len(name) > 10 else "")
            p.drawText(body_rect.adjusted(2, 2, -14, -2),
                       QtCore.Qt.AlignmentFlag.AlignBottom | QtCore.Qt.AlignmentFlag.AlignLeft,
                       label)

    return px


