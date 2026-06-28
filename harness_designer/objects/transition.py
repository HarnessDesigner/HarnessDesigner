# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

from typing import TYPE_CHECKING

from . import ObjectBase as _ObjectBase
from .objects2d import transition as _transition_2d
from .objects3d import transition as _transition_3d


if TYPE_CHECKING:
    from .. import ui as _ui
    from ..database.project_db import pjt_transition as _pjt_transition


class Transition(_ObjectBase):
    """Represent a transition in :mod:`harness_designer.objects.transition`.

    UNKNOWN details are inferred from the class name and surrounding code.
    """
    obj2d: _transition_2d.Transition = None
    obj3d: _transition_3d.Transition = None

    def __init__(self, mainframe: "_ui.MainFrame",
                 db_obj: "_pjt_transition.PJTTransition", project_load=False):
        """Initialise the :class:`Transition` instance.

        UNKNOWN details are inferred from the callable name and signature.

        :param mainframe: Main application frame.
        :type mainframe: :class:`_ui.MainFrame`
        :param db_obj: Database-backed object.
        :type db_obj: :class:`_pjt_transition.PJTTransition`
        """

        db_obj.set_object(self)
        db_obj.add_object(self)

        super().__init__(mainframe, db_obj)

        self.obj2d = _transition_2d.Transition(self, db_obj)
        self.obj3d = _transition_3d.Transition(self, db_obj)
        self.mainframe.add_object(self)
