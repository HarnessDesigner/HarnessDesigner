from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .. import ObjectBase as _ObjectBase
    from ... import ui as _ui
    from ...ui import editor_2d as _editor_2d
    from ...database import project_db as _project_db


class Base2D:

    def __init__(self, parent: "_ObjectBase",
                 db_obj: "_project_db.PJTEntryBase"):

        self._parent: "_ObjectBase" = parent
        self.db_obj = db_obj

        self.editor2d: "_editor_2d.Editor2D" = parent.mainframe.editor2d
        self.mainframe: "_ui.MainFrame" = parent.mainframe

        self._is_selected = False

    def set_selected(self, flag: bool):
        self._is_selected = flag

        if flag:
            self.mainframe._set_selected(self._parent)  # NOQA
        else:
            self.mainframe._set_selected(None)  # NOQA

    @property
    def is_selected(self) -> bool:
        return self._is_selected

    def render(self, pdc, gcdc, gc):
        pass

