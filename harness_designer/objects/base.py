from typing import TYPE_CHECKING, Union

import wx

from ..wrappers import wxartist_event as _wxartist_event


if TYPE_CHECKING:
    from .. import editor_3d as _editor_3d
    from .. import editor_2d as _editor_2d
    from ..wrappers import wxkey_event as _wxkey_event
    from ..wrappers import wxmouse_event as _wxmouse_event


class ObjectBase:
    def __init__(self, db_obj, editor3d: Union["_editor_3d.Editor3D", None], editor2d: Union["_editor_2d.Editor2D", None]):
        self._wxid = wx.NewIdRef()

        self._db_obj = db_obj
        self._editor3d = editor3d
        self._editor2d = editor2d
        self._part = db_obj.part
        self._selected = False
        self._objs = []

    @property
    def part(self):
        raise NotImplementedError

    def menu3d(self, x, y):
        pass

    def menu2d(self, x, y):
        pass

    def tools3d(self):
        pass

    def tools2d(self):
        pass

    def init(self):
        for obj in self._objs:
            obj.set_py_data(self)
            obj.set_selected_color(False)

    @property
    def id(self) -> int:
        return self._db_obj.db_id

    @property
    def wxid(self) -> int:
        return self._wxid

    def IsSelected(self, flag: bool | None = None) -> bool | None:
        if flag is None:
            return self._selected
        else:
            self._selected = flag
            for obj in self._objs:
                obj.set_selected_color(flag)

            self._editor3d.canvas.draw_idle()

            if flag:
                self._editor3d.Unbind(_wxartist_event.EVT_ARTIST_SET_SELECTED,
                                      handler=self._on_artist_set, id=self._wxid)
                self._editor3d.Bind(_wxartist_event.EVT_ARTIST_UNSET_SELECTED,
                                    self._on_artist_unset, id=self._wxid)

                self._editor3d.Bind(wx.EVT_KEY_UP, self._on_key_up)

            else:
                self._editor3d.Bind(_wxartist_event.EVT_ARTIST_SET_SELECTED,
                                    self._on_artist_set, id=self._wxid)
                self._editor3d.Unbind(_wxartist_event.EVT_ARTIST_UNSET_SELECTED,
                                      handler=self._on_artist_unset, id=self._wxid)

                self._editor3d.Unbind(wx.EVT_KEY_UP, handler=self._on_key_up)



    def _on_artist_set(self, evt: "_wxartist_event.ArtistEvent"):
        self._editor3d.SetSelected(self, True)
        evt.Skip()

    def _on_artist_unset(self, evt: "_wxartist_event.ArtistEvent"):
        self._editor3d.SetSelected(self, False)
        evt.Skip()

    def _on_key_up(self, evt: "_wxkey_event.KeyEvent"):
        if evt.GetKeyCode() == wx.WXK_DELETE:
            if self._editor3d is not None:
                self._editor3d.remove(self)
            if self._editor2d is not None:
                self._editor2d.remove(self)

            self._db_obj.delete()

        evt.Skip()




