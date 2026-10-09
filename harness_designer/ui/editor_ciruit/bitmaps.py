# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

from PySide6 import QtCore, QtGui

from ... import check_types as _check_types


# ---------------------------------------------------------------------------
# Conductor material colours
# Bare copper → warm orange-brown; tinned copper → silvery; aluminium → light silver
# ---------------------------------------------------------------------------
CONDUCTOR_MATERIAL_COLORS: dict[str, str] = {
    "copper": "#b87333",
    "tinned_copper": "#c8c8c0",
    "tinned": "#c8c8c0",
    "tin": "#c8c8c0",
    "aluminium": "#a8a9ad",
    "aluminum": "#a8a9ad",
    "silver": "#e8e8e8",
    "gold": "#d4af37",
    "nickel": "#9a9a9a",
    "steel": "#8c8c8c",
    "default": "#b87333",  # fallback → copper
}


@_check_types.do
def conductor_color(material: str | None) -> str:
    """Execute the conductor color operation.

    UNKNOWN details are inferred from the callable name and signature.

    :param material: Value for ``material``.
    :type material: str | None
    :returns: Return value. UNKNOWN details.
    :rtype: str
    """
    if not material:
        return CONDUCTOR_MATERIAL_COLORS["default"]

    key = material.lower().replace(" ", "_").replace("-", "_")
    for k, v in CONDUCTOR_MATERIAL_COLORS.items():
        if k in key:
            return v

    return CONDUCTOR_MATERIAL_COLORS["default"]


# Row height used for wire / housing renders
ROW_H = 48   # px  (set once; must match verticalHeader default section size)


# ---------------------------------------------------------------------------
# ── Wire pixmap renderer ──────────────────────────────────────────────────
# ---------------------------------------------------------------------------
@_check_types.do
def make_wire_pixmap(primary_hex: str | None, stripe_hex: str | None,
                     material: str | None, width: int = 160,
                     height: int = ROW_H) -> QtGui.QPixmap:
    """
    Render a horizontal wire segment with:
      • Insulation body in primary_hex colour
      • Diagonal stripe bands in stripe_hex (if different from primary)
      • Right ~25 % of the wire "stripped" showing the bare conductor colour
      • Subtle 3-D cylindrical shading via a linear gradient highlight
      • Anti-aliased rounded endcaps

    Returns a QPixmap sized (width × height).
    """
    px = QtGui.QPixmap(width, height)
    px.fill(QtCore.Qt.GlobalColor.transparent)

    p = QtGui.QPainter(px)
    p.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing, True)
    p.setRenderHint(QtGui.QPainter.RenderHint.SmoothPixmapTransform, True)

    primary = QtGui.QColor(primary_hex or "#888888")
    stripe = QtGui.QColor(stripe_hex or primary_hex or "#888888")
    cond_hex = conductor_color(material)
    conductor = QtGui.QColor(cond_hex)

    # radius of insulation cylinder
    wire_r = height * 0.30
    cx_top = height / 2 - wire_r
    cx_bot = height / 2 + wire_r

    # x where stripping begins
    strip_x = int(width * 0.72)
    end_x = width - 4

    # ── helpers ──────────────────────────────────────────────────────
    @_check_types.do
    def _cylinder_gradient(color: QtGui.QColor, x0: float, x1: float) -> QtGui.QLinearGradient:  # NOQA
        """Vertical gradient faking cylindrical shading."""

        g = QtGui.QLinearGradient(x0, cx_top, x0, cx_bot)
        light = color.lighter(155)
        light.setAlpha(220)
        mid = color
        dark = color.darker(140)
        g.setColorAt(0.00, light)
        g.setColorAt(0.30, mid)
        g.setColorAt(0.70, mid)
        g.setColorAt(1.00, dark)
        return g

    # ── insulated section (left → strip_x) ──────────────────────────
    ins_rect = QtCore.QRectF(4, cx_top, strip_x - 4, wire_r * 2)

    # Base fill
    p.setBrush(QtGui.QBrush(_cylinder_gradient(primary, 4, strip_x)))
    p.setPen(QtCore.Qt.PenStyle.NoPen)
    p.drawRoundedRect(ins_rect, wire_r * 0.4, wire_r * 0.4)

    # Diagonal stripe bands (paint only if stripe differs from primary)
    has_stripe = stripe_hex and (stripe_hex.lower() != (primary_hex or "").lower())
    if has_stripe:
        p.save()
        clip = QtGui.QPainterPath()
        clip.addRoundedRect(ins_rect, wire_r * 0.4, wire_r * 0.4)
        p.setClipPath(clip)
        p.setBrush(QtGui.QBrush(stripe))
        p.setPen(QtCore.Qt.PenStyle.NoPen)

        # stripe width
        band_w = wire_r * 1.0

        # gap between stripe centres
        gap = wire_r * 1.8
        x = 4.0 - height
        while x < strip_x:
            poly = QtGui.QPolygonF([QtCore.QPointF(x, cx_top),
                              QtCore.QPointF(x + band_w, cx_top),
                              QtCore.QPointF(x + band_w + height, cx_bot),
                              QtCore.QPointF(x + height, cx_bot)])

            p.drawPolygon(poly)
            x += gap

        p.restore()

    # Re-apply cylinder gradient on top (semi-transparent for shine)
    shine = _cylinder_gradient(primary, 4, strip_x)
    shine.setColorAt(0.0, QtGui.QColor(255, 255, 255, 60))
    shine.setColorAt(0.3, QtGui.QColor(255, 255, 255, 0))
    shine.setColorAt(1.0, QtGui.QColor(0, 0, 0, 40))
    p.setBrush(QtGui.QBrush(shine))
    p.drawRoundedRect(ins_rect, wire_r * 0.4, wire_r * 0.4)

    # ── insulation cut edge (small taper) ───────────────────────────
    taper_w = 6
    taper_rect = QtCore.QRectF(strip_x - taper_w, cx_top, taper_w, wire_r * 2)
    taper_g = QtGui.QLinearGradient(strip_x - taper_w, 0, strip_x, 0)
    taper_g.setColorAt(0.0, primary)
    taper_g.setColorAt(1.0, primary.darker(180))
    p.setBrush(QtGui.QBrush(taper_g))
    p.setPen(QtCore.Qt.PenStyle.NoPen)
    p.drawRect(taper_rect)

    # ── conductor / stripped section (strip_x → end_x) ──────────────

    # conductor is thinner than insulation
    cond_r = wire_r * 0.52
    cond_top = height / 2 - cond_r
    cond_rect = QtCore.QRectF(strip_x, cond_top, end_x - strip_x, cond_r * 2)

    p.setBrush(QtGui.QBrush(_cylinder_gradient(conductor, strip_x, end_x)))
    p.setPen(QtCore.Qt.PenStyle.NoPen)
    p.drawRoundedRect(cond_rect, cond_r * 0.3, cond_r * 0.3)

    # Strand lines on conductor (fine horizontal lines)
    p.save()
    strand_pen = QtGui.QPen(conductor.darker(120))
    strand_pen.setWidthF(0.5)
    p.setPen(strand_pen)
    step = cond_r * 0.55
    for dy in [-step, 0, step]:
        y = height / 2 + dy
        if cond_top < y < cond_top + cond_r * 2:
            p.drawLine(QtCore.QPointF(strip_x + 2, y), QtCore.QPointF(end_x - 2, y))

    p.restore()

    # Conductor tip highlight
    tip_g = QtGui.QLinearGradient(end_x - 10, 0, end_x, 0)
    tip_g.setColorAt(0.0, QtGui.QColor(255, 255, 255, 0))
    tip_g.setColorAt(1.0, QtGui.QColor(255, 255, 255, 80))
    p.setBrush(QtGui.QBrush(tip_g))
    p.drawRoundedRect(cond_rect, cond_r * 0.3, cond_r * 0.3)

    # ── outline ─────────────────────────────────────────────────────
    out_pen = QtGui.QPen(QtGui.QColor(0, 0, 0, 80))
    out_pen.setWidthF(0.8)
    p.setPen(out_pen)
    p.setBrush(QtCore.Qt.BrushStyle.NoBrush)
    p.drawRoundedRect(ins_rect, wire_r * 0.4, wire_r * 0.4)
    p.drawRoundedRect(cond_rect, cond_r * 0.3, cond_r * 0.3)

    p.end()

    return px


