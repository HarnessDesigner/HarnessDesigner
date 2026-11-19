# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

"""The application's default ``QSurfaceFormat`` and the canvases' texture
format, both built from ``Config.graphics`` (Preferences > Graphics) and
``Config.debug.opengl`` (Debug Settings).

Qt reads the default surface format when an OpenGL context is created, so
:func:`build_default_format` has to run, and its result be made the default
with ``QSurfaceFormat.setDefaultFormat``, before ANY context exists (that
includes the GL information query): ``App._init`` does both. The values are
therefore read once per run and a change in the dialog needs a restart.
"""

from OpenGL import GL
from PySide6 import QtGui
from PySide6 import QtOpenGLWidgets

from .. import config as _config
from .. import check_types as _check_types


Config = _config.Config

# (label, value) pairs, in the order the Preferences dialog lists them.
BUFFERING_CHOICES: list[tuple[str, str]] = [
    ('Driver default', 'default'),
    ('Single buffer', 'single'),
    ('Double buffer', 'double'),
    ('Triple buffer', 'triple')
]

TEXTURE_FORMAT_CHOICES: list[tuple[str, str]] = [
    ('RGBA8 (8 bits per channel)', 'RGBA8'),
    ('RGB10_A2 (10 bit colour, 2 bit alpha)', 'RGB10_A2'),
    ('RGBA16F (16 bit float per channel)', 'RGBA16F')
]

UPDATE_BEHAVIOR_CHOICES: list[tuple[str, str]] = [
    ('Discard each frame (Qt default)', 'no_partial'),
    ('Keep the last frame', 'partial')
]

_UpdateBehavior = QtOpenGLWidgets.QOpenGLWidget.UpdateBehavior

_UPDATE_BEHAVIORS: dict[str, QtOpenGLWidgets.QOpenGLWidget.UpdateBehavior] = {
    'no_partial': _UpdateBehavior.NoPartialUpdate,
    'partial': _UpdateBehavior.PartialUpdate
}

_SwapBehavior = QtGui.QSurfaceFormat.SwapBehavior

_SWAP_BEHAVIORS: dict[str, QtGui.QSurfaceFormat.SwapBehavior] = {
    'default': _SwapBehavior.DefaultSwapBehavior,
    'single': _SwapBehavior.SingleBuffer,
    'double': _SwapBehavior.DoubleBuffer,
    'triple': _SwapBehavior.TripleBuffer
}

_TEXTURE_FORMATS: dict[str, int] = {
    'RGBA8': GL.GL_RGBA8,
    'RGB10_A2': GL.GL_RGB10_A2,
    'RGBA16F': GL.GL_RGBA16F
}


@_check_types.do
def build_default_format() -> QtGui.QSurfaceFormat:
    """
    The surface format every OpenGL widget and context is created with.

    :returns: The format to hand to ``QSurfaceFormat.setDefaultFormat``.
    :rtype: QtGui.QSurfaceFormat
    """

    graphics = Config.graphics

    fmt = QtGui.QSurfaceFormat()
    fmt.setDepthBufferSize(24)

    # MSAA -- QOpenGLWidget renders into a multisampled FBO and resolves it
    # automatically. Framebuffer readbacks must go through
    # grabFramebuffer() (resolved), not raw glReadPixels.
    fmt.setSamples(graphics.msaa_samples)

    # Swap interval 1 = every window flush waits for the monitor's vertical
    # blank (Qt's default); 0 = no wait. With the wait, the 3D view sat at
    # ~35 fps (a repaint per mouse move plus the axis gizmo's own flush).
    if graphics.vsync:
        fmt.setSwapInterval(1)
    else:
        fmt.setSwapInterval(0)

    fmt.setSwapBehavior(_SWAP_BEHAVIORS[graphics.buffering])

    fmt.setVersion(3, 3)
    fmt.setProfile(QtGui.QSurfaceFormat.OpenGLContextProfile.CompatibilityProfile)

    # No colour space is requested for sRGB: QOpenGLWidget ignores
    # QSurfaceFormat.setColorSpace (measured: the framebuffer stays linear).
    # An sRGB framebuffer is the SRGB8_ALPHA8 texture format, see
    # texture_format(), plus GL_FRAMEBUFFER_SRGB in CanvasBase.initializeGL.

    if Config.debug.opengl.debug_context:
        fmt.setOption(QtGui.QSurfaceFormat.FormatOption.DebugContext)

    return fmt


@_check_types.do
def update_behavior() -> QtOpenGLWidgets.QOpenGLWidget.UpdateBehavior:
    """
    Whether a canvas keeps its last frame between paints
    (``Config.graphics.update_behavior``), for ``QOpenGLWidget.setUpdateBehavior``.

    :rtype: QtOpenGLWidgets.QOpenGLWidget.UpdateBehavior
    """

    return _UPDATE_BEHAVIORS[Config.graphics.update_behavior]


@_check_types.do
def texture_format() -> int:
    """
    The internal format of the texture a canvas renders into, as the OpenGL
    enum ``QOpenGLWidget.setTextureFormat`` takes. With
    ``Config.graphics.srgb`` on it is ``SRGB8_ALPHA8`` whatever
    ``texture_format`` says (an sRGB buffer is 8 bit).

    :rtype: int
    """

    if Config.graphics.srgb:
        return GL.GL_SRGB8_ALPHA8

    return _TEXTURE_FORMATS[Config.graphics.texture_format]
