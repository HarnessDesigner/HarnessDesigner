from python_utils import remap
from OpenGL.GL import *


class GLMaterial:
    _ambient = (0.0, 0.0, 0.0)
    _diffuse = (0.0, 0.0, 0.0)
    _specular = (0.0, 0.0, 0.0)
    _shine = 0.0

    def __init__(self, color):
        self._color = color
        self._x_ray = False

    def x_ray(self, flag):
        self._x_ray = flag

    def set(self):
        if self._x_ray:
            a = (0.2,)
        else:
            a = self._color[-1:]

        glMaterialfv(GL_FRONT, GL_AMBIENT, self._ambient + a)
        glMaterialfv(GL_FRONT, GL_DIFFUSE, self._diffuse + a)
        glMaterialfv(GL_FRONT, GL_SPECULAR, self._specular + a)
        glMaterialf(GL_FRONT, GL_SHININESS, self._shine)


class BlackPlastic(GLMaterial):
    _ambient = (0.0, 0.0, 0.0)
    _diffuse = (0.01, 0.01, 0.01)
    _specular = (0.50, 0.50, 0.50)
    _shine = 32.0


class CyanPlastic(GLMaterial):
    _ambient = (0.0, 0.1, 0.06)
    _diffuse = (0.0, 0.50980392, 0.50980392)
    _specular = (0.50196078, 0.50196078, 0.50196078)
    _shine = 32.0


class GreenPlastic(GLMaterial):
    _ambient = (0.0, 0.0, 0.0)
    _diffuse = (0.1, 0.35, 0.1)
    _specular = (0.45, 0.55, 0.45)
    _shine = 32.0
          

class RedPlastic(GLMaterial):
    _ambient = (0.0, 0.0, 0.0)
    _diffuse = (0.5, 0.0, 0.0)
    _specular = (0.7, 0.6, 0.6)
    _shine = 32.0
          

class WhitePlastic(GLMaterial):
    _ambient = (0.0, 0.0, 0.0)
    _diffuse = (0.55, 0.55, 0.55)
    _specular = (0.70, 0.70, 0.70)
    _shine = 32.0
          

class YellowPlastic(GLMaterial):
    _ambient = (0.0, 0.0, 0.0)
    _diffuse = (0.5, 0.5, 0.0)
    _specular = (0.60, 0.60, 0.50)
    _shine = 32.0


class Rubber(GLMaterial):
    _ambient = (0.00, 0.00, 0.0)
    _diffuse = (0.0, 0.0, 0.0)
    _specular = (0.0, 0.0, 0.0)
    _shine = 10.0

    def __init__(self, color):
        super().__init__(color)
        r, g, b, _ = color

        if r == g == b == 0.0:
            ar, ag, ab = (0.02, 0.02, 0.02)
            dr, dg, db = (0.01, 0.01, 0.01)
            sr, sg, sb = (0.4, 0.4, 0.4)
        else:
            ar = remap(r, 0.0, 1.0, 0.0, 0.05)
            ag = remap(g, 0.0, 1.0, 0.0, 0.05)
            ab = remap(b, 0.0, 1.0, 0.0, 0.05)

            dr = remap(r, 0.0, 1.0, 0.4, 0.5)
            dg = remap(g, 0.0, 1.0, 0.4, 0.5)
            db = remap(b, 0.0, 1.0, 0.4, 0.5)

            sr = remap(r, 0.0, 1.0, 0.04, 0.7)
            sg = remap(g, 0.0, 1.0, 0.04, 0.7)
            sb = remap(b, 0.0, 1.0, 0.04, 0.7)

        self._ambient = (ar, ag, ab)
        self._diffuse = (dr, dg, db)
        self._specular = (sr, sg, sb)


class Metallic(GLMaterial):
    _ambient = (0.00, 0.00, 0.0)
    _diffuse = (0.0, 0.0, 0.0)
    _specular = (0.0, 0.0, 0.00)
    _shine = 51.2

    def __init__(self, color):
        super().__init__(color)
        r, g, b, _ = color

        ar = remap(r, 0.75294, 1.0, 0.19215, 0.24705)
        ag = remap(g, 0.75294, 0.843137, 0.19215, 0.19607)
        ab = remap(b, 0.0, 0.75294, 0.07058, 0.19215)

        dr = remap(r, 0.75294, 1.0, 0.50588, 0.3451)
        dg = remap(g, 0.75294, 0.843137, 0.50588, 0.3137)
        db = remap(b, 0.0, 0.75294, 0.09019, 0.50588)

        sr = remap(r, 0.75294, 1.0, 0.50588, 0.79607)
        sg = remap(g, 0.75294, 0.843137, 0.50588, 0.72156)
        sb = remap(b, 0.0, 0.75294, 0.2078, 0.50588)

        self._ambient = (ar, ag, ab)
        self._diffuse = (dr, dg, db)
        self._specular = (sr, sg, sb)


class Polished(GLMaterial):
    _ambient = (0.0, 0.00, 0.0)
    _diffuse = (0.0, 0.0, 0.0)
    _specular = (0.0, 0.0, 0.00)
    _shine = 0.0

    def __init__(self, color):
        super().__init__(color)
        r, g, b, _ = color

        ar = remap(r, 0.75294, 1.0, 0.22745, 0.24705)
        ag = remap(g, 0.75294, 0.843137, 0.22745, 0.22352)
        ab = remap(b, 0.0, 0.75294, 0.06274, 0.22745)

        dr = remap(r, 0.75294, 1.0, 0.27450, 0.34509)
        dg = remap(g, 0.75294, 0.843137, 0.27450, 0.31372)
        db = remap(b, 0.0, 0.75294, 0.09019, 0.27450)

        sr = remap(r, 0.75294, 1.0, 0.77254, 0.79607)
        sg = remap(g, 0.75294, 0.843137, 0.77254, 0.72156)
        sb = remap(b, 0.0, 0.75294, 0.20784, 0.77254)

        self._ambient = (ar, ag, ab)
        self._diffuse = (dr, dg, db)
        self._specular = (sr, sg, sb)

        self._shine = remap(r + g + b, 1.843137, 2.25882, 83.2, 89.6)
