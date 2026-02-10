
import numpy as np

from ...geometry import point as _point
from ...wrappers.decimal import Decimal as _decimal
from ... import config as _config


class Config(metaclass=_config.Config):
    renderer = "GLRenderer"


_registered = {}
_active = None


def get_active_renderer_cls():
    return _active


def get_active_renderer():
    return _active.__name__


def get_renderers() -> list[str]:
    return list(_registered.keys())


def set_renderer_active(name: str):
    global _active
    if name not in _registered:
        raise NameError(name)

    _active = _registered[name]


class RendererMeta(type):

    def __init__(cls, name, bases, dct):
        super().__init__(name, bases, dct)
        cls.__name__ = name
        _registered[name] = cls


class RendererBase:

    @classmethod
    def set_active(cls):
        global _active
        _active = cls

    def init(self, w: int | float, h: int | float):
        raise NotImplementedError

    @staticmethod
    def set_viewport(width: int | float, height: int | float):
        raise NotImplementedError

    @staticmethod
    def get_world_coords(mx: int, my: int) -> _point.Point:
        raise NotImplementedError

    def reset_camera(self, *_):
        raise NotImplementedError

    def draw(self) -> "DrawWrapperBase":
        raise NotImplementedError

    @staticmethod
    def build_mesh(model) -> tuple[np.ndarray, np.ndarray, int]:
        raise NotImplementedError

    def rotate(self, dx: _decimal, dy: _decimal):
        raise NotImplementedError

    def look(self, dx: _decimal, dy: _decimal):
        raise NotImplementedError

    def zoom(self, dx: _decimal, dy: _decimal | None = None):
        raise NotImplementedError

    def walk(self, dx: _decimal, dy: _decimal):
        raise NotImplementedError

    def pan(self, dx: _decimal, dy: _decimal):
        raise NotImplementedError


class DrawWrapperBase:
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        pass

    def grid(self):
        raise NotImplementedError

    @staticmethod
    def model(*args, **kwargs):
        raise NotImplementedError

