# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

from typing import TYPE_CHECKING

import uuid as _uuid_module

import build123d

from . import base2d as _base2d
from ...geometry import point as _point
from ... import config as _config
from ... import color as _color
from ...gl import materials as _materials
from ...shapes import text as _text
from ... import utils as _utils


if TYPE_CHECKING:
    from ...database.project_db import pjt_cavity as _pjt_cavity
    from .. import cavity as _cavity


Config = _config.Config.editor2d

_ALIGN_BOTTOM_RIGHT = [build123d.TextAlign.RIGHT, build123d.TextAlign.BOTTOM]


class Cavity(_base2d.Base2D):
    """
    2D representation of a cavity for schematic view

    Renders only this cavity's own name -- RIGHT/BOTTOM-aligned text
    sitting just outside its owning housing's rectangle, a fixed gap
    above its terminal's own bracket -- on the VBO/shader
    pipeline (see ``objects2d/base2d.py``'s ``Base2D``), matching how
    ``Base3D`` subclasses render. ``position2d``/``angle2d`` are computed
    and persisted by the owning ``objects2d/housing.py``'s ``Housing``
    whenever its layout changes (see ``Housing._layout_children``) --
    this class only reacts to its own name changing, to rebuild its text
    mesh in place.
    """
    _parent: "_cavity.Cavity" = None
    db_obj: "_pjt_cavity.PJTCavity"

    def __init__(self, parent: "_cavity.Cavity",
                 db_obj: "_pjt_cavity.PJTCavity"):
        """Initialise the :class:`Cavity` instance.

        :param parent: Parent object.
        :type parent: :class:`_cavity.Cavity`
        :param db_obj: Database-backed object.
        :type db_obj: :class:`_pjt_cavity.PJTCavity`
        """

        # _mesh_args()/_build() (below) read self.db_obj -- set it before
        # that first call, same as objects3d/note.py's Note.__init__ does
        # (Base2D.__init__, which normally sets this, doesn't run until
        # after _build() since the VBO it builds is one of its own args).
        self.db_obj = db_obj

        # This cavity's own id into shapes.text's VBO registry -- generated
        # and owned here, exactly like objects3d/note.py's Note._text_uuid.
        self._text_uuid = str(_uuid_module.uuid4())

        position = db_obj.position2d
        angle = db_obj.angle2d
        scale = _point.Point(1.0, 1.0, 1.0)
        material = _materials.Generic(_color.Color(*Config.colors.label))

        parent.mainframe.editor2d.editor.context.acquire()
        vbo, _width, _height = self._build()
        super().__init__(parent, db_obj, vbo, angle, position, scale, material)
        parent.mainframe.editor2d.editor.context.release()

        self._housing = None  # Reference to parent housing

        self._name_cb = self.db_obj.bind(self._rebuild, 'name')

    def _mesh_args(self) -> dict:
        return dict(text=self.db_obj.name, font_size=Config.label.cavity_name_font_size,
                    text_align=_ALIGN_BOTTOM_RIGHT)

    def _build(self):
        """Build this cavity's name VBO (construction time only -- see
        :meth:`_rebuild` for in-place content updates).

        :returns: ``(vbo, width, height)``.
        """
        return _text.create_vbo(self._text_uuid, **self._mesh_args())

    def _rebuild(self, _entry=None):
        """Rebuild this cavity's name mesh in place from its current
        name and re-derive its OBB/AABB (``self._vbo.update`` recomputes
        the VBO's own ``local_obb``/``local_aabb``, but that doesn't by
        itself propagate to this object's world-space ``obb``/``aabb`` --
        see ``BaseVar._compute_obb``/``_compute_aabb``). Bound to fire
        whenever this cavity's own name changes.
        """
        self.editor2d.editor.context.acquire()
        try:
            vertices, faces, _width, _height = _text.create(**self._mesh_args())
            packed, count = _utils.compute_normals(vertices, faces)
            self._vbo.update(packed, count)
            self._compute_obb()
            self._compute_aabb()
        finally:
            self.editor2d.editor.context.release()

        self.editor2d.Refresh()

    def _delete(self):
        self._name_cb.unbind()
        super()._delete()