# ---------------------------------------------------------------------------
# ── Housing / connector image renderer ───────────────────────────────────
# ---------------------------------------------------------------------------

@_check_types.do
def scale_housing_pixmap(src: QtGui.QPixmap, height: int = ROW_H) -> QtGui.QPixmap:
    """Scale a housing image to fit within a cell, preserving aspect ratio."""

    if src is None or src.isNull():
        return QtGui.QPixmap()

    return src.scaledToHeight(
        height - 6, QtCore.Qt.TransformationMode.SmoothTransformation)


@_check_types.do
def placeholder_connector_pixmap(name: str, height: int = ROW_H) -> QtGui.QPixmap:
    """
    Draw a minimal schematic connector symbol when no photo is available.
    Shows a rectangular housing outline with pin cavities.
    """
    w = max(height + 20, 64)
    h = height - 4
    px = QtGui.QPixmap(w, h)
    px.fill(QtCore.Qt.GlobalColor.transparent)

    p = QtGui.QPainter(px)
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

    p.end()

    return px


# ---------------------------------------------------------------------------
# ── Pixmap cache (keyed by colour/material strings) ──────────────────────
# ---------------------------------------------------------------------------
WIRE_PIXMAP_CACHE: dict[tuple, QtGui.QPixmap] = {}


@_check_types.do
def cached_wire_pixmap(primary: str | None, stripe: str | None,
                       material: str | None, width: int,
                       height: int) -> QtGui.QPixmap:
    """Execute the cached wire pixmap operation.

    UNKNOWN details are inferred from the callable name and signature.

    :param primary: Value for ``primary``.
    :type primary: str | None
    :param stripe: Value for ``stripe``.
    :type stripe: str | None
    :param material: Value for ``material``.
    :type material: str | None
    :param width: Value for ``width``.
    :type width: int
    :param height: Value for ``height``.
    :type height: int
    :returns: Return value. UNKNOWN details.
    :rtype: :class:`QPixmap`
    """

    key = (primary, stripe, material, width, height)

    if key not in WIRE_PIXMAP_CACHE:
        WIRE_PIXMAP_CACHE[key] = make_wire_pixmap(
            primary, stripe, material, width, height)

    return WIRE_PIXMAP_CACHE[key]
