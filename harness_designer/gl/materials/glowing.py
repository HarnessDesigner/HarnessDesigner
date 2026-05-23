# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

from . import material as _material


class GlowingMaterial(_material.GLMaterial):
    """Represent a glowing material in :mod:`harness_designer.gl.materials.glowing`.

    UNKNOWN details are inferred from the class name and surrounding code.
    """
    _ambient = (0.0, 0.0, 0.0)
    _diffuse = (0.55, 0.55, 0.55)
    _specular = (0.70, 0.70, 0.70)
    _shine = 92.0

    def __init__(self, color):
        """Initialise the :class:`GlowingMaterial` instance.

        UNKNOWN details are inferred from the callable name and signature.

        :param color: Value for ``color``.
        :type color: UNKNOWN
        """
        self._emissive = color.rgba_scalar
        self.diffuse = color.rgb_scalar

        _material.GLMaterial.__init__(self, color)
