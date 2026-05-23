# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

from typing import TYPE_CHECKING

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
    obj3d: "Cavity3D" = None

    def __init__(self, parent: "_housing_editor.HousingEditorDialog", cavity: "_cavity.Cavity"):
        super().__init__(parent, cavity)
        self.dialog = parent
        self.obj3d = Cavity3D(self, cavity)
        self.obj2d = None

        parent.add_object(self)


class Cavity3D(_base3d.Base3D):
    db_obj: "_cavity.Cavity" = None

    def __init__(self, parent: Cavity, db_obj: "_cavity.Cavity"):
        self.dialog: "_housing_editor.HousingEditorDialog" = parent.dialog

        angle = db_obj.angle3d
        position = db_obj.position3d.copy()

        self._scale = _point.Point(1.0, 1.0, 1.0)

        material = _materials.Plastic(
            _color.Color(0.8, 0.3, 0.3, 1.0))

        self.db_obj = db_obj

        parent.dialog.context.acquire()

        vbo = self.build()

        _base3d.Base3D.__init__(self, parent, db_obj, vbo,
                                angle, position, self._scale,
                                material)

        self._selected_material = _materials.Plastic(
            _color.Color(0.3, 1.0, 0.3, 1.0))

        self._is_visible = True
        self.autoplace = False
        self.editor3d.Refresh(False)
        parent.dialog.context.release()

    def set_selected(self, flag: bool):
        if flag:
            self.dialog.cavity_panel.set_cavity(self)
        else:
            self.dialog.cavity_panel.set_cavity(None)

        _base3d.Base3D.set_selected(self, flag)

    @property
    def compat_terminals(self) -> list["_terminal.Terminal"]:
        return self.db_obj.compat_terminals

    @compat_terminals.setter
    def compat_terminals(self, value: list[str]):
        pass

    @property
    def width(self) -> float:
        return self.db_obj.width

    @width.setter
    def width(self, value: float):
        self.db_obj.width = value
        self._scale.x = value

    @property
    def height(self) -> float:
        return self.db_obj.height

    @height.setter
    def height(self, value: float):
        self.db_obj.height = value
        self._scale.y = value

    @property
    def length(self) -> float:
        return self.db_obj.length

    @length.setter
    def length(self, value: float):
        self.db_obj.length = value
        self._scale.z = value

    @property
    def is_round(self) -> bool:
        return self.db_obj.round_terminal

    @is_round.setter
    def is_round(self, value: bool):
        self.db_obj.round_terminal = value
        self.build()

    @property
    def terminal_sizes(self) -> list[float]:
        return self.db_obj.terminal_sizes

    @terminal_sizes.setter
    def terminal_sizes(self, value: list[float]):
        self.db_obj.terminal_sizes = value

    @property
    def name(self) -> str:
        return self.db_obj.name

    @name.setter
    def name(self, value: str):
        self.db_obj.name = value

    @property
    def idx(self) -> int:
        return self.db_obj.idx

    @idx.setter
    def idx(self, value: int):
        self.db_obj.idx = value

    def build(self):
        self.editor3d.context.acquire()
        if self.is_round:
            width = height = float(_d(self.width) / _d(2.0))
            self.db_obj.width = width
            self.db_obj.height = height

            self._vbo = _cylinder.create_vbo()
            self._vbo.acquire()
        else:
            width = self.width
            height = self.height

            self._vbo = _box.create_vbo()

        self._vbo.acquire()
        with self._scale:
            self._scale.x = width
            self._scale.y = height

        self._scale.z = self.length

        self.editor3d.context.release()

        return self._vbo
