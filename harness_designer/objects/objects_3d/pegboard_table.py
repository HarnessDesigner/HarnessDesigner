# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

from typing import TYPE_CHECKING

from . import base_3d as _base_3d
from ... import check_types as _check_types


if TYPE_CHECKING:
    from .. import pegboard_table as _pegboard_table
    from ...database.project_db import pjt_pegboard_table as _pjt_pegboard_table


class PegboardTable(_base_3d.Base3D):
    """Peg-board floating wire table -- has no 3D-view presence at all
    (it's a peg-board-only overlay, never placed in the 3D scene), so
    this constructs as a fully inert placeholder, same shape as
    ``objects_3d.note.Note``'s own no-vbo/no-position branch: ``vbo``/
    ``angle``/``position``/``scale``/``material`` all ``None``, marked
    not-visible so ``render()`` (which already no-ops on ``vbo is
    None``, see ``BaseVar.render``) has nothing to do regardless.
    """

    parent: "_pegboard_table.PegboardTable" = None
    db_obj: "_pjt_pegboard_table.PJTPegboardTable" = None

    @_check_types.do
    def __init__(self, parent: "_pegboard_table.PegboardTable",
                 db_obj: "_pjt_pegboard_table.PJTPegboardTable"):
        """Initialise the :class:`PegboardTable` instance.

        :param parent: Parent object.
        :type parent: :class:`_pegboard_table.PegboardTable`
        :param db_obj: Database-backed object.
        :type db_obj: :class:`_pjt_pegboard_table.PJTPegboardTable`
        """
        super().__init__(parent, db_obj, None, None, None, None, None)
        self._is_visible = False
