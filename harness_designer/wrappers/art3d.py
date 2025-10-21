from typing import TYPE_CHECKING

from mpl_toolkits.mplot3d import art3d


class Line3D(art3d.Line3D):
    _py_data = None
    _is_removed = False

    def set_py_data(self, data):
        self._py_data = data

    def get_py_data(self):
        return self._py_data

    def remove(self):
        if self._is_removed:
            return
        art3d.Line3D.remove(self)
        self._is_removed = True


setattr(art3d, 'Line3D', Line3D)


class Path3DCollection(art3d.Path3DCollection):
    _py_data = None
    _is_removed = False

    def set_py_data(self, data):
        self._py_data = data

    def get_py_data(self):
        return self._py_data

    def remove(self):
        if self._is_removed:
            return
        art3d.Path3DCollection.remove(self)
        self._is_removed = True


setattr(art3d, 'Path3DCollection', Path3DCollection)


class Poly3DCollection(art3d.Poly3DCollection):
    _py_data = None
    _is_removed = False

    def set_py_data(self, data):
        self._py_data = data

    def get_py_data(self):
        return self._py_data

    def remove(self):
        if self._is_removed:
            return
        art3d.Poly3DCollection.remove(self)
        self._is_removed = True


setattr(art3d, 'Poly3DCollection', Poly3DCollection)

if TYPE_CHECKING:
    art3d.Line3D = Line3D
    art3d.Path3DCollection = Path3DCollection
    art3d.Poly3DCollection = Poly3DCollection
