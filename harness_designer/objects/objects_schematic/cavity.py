# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

from typing import TYPE_CHECKING

import uuid as _uuid_module

import build123d

from . import base_schematic as _base_schematic
from ...geometry import point as _point
from ... import config as _config
from ... import color as _color
from ...gl import materials as _materials
from ...shapes import text as _text
from ... import utils as _utils
from ... import check_types as _check_types


if TYPE_CHECKING:
    from ...database.project_db import pjt_cavity as _pjt_cavity
    from .. import cavity as _cavity


Config = _config.Config.editor2d

_ALIGN_BOTTOM_RIGHT = [build123d.TextAlign.RIGHT, build123d.TextAlign.BOTTOM]


# TODO: add render function

class Cavity(_base_schematic.BaseSchematic):
    """
    2D representation of a cavity for schematic view

    Renders only this cavity's own name -- RIGHT/BOTTOM-aligned text
    sitting just outside its owning housing's rectangle, a fixed gap
    above its terminal's own bracket -- on the VBO/shader
    pipeline (see ``objects_schematic/base_schematic.py``'s ``BaseSchematic``), matching how
    ``Base3D`` subclasses render. ``position2d``/``angle2d`` are computed
    and persisted by the owning ``objects_schematic/housing.py``'s ``Housing``
    whenever its layout changes (see ``Housing._layout_children``).

    Owns two DB binds on itself: its own ``'name'`` (rebuilds this
    cavity's own text mesh, and tells the housing to update its cached
    copy -- see :meth:`_on_name_changed`) and the synthetic
    ``'terminal_id'`` tag (tells the housing to reposition this
    cavity's seated terminal -- see :meth:`_on_terminal_changed`). The
    housing itself binds to neither; both flow from here instead.
    """
    _parent: "_cavity.Cavity" = None
    db_obj: "_pjt_cavity.PJTCavity"

    @_check_types.do
    def __init__(self, parent: "_cavity.Cavity",
                 db_obj: "_pjt_cavity.PJTCavity"):
        """Initialise the :class:`Cavity` instance.

        :param parent: Parent object.
        :type parent: :class:`_cavity.Cavity`
        :param db_obj: Database-backed object.
        :type db_obj: :class:`_pjt_cavity.PJTCavity`
        """

        # _mesh_args()/_build() (below) read self.db_obj -- set it before
        # that first call, same as objects_3d/note.py's Note.__init__ does
        # (BaseSchematic.__init__, which normally sets this, doesn't run until
        # after _build() since the VBO it builds is one of its own args).
        self.db_obj = db_obj

        # This cavity's own id into shapes.text's VBO registry -- generated
        # and owned here, exactly like objects_3d/note.py's Note._text_uuid.
        self._text_uuid = str(_uuid_module.uuid4())

        position = db_obj.position2d
        angle = db_obj.angle2d
        scale = _point.Point(1.0, 1.0, 1.0)
        material = _materials.Generic(_color.Color(*Config.colors.label))

        with parent.mainframe.editor2d.editor.context:
            vbo, _width, _height = self._build()
            super().__init__(parent, db_obj, vbo, angle, position, scale, material)

        self._name_cb = self.db_obj.bind(self._on_name_changed, 'name')

        # Fires whenever a terminal is attached, detached, or moved
        # to/from this cavity -- see database/project_db/pjt_terminal.py's
        # PJTTerminal.cavity_id setter, which is what actually calls
        # _populate('terminal_id') on this cavity's own db_obj (there's
        # no real terminal_id column on pjt_cavities to bind to
        # directly, so the terminal's own setter fires it by hand).
        self._terminal_cb = self.db_obj.bind(self._on_terminal_changed, 'terminal_id')

    @property
    @_check_types.do
    def housing(self):
        """This cavity's owning ``Housing2D``, or ``None``.

        Resolved on demand via ``self.parent.housing`` (see
        ``objects/cavity.py``'s ``Cavity``) rather than cached -- by the
        time either bound callback below fires, this cavity's housing
        is guaranteed to already exist (never at this object's own
        construction time).
        """
        housing_obj = self.parent.housing
        if housing_obj is None:
            return None

        return housing_obj.objschematic

    @_check_types.do
    def _on_name_changed(self, _entry=None):
        """Rebuild this cavity's own name mesh (see :meth:`_rebuild`)
        and tell the owning housing to update its cached copy -- a
        cavity rename can reorder its own slot and change the
        housing-wide max-cavity-name-width, so the housing does a full
        rebuild (see ``objects_schematic/housing.py``'s ``Housing.
        update_cavity_name``).
        """
        self._rebuild()

        housing = self.housing
        if housing is not None:
            housing.update_cavity_name(self.db_obj.db_id, self.db_obj.name)

    @_check_types.do
    def _on_terminal_changed(self, _entry=None):
        """Tell the owning housing to (re)position this cavity's own
        seated terminal -- see ``objects_schematic/housing.py``'s ``Housing.
        update_terminal_name``. Never a full housing rebuild -- seating
        a terminal doesn't affect sort order or the housing's own
        layout constants, only whether this one row shows a bracket and
        wire-stub line at all.
        """
        housing = self.housing
        if housing is None:
            return

        terminal = self.db_obj.terminal
        if terminal is None:
            housing.update_terminal_name(self.db_obj.db_id, None, None)
        else:
            housing.update_terminal_name(self.db_obj.db_id, terminal.db_id, terminal.name)

    @_check_types.do
    def _mesh_args(self) -> dict:
        return dict(text=self.db_obj.name, font_size=Config.label.cavity_name_font_size,
                    text_align=_ALIGN_BOTTOM_RIGHT)

    @_check_types.do
    def _build(self):
        """Build this cavity's name VBO (construction time only -- see
        :meth:`_rebuild` for in-place content updates).

        :returns: ``(vbo, width, height)``.
        """
        return _text.create_vbo(self._text_uuid, **self._mesh_args())

    @_check_types.do
    def _rebuild(self, _entry=None):
        """Rebuild this cavity's name mesh in place from its current
        name and re-derive its OBB/AABB (``self._vbo.update`` recomputes
        the VBO's own ``local_obb``/``local_aabb``, but that doesn't by
        itself propagate to this object's world-space ``obb``/``aabb`` --
        see ``BaseVar._compute_obb``/``_compute_aabb``). Bound to fire
        whenever this cavity's own name changes.
        """
        with self.editor2d.editor.context:
            vertices, faces, _width, _height = _text.create(**self._mesh_args())
            packed, count = _utils.compute_normals(vertices, faces)
            self._vbo.update(packed, count)
            self._compute_obb()
            self._compute_aabb()

        self.editor2d.Refresh()

    @_check_types.do
    def _delete(self):
        self._name_cb.unbind()
        self._terminal_cb.unbind()
        super()._delete()
