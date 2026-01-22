from .utils import remap
from OpenGL.GL import *


class GLMaterial:

    _ambient = (0.0, 0.0, 0.0)

    # color is the "color" we tend to think of, tends to be white for metals
    _diffuse = (0.0, 0.0, 0.0)

    # plastics white, metals darker color
    _specular = (0.0, 0.0, 0.0)

    # polished metals has the highest shine, rubber type materials will have a rally low shine. plastics are in between
    _shine = 0.0  # 0.0 to 128.0

    def __init__(self, color):
        self._color = color
        self._saved_emission = []
        self._saved_ambient = []
        self._saved_diffuse = []
        self._saved_specular = []
        self._saved_shine = []

        self.x_ray = False
        self.x_ray_color = [0.2, 0.2, 1.0, 0.35]

    @property
    def is_opaque(self):
        if self.x_ray:
            return False

        return self._color[-1] == 1.0

    def set(self):
        self._saved_emission = glGetMaterialfv(GL_FRONT, GL_EMISSION)
        self._saved_ambient = glGetMaterialfv(GL_FRONT, GL_AMBIENT)
        self._saved_diffuse = glGetMaterialfv(GL_FRONT, GL_DIFFUSE)
        self._saved_specular = glGetMaterialfv(GL_FRONT, GL_SPECULAR)
        self._saved_shine = glGetMaterialfv(GL_FRONT, GL_SHININESS)

        a = tuple(self._color[:-1])

        if self.x_ray:
            glMaterialfv(GL_FRONT, GL_EMISSION, self.x_ray_color)
            glMaterialfv(GL_FRONT, GL_AMBIENT, self.x_ray_color)
            glMaterialfv(GL_FRONT, GL_DIFFUSE, self.x_ray_color)
            glMaterialfv(GL_FRONT, GL_SPECULAR, self.x_ray_color)
            glMaterialf(GL_FRONT, GL_SHININESS, 110.0)
        else:
            glMaterialfv(GL_FRONT, GL_AMBIENT, self._ambient + a)
            glMaterialfv(GL_FRONT, GL_DIFFUSE, self._diffuse + a)
            glMaterialfv(GL_FRONT, GL_SPECULAR, self._specular + a)
            glMaterialf(GL_FRONT, GL_SHININESS, self._shine)

    def unset(self):
        glMaterialfv(GL_FRONT, GL_EMISSION, self._saved_emission)
        glMaterialfv(GL_FRONT, GL_AMBIENT, self._saved_ambient)
        glMaterialfv(GL_FRONT, GL_DIFFUSE, self._saved_diffuse)
        glMaterialfv(GL_FRONT, GL_SPECULAR, self._saved_specular)
        glMaterialf(GL_FRONT, GL_SHININESS, self._saved_shine)


class DefaultMaterial(GLMaterial):
    _ambient = (0.3, 0.3, 0.3, 0.5)
    _diffuse = (0.5, 0.5, 0.5, 0.5)
    _specular = (0.8, 0.8, 0.8, 0.5)
    _shine = 100.0


class Plastic(GLMaterial):
    _ambient = (0.0, 0.0, 0.0)
    _diffuse = (0.0, 0.0, 0.0)
    _specular = (0.898039, 0.898039, 0.898039)
    _shine = 110.0

    def __init__(self, color):
        super().__init__(color)
        self._ambient = tuple(color[:-1])
        self._diffuse = tuple(color[:-1])


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
    _ambient = (0.0, 0.0, 0.0)
    _diffuse = (0.0, 0.0, 0.0)
    _specular = (0.0, 0.0, 0.0)
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
