# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

from typing import TYPE_CHECKING

from . import ObjectBase as _ObjectBase
from .objects2d import housing as _housing_2d
from .objects3d import housing as _housing_3d

from . import cavity as _cavity
from . import tpa_lock as _tpa_lock
from . import cpa_lock as _cpa_lock
from . import seal as _seal
from . import cover as _cover
from . import boot as _boot


if TYPE_CHECKING:
    from .. import ui as _ui
    from ..database.project_db import pjt_housing as _pjt_housing
    from ..database.project_db import pjt_cavity as _pjt_cavity
    from ..database.project_db import pjt_seal as _pjt_seal
    from ..database.project_db import pjt_tpa_lock as _pjt_tpa_lock
    from ..database.project_db import pjt_cpa_lock as _pjt_cpa_lock
    from ..database.project_db import pjt_cover as _pjt_cover
    from ..database.project_db import pjt_boot as _pjt_boot


class Housing(_ObjectBase):
    """Represent a housing in :mod:`harness_designer.objects.housing`.

    UNKNOWN details are inferred from the class name and surrounding code.
    """
    obj2d: _housing_2d.Housing = None
    obj3d: _housing_3d.Housing = None

    db_obj: "_pjt_housing.PJTHousing" = None

    def __init__(self, mainframe: "_ui.MainFrame",
                 db_obj: "_pjt_housing.PJTHousing"):
        """Initialise the :class:`Housing` instance.

        UNKNOWN details are inferred from the callable name and signature.

        :param mainframe: Main application frame.
        :type mainframe: :class:`_ui.MainFrame`
        :param db_obj: Database-backed object.
        :type db_obj: :class:`_pjt_housing.PJTHousing`
        """

        db_obj.set_object(self)
        db_obj.add_object(self)

        super().__init__(mainframe, db_obj)

        self.obj2d = _housing_2d.Housing(self, db_obj)
        self.obj3d = _housing_3d.Housing(self, db_obj)

        self.cavities: dict[int, _cavity.Cavity]
        self.seals = []
        self.tpa_locks = []
        self.cpa_locks = []
        self.cover = None
        self.boot = None
        self.mainframe.add_object(self)

    def add_cavity(self, cavity: "_pjt_cavity.PJTCavity"):
        """Add a cavity.

        UNKNOWN details are inferred from the callable name and signature.

        :param cavity: Value for ``cavity``.
        :type cavity: :class:`_pjt_cavity.PJTCavity`
        """
        pass

    def add_tpa_lock(self, tpa_lock: "_pjt_tpa_lock.PJTTPALock"):
        """Add a TPA lock.

        UNKNOWN details are inferred from the callable name and signature.

        :param tpa_lock: Value for ``tpa_lock``.
        :type tpa_lock: :class:`_pjt_tpa_lock.PJTTPALock`
        """
        pass

    def add_cpa_lock(self, cpa_lock: "_pjt_cpa_lock.PJTCPALock"):
        """Add a CPA lock.

        UNKNOWN details are inferred from the callable name and signature.

        :param cpa_lock: Value for ``cpa_lock``.
        :type cpa_lock: :class:`_pjt_cpa_lock.PJTCPALock`
        """
        pass

    def add_boot(self, boot: "_pjt_boot.PJTBoot"):
        """Add a boot.

        UNKNOWN details are inferred from the callable name and signature.

        :param boot: Value for ``boot``.
        :type boot: :class:`_pjt_boot.PJTBoot`
        """
        pass

    def add_cover(self, cover: "_pjt_cover.PJTCover"):
        """Add a cover.

        UNKNOWN details are inferred from the callable name and signature.

        :param cover: Value for ``cover``.
        :type cover: :class:`_pjt_cover.PJTCover`
        """
        pass

    def add_seal(self, seal: "_pjt_seal.PJTSeal"):
        """Add a seal.

        UNKNOWN details are inferred from the callable name and signature.

        :param seal: Value for ``seal``.
        :type seal: :class:`_pjt_seal.PJTSeal`
        """
        pass
