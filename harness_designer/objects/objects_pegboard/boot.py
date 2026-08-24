# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

from typing import TYPE_CHECKING

from . import base_pegboard as _base_pegboard
from ...geometry import point as _point
from ...geometry import angle as _angle
from ... import check_types as _check_types


if TYPE_CHECKING:
    from ...database.project_db import pjt_boot as _pjt_boot
    from .. import boot as _boot


class Boot(_base_pegboard.BasePegboard):
    """Represent a boot in :mod:`harness_designer.objects.objects_pegboard.boot`.

    UNKNOWN details are inferred from the class name and surrounding code.
    """
    _parent: "_boot.Boot" = None
    db_obj: "_pjt_boot.PJTBoot"

    @_check_types.do
    def __init__(self, parent: "_boot.Boot", db_obj: "_pjt_boot.PJTBoot"):
        """Initialise the :class:`Boot` instance.

        UNKNOWN details are inferred from the callable name and signature.

        :param parent: Parent object.
        :type parent: :class:`_boot.Boot`
        :param db_obj: Database-backed object.
        :type db_obj: :class:`_pjt_boot.PJTBoot`
        """

        # TODO: A boot will need a real peg-board presence (it's the
        #       other thing, besides a wire service loop, that can sit at
        #       a housing's cable-exit and needs to be visible there --
        #       see wire_service_loop.py's own docstring: "the only time
        #       the wire service loops will be rendered is if there is no
        #       boot or if the boot is not visible"). PJTBoot currently
        #       has no pegboard mixins at all (no Position/Angle/Visible
        #       PegboardMixin -- checked, unlike wire/bundle/transition/
        #       housing which already have them), so this needs a
        #       database change first (add those mixins/columns, same
        #       pattern as the other anchor types) before this class can
        #       do anything real. Revisit once the database side is
        #       worked out.
        super().__init__(parent, db_obj, None, None,
                         None, None, None)

    def render(self, shaders):
        pass
