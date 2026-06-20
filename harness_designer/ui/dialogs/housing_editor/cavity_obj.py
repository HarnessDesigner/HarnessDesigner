# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

import math
from typing import TYPE_CHECKING

import numpy as np

from .... import objects as _objects
from ....objects.objects3d import base3d as _base3d
from ....geometry import point as _point
from ....shapes import box as _box
from ....gl import materials as _materials
from .... import color as _color
from ....geometry.decimal import Decimal as _d
from ....shapes import cylinder as _cylinder


if TYPE_CHECKING:
    from . import housing_editor as _housing_editor
    from ....database.global_db import cavity as _cavity
    from ....database.global_db import terminal as _terminal


class Cavity(_objects.ObjectBase):
    """Represent a cavity in :mod:`harness_designer.ui.dialogs.housing_editor.cavity_obj`.

    UNKNOWN details are inferred from the class name and surrounding code.
    """
    obj3d: "Cavity3D" = None

    def __init__(self, parent: "_housing_editor.HousingEditorDialog", cavity: "_cavity.Cavity"):
        """Initialise the :class:`Cavity` instance.

        UNKNOWN details are inferred from the callable name and signature.

        :param parent: Parent object.
        :type parent: :class:`_housing_editor.HousingEditorDialog`
        :param cavity: Value for ``cavity``.
        :type cavity: :class:`_cavity.Cavity`
        """
        super().__init__(parent, cavity)
        self.dialog = parent
        self.obj3d = Cavity3D(self, cavity)
        self.obj2d = None

        parent.add_object(self)


