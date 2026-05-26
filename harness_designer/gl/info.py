# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

"""
gl/info.py — query OpenGL capabilities.

wx: created a 1×1 glcanvas.GLCanvas as a temporary GL context host,
    called canvas.SetCurrent(context), then queried GL strings.

Qt:  QOffscreenSurface + QOpenGLContext achieves the same thing without
     needing a visible widget.  This matches the note in the Phase 1
     CONVERSION_LOG: "Temporary hidden wx.Frame for GL context creation →
     removed; _gl_info.get() called directly (GL info module will be
     updated in Phase 4 to use an offscreen surface)".

The public API is identical: call get(parent) once to collect and cache,
then call get() (no argument) to retrieve cached info.
"""

from OpenGL import GL
from PySide6.QtGui import QOffscreenSurface, QOpenGLContext, QSurfaceFormat


def _safe_gl_get_string(param) -> str:
    """Execute the safe GL get string operation.

    UNKNOWN details are inferred from the callable name and signature.

    :param param: Value for ``param``.
    :type param: UNKNOWN
    :returns: Return value. UNKNOWN details.
    :rtype: str
    """
    try:
        result = GL.glGetString(param)
        if result is None:
            return "N/A"
        return result.decode('utf-8') if isinstance(result, bytes) else str(result)
    except Exception as e:  # noqa: BLE001
        return f"Error: {e}"


def _safe_gl_get_integer(param):
    """Execute the safe GL get integer operation.

    UNKNOWN details are inferred from the callable name and signature.

    :param param: Value for ``param``.
    :type param: UNKNOWN
    :returns: Return value. UNKNOWN details.
    :rtype: UNKNOWN
    """
    try:
        return GL.glGetInteger(param)
    except Exception:  # NOQA
        return None


def _safe_gl_get_integerv(param):
    """Execute the safe GL get integerv operation.

    UNKNOWN details are inferred from the callable name and signature.

    :param param: Value for ``param``.
    :type param: UNKNOWN
    :returns: Return value. UNKNOWN details.
    :rtype: UNKNOWN
    """
    try:
        return GL.glGetIntegerv(param)
    except Exception:  # NOQA
        return None


_info = None


def get(parent=None):
    """
    Get or collect OpenGL information.

    When called WITH a parent (any QWidget or None):
        Creates a QOffscreenSurface + QOpenGLContext, activates it,
        queries GL capabilities, caches, and returns None.

    When called WITHOUT a parent:
        Returns the previously cached dict.
        Raises RuntimeError if info was never collected.
    """
    global _info

    if _info is not None:
        return _info

    # --- collect via offscreen surface (replaces temporary GLCanvas) ---

    # Use the default format that was set in app.py
    # This ensures the info context is compatible with widget contexts
    fmt = QSurfaceFormat.defaultFormat()

    surface = QOffscreenSurface()
    surface.setFormat(fmt)
    surface.create()

    context = QOpenGLContext()
    context.setFormat(fmt)
    context.create()
    context.makeCurrent(surface)

    try:
        _info = {
            'GFX Vendor':    _safe_gl_get_string(GL.GL_VENDOR),
            'GFX Adapter':   _safe_gl_get_string(GL.GL_RENDERER),
            'OpenGL Version': _safe_gl_get_string(GL.GL_VERSION),
            'GLSL Version':  _safe_gl_get_string(GL.GL_SHADING_LANGUAGE_VERSION),
            'Extension Count': _safe_gl_get_integer(GL.GL_NUM_EXTENSIONS),
            'Element Limits': {
                'Max Elements Indices':  _safe_gl_get_integer(GL.GL_MAX_ELEMENTS_INDICES),
                'Max Elements Vertices': _safe_gl_get_integer(GL.GL_MAX_ELEMENTS_VERTICES),
            },
            'Texture Capabilities': {
                'Max Texture Size':          _safe_gl_get_integer(GL.GL_MAX_TEXTURE_SIZE),
                'Max 3D Texture Size':       _safe_gl_get_integer(GL.GL_MAX_3D_TEXTURE_SIZE),
                'Max Cube Map Texture Size': _safe_gl_get_integer(GL.GL_MAX_CUBE_MAP_TEXTURE_SIZE),
                'Max Array Texture Layers':  _safe_gl_get_integer(GL.GL_MAX_ARRAY_TEXTURE_LAYERS),
                'Max Texture Image Units':   _safe_gl_get_integer(GL.GL_MAX_TEXTURE_IMAGE_UNITS),
            },
        }
    finally:
        context.doneCurrent()
        surface.destroy()

    return None
