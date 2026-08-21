# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

"""
Shape helper modules used to build reusable geometry and 2D overlays.

This subpackage collects small generators and painter-backed helpers used by
other parts of :mod:`harness_designer`.
"""
from typing import TYPE_CHECKING, Union as _Union

from .. import check_types as _check_types


if TYPE_CHECKING:
    from .. import ui as _ui
    from .. import splash as _splash


_arrow_vbo = None
_box_vbo = None
_circle_vbo = None
_cylinder_vbo = None
_disc_ring_vbo = None
_helix_vbo = None
_cylinder_helix_vbo = None
_stripe_cylinder_helix_vbo = None
_rectangle_vbo = None
_sphere_vbo = None


@_check_types.do
def cache_primitives(mainframe: "_ui.MainFrame", splash: _Union["_splash.Splash", None] = None):
    """Build every non-pooled primitive VBO (arrow/box/cylinder/sphere/etc.)
    plus the full text-glyph set, using *mainframe*'s already-current GL
    context. Called once, right after the mainframe first becomes visible
    (see ui/mainframe.py's ``_open_project``) -- these VBOs need a real GL
    context to upload to, so they can't be built any earlier in startup.

    :param mainframe: Mainframe whose 3D editor GL context is used.
    :type mainframe: _ui.MainFrame
    :param splash: If given, still-visible startup splash to post status
        text and a real progress bar (glyph count is known up front) to
        while these load. Left up to the caller to destroy afterward.
    :type splash: _splash.Splash | None
    """

    from PySide6.QtCore import Qt
    from PySide6.QtWidgets import QApplication

    from . import arrow
    from . import box
    from . import circle
    from . import cylinder
    from . import cylinder_helix
    from . import disc_ring
    from . import helix
    from . import rectangle
    from . import sphere
    from . import text

    global _arrow_vbo
    global _box_vbo
    global _circle_vbo
    global _cylinder_vbo
    global _disc_ring_vbo
    global _helix_vbo
    global _cylinder_helix_vbo
    global _stripe_cylinder_helix_vbo
    global _rectangle_vbo
    global _sphere_vbo

    @_check_types.do
    def _on_glyph_progress(done: int, total: int) -> None:
        if done == 0:
            splash.start_progress('Loading text glyphs...', total)
        else:
            splash.set_progress(done, f'Loading text glyphs... ({done}/{total})')

            if done == total:
                splash.end_progress_bar()

    QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
    try:
        with mainframe.editor3d.context:
            splash.SetText('Loading helix shape...')
            _helix_vbo = helix.create_vbo(1999)

            splash.SetText('Loading arrow shape...')
            _arrow_vbo = arrow.create_vbo()

            splash.SetText('Loading box shape...')
            _box_vbo = box.create_vbo()

            splash.SetText('Loading cylinder shape...')
            _cylinder_vbo = cylinder.create_vbo()

            splash.SetText('Loading cylinder helix shape...')
            _cylinder_helix_vbo = cylinder_helix.create_vbo()

            splash.SetText('Loading cylinder helix stripe shape...')
            _stripe_cylinder_helix_vbo = cylinder_helix.create_stripe_vbo()

            splash.SetText('Loading sphere shape...')
            _sphere_vbo = sphere.create_vbo()

            splash.SetText('Loading disc ring shape...')
            _disc_ring_vbo = disc_ring.create_vbo()

            text.build_chars(mainframe, _on_glyph_progress)

            # _rectangle_vbo = rectangle.create_vbo()
            # _circle_vbo = circle.create_vbo()
    finally:
        QApplication.restoreOverrideCursor()
