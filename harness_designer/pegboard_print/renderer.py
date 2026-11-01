# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

"""
Draws one piece of the peg board at an exact millimetres-per-pixel.

The peg board canvas is a locked top-down orthographic view whose scale is
``camera.distance / 1000`` world millimetres per pixel (see
``gl/canvas_pegboard/camera.py``), so a piece of the board is rendered by
pointing that same camera at the piece's centre, setting the distance for the
wanted millimetres per pixel, and running the canvas's normal ``_on_draw`` into
an offscreen framebuffer of the piece's pixel size. Every object the canvas
draws comes along, the floating wire tables and concentric sections included,
exactly as they look on screen.

Everything the render changes on the live canvas (camera, size, selection,
floor, clear colour) is put back before it returns, with no event processing in
between, so the editor never paints in the print state.
"""

from typing import TYPE_CHECKING

from OpenGL import GL
from PySide6 import QtGui, QtOpenGL

from ..geometry import point as _point

if TYPE_CHECKING:
    from ..gl.canvas_pegboard import canvas as _canvas


# Multisampling for the print render (falls back to none if the driver refuses).
_SAMPLES = 4


def _no_op(*_, **__) -> None:
    """Stands in for a draw method that should draw nothing."""


def content_bounds(canvas: "_canvas.Canvas") -> tuple[float, float, float, float] | None:
    """Bounding box of everything visible on the peg board.

    :param canvas: The peg board's canvas.
    :returns: ``(x0, z0, x1, z1)`` in world mm, or ``None`` when empty.
    """
    x0 = z0 = float('inf')
    x1 = z1 = float('-inf')

    for obj in list(canvas._objects):  # NOQA
        view = canvas._get_view_object(obj)  # NOQA
        if view is None or not getattr(view, 'is_visible', True):
            continue

        # A floating table whose owner is hidden is not drawn either.
        if getattr(view, '_anchor_is_visible', True) is False:
            continue

        bounds = view.get_bounds()
        if bounds is None:
            continue

        left, top, right, bottom = bounds
        if not all(v == v and abs(v) != float('inf') for v in bounds):
            continue

        x0 = min(x0, left)
        z0 = min(z0, top)
        x1 = max(x1, right)
        z1 = max(z1, bottom)

    if x0 == float('inf') or x1 <= x0 or z1 <= z0:
        return None

    return x0, z0, x1, z1


def _make_fbo(width: int, height: int) -> QtOpenGL.QOpenGLFramebufferObject:
    """An offscreen framebuffer with depth, multisampled when it can be."""
    for samples in (_SAMPLES, 0):
        fmt = QtOpenGL.QOpenGLFramebufferObjectFormat()
        fmt.setAttachment(QtOpenGL.QOpenGLFramebufferObject.Attachment.CombinedDepthStencil)
        fmt.setSamples(samples)

        fbo = QtOpenGL.QOpenGLFramebufferObject(width, height, fmt)
        if fbo.isValid():
            return fbo

    raise RuntimeError(f'Could not create a {width} x {height} offscreen framebuffer.')


def render_tile(canvas: "_canvas.Canvas", left: float, top: float, width_px: int,
                height_px: int, mm_per_pixel: float) -> QtGui.QImage:
    """Render the part of the peg board whose top-left corner is (*left*, *top*).

    :param canvas: The peg board's canvas.
    :param left: World X of the picture's left edge, mm.
    :param top: World Z of the picture's top edge, mm.
    :param width_px: Picture width in pixels.
    :param height_px: Picture height in pixels.
    :param mm_per_pixel: World millimetres each pixel covers.
    :returns: An opaque picture, white where nothing is drawn.
    """
    camera = canvas.camera

    old_size = canvas.size
    old_x, _, old_z = camera.focal_position.as_float
    old_distance = camera.distance
    old_min_distance = camera._min_distance  # NOQA

    # The selected object is drawn in its own overlay pass, and a floating
    # table or section draws a selection ring of its own.
    selected = canvas._selected  # NOQA
    selected_view = None if selected is None else canvas._get_view_object(selected)  # NOQA
    ring_patched = selected_view is not None and hasattr(selected_view, '_render_selection_border')

    with canvas.context:
        fbo = _make_fbo(width_px, height_px)

        try:
            canvas._selected = None  # NOQA
            canvas._render_floor_after = _no_op  # NOQA
            if ring_patched:
                selected_view._render_selection_border = _no_op  # NOQA

            canvas.size = (width_px, height_px)

            # This camera's "distance" is its zoom, clamped to a range meant for
            # interactive use; a big enlargement needs finer than that.
            distance = mm_per_pixel * 1000.0
            camera._min_distance = min(old_min_distance, distance / 2.0)  # NOQA
            camera.CenterOn(_point.Point(left + width_px * mm_per_pixel / 2.0, 0.0,
                                         top + height_px * mm_per_pixel / 2.0))
            camera.distance = distance

            # A camera that did not move (same spot, same zoom) would not be
            # marked dirty, and so would keep the projection built for the
            # previous picture size.
            camera._is_dirty = True  # NOQA

            fbo.bind()
            GL.glViewport(0, 0, width_px, height_px)
            GL.glClearColor(1.0, 1.0, 1.0, 1.0)

            canvas._on_draw()  # NOQA

            # Blending leaves translucent parts with alpha below 1; the picture
            # is printed on white paper, so make every pixel opaque without
            # touching its colour.
            GL.glColorMask(GL.GL_FALSE, GL.GL_FALSE, GL.GL_FALSE, GL.GL_TRUE)
            GL.glClearColor(0.0, 0.0, 0.0, 1.0)
            GL.glClear(GL.GL_COLOR_BUFFER_BIT)
            GL.glColorMask(GL.GL_TRUE, GL.GL_TRUE, GL.GL_TRUE, GL.GL_TRUE)

            image = fbo.toImage()
            fbo.release()

        finally:
            GL.glColorMask(GL.GL_TRUE, GL.GL_TRUE, GL.GL_TRUE, GL.GL_TRUE)
            GL.glBindFramebuffer(GL.GL_FRAMEBUFFER, canvas.defaultFramebufferObject())
            GL.glViewport(0, 0, *old_size)
            GL.glClearColor(*canvas.config.background_color)

            canvas.__dict__.pop('_render_floor_after', None)
            if ring_patched:
                selected_view.__dict__.pop('_render_selection_border', None)
            canvas._selected = selected  # NOQA

            canvas.size = old_size
            camera.CenterOn(_point.Point(old_x, 0.0, old_z))
            camera.distance = old_distance
            camera._min_distance = old_min_distance  # NOQA
            camera._is_dirty = True  # NOQA

            del fbo

    canvas.update()
    return image.convertToFormat(QtGui.QImage.Format.Format_RGB32)