class Cavity3D(_base3d.Base3D):
    """Represent a cavity 3D in :mod:`harness_designer.ui.dialogs.housing_editor.cavity_obj`.

    UNKNOWN details are inferred from the class name and surrounding code.
    """
    db_obj: "_cavity.Cavity" = None

    def __init__(self, parent: Cavity, db_obj: "_cavity.Cavity"):
        """Initialise the :class:`Cavity3D` instance.

        UNKNOWN details are inferred from the callable name and signature.

        :param parent: Parent object.
        :type parent: :class:`Cavity`
        :param db_obj: Database-backed object.
        :type db_obj: :class:`_cavity.Cavity`
        """
        self.dialog: "_housing_editor.HousingEditorDialog" = parent.dialog
        self.editor3d = parent.dialog
        self.db_obj = db_obj

        self._angle = db_obj.angle3d
        self._scale = db_obj.scale
        self._position = db_obj.position3d

        material = _materials.Plastic(
            _color.Color(0.8, 0.3, 0.3, 1.0))

        parent.dialog.mainframe.editor3d.context.acquire()

        vbo = self.build()

        _base3d.Base3D.__init__(self, parent, db_obj, vbo,
                                self._angle, self._position, self._scale,
                                material)

        self._selected_material = _materials.Plastic(
            _color.Color(0.3, 1.0, 0.3, 1.0))

        self._is_visible = True
        self.autoplace = False
        self.editor3d.Refresh(False)
        parent.dialog.mainframe.editor3d.context.release()

    def set_selected(self, flag: bool):
        """Set the selected.

        UNKNOWN details are inferred from the callable name and signature.

        :param flag: Value for ``flag``.
        :type flag: bool
        """
        if flag:
            self.dialog.cavity_panel.set_cavity(self)
        else:
            self.dialog.cavity_panel.set_cavity(None)

        _base3d.Base3D.set_selected(self, flag)

    @property
    def compat_terminals(self) -> list["_terminal.Terminal"]:
        """Return the compat terminals.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: list['_terminal.Terminal']
        """
        return self.db_obj.compat_terminals

    @compat_terminals.setter
    def compat_terminals(self, value: list[str]):
        """Set the compat terminals.

        UNKNOWN details are inferred from the callable name and signature.

        :param value: Value to store or process.
        :type value: list[str]
        """
        pass

    @property
    def width(self) -> float:
        """Return the width.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: float
        """
        return self.db_obj.width

    @width.setter
    def width(self, value: float):
        """Set the width.

        UNKNOWN details are inferred from the callable name and signature.

        :param value: Value to store or process.
        :type value: float
        """
        self.db_obj.width = value
        self._scale.x = value

    @property
    def height(self) -> float:
        """Return the height.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: float
        """
        return self.db_obj.height

    @height.setter
    def height(self, value: float):
        """Set the height.

        UNKNOWN details are inferred from the callable name and signature.

        :param value: Value to store or process.
        :type value: float
        """
        self.db_obj.height = value
        self._scale.y = value

    @property
    def length(self) -> float:
        """Return the length.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: float
        """
        return self.db_obj.length

    @length.setter
    def length(self, value: float):
        """Set the length.

        UNKNOWN details are inferred from the callable name and signature.

        :param value: Value to store or process.
        :type value: float
        """
        self.db_obj.length = value
        self._scale.z = value

    @property
    def is_round(self) -> bool:
        """Return the is round.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: bool
        """
        return self.db_obj.round_terminal

    @is_round.setter
    def is_round(self, value: bool):
        """Set the is round.

        UNKNOWN details are inferred from the callable name and signature.

        :param value: Value to store or process.
        :type value: bool
        """
        self.db_obj.round_terminal = value
        self.build()

    @property
    def terminal_sizes(self) -> list[float]:
        """Return the terminal sizes.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: list[float]
        """
        return self.db_obj.terminal_sizes

    @terminal_sizes.setter
    def terminal_sizes(self, value: list[float]):
        """Set the terminal sizes.

        UNKNOWN details are inferred from the callable name and signature.

        :param value: Value to store or process.
        :type value: list[float]
        """
        self.db_obj.terminal_sizes = value

    @property
    def name(self) -> str:
        """Return the name.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: str
        """
        return self.db_obj.name

    @name.setter
    def name(self, value: str):
        """Set the name.

        UNKNOWN details are inferred from the callable name and signature.

        :param value: Value to store or process.
        :type value: str
        """
        self.db_obj.name = value

    @property
    def idx(self) -> int:
        """Return the idx.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: int
        """
        return self.db_obj.idx

    @idx.setter
    def idx(self, value: int):
        """Set the idx.

        UNKNOWN details are inferred from the callable name and signature.

        :param value: Value to store or process.
        :type value: int
        """
        self.db_obj.idx = value

    def apply_analysis(self, kind: str, params: dict, d_start: float, d_end: float) -> None:
        """Set position and orientation from surface analysis results."""

        is_round = (kind == 'circle')
        length = abs(float(d_end) - float(d_start))

        if is_round:
            width = float(params['radius']) * 2.0
            height = float(params['radius']) * 2.0
        else:
            width = float(params['half_w']) * 2.0
            height = float(params['half_h']) * 2.0

        self.db_obj.size = (width, height, length)

        n = np.array(params['normal'], dtype=np.float64)
        n /= np.linalg.norm(n) + 1e-12
        u = np.array(params['u'], dtype=np.float64)
        v = np.array(params['v'], dtype=np.float64)
        center = np.array(params['center'], dtype=np.float64)

        mid_d = (float(d_start) + float(d_end)) / 2.0
        pos = center + (mid_d - float(d_start)) * n

        # YXZ Euler decomposition matching the engine convention
        R = np.column_stack([u, v, n])
        pitch = math.degrees(float(np.arcsin(np.clip(-R[1, 2], -1.0, 1.0))))
        yaw = math.degrees(float(np.arctan2(R[0, 2], R[2, 2])))
        roll = math.degrees(float(np.arctan2(R[1, 0], R[1, 1])))

        ctx = self.dialog.context
        ctx.acquire()

        with self._angle:
            self._angle.x = pitch
            self._angle.y = yaw

        self._angle.z = roll

        with self._position:
            self._position.x = float(pos[0])
            self._position.y = float(pos[1])

        self._position.z = float(pos[2])

        ctx.release()

        self.is_round = is_round

    def build(self):
        """Execute the build operation.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Return value. UNKNOWN details.
        :rtype: UNKNOWN
        """
        self.editor3d.mainframe.editor3d.context.acquire()

        if self.is_round:
            width = height = float(_d(self.width) / _d(2.0))
            self._vbo = _cylinder.create_vbo()
        else:
            width = self.width
            height = self.height
            self._vbo = _box.create_vbo()

        self._vbo.acquire()

        with self._scale:
            self._scale.x = width
            self._scale.y = height

        self._scale.z = self.length

        self.editor3d.mainframe.editor3d.context.release()

        return self._vbo
