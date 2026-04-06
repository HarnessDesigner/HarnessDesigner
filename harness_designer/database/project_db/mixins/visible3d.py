from wx import propgrid as wxpg

from .base import BaseMixin


class Visible3DMixin(BaseMixin):

    @property
    def is_visible3d(self) -> bool:
        return bool(self._table.select('is_visible3d', id=self._db_id)[0][0])

    @is_visible3d.setter
    def is_visible3d(self, value: bool):
        self._table.update(self._db_id, is_visible3d=int(value))

    @property
    def _visible3d_propgrid(self) -> wxpg.PGProperty:
        from ....ui.editor_obj.prop_grid import bool_prop as _bool_prop

        visible_prop = _bool_prop.BoolProperty('Visible 3D', 'is_visible3d', self.is_visible3d)

        return visible_prop
