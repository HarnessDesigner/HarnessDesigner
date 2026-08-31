# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

from ... import color as _color
from . import material as _material
from ... import check_types as _check_types


class RubberMaterial(_material.GLMaterial):
    """Represent a rubber material in :mod:`harness_designer.gl.materials.rubber`.

    Rubber is a dielectric -- its own hue stays in ``diffuse`` (the
    dominant term for a matte surface), while ``specular`` stays a fixed,
    low, colorless sheen (rubber's highlight isn't tinted by its own
    color, unlike a metal's -- see :class:`~.metallic.MetallicMaterial`).
    A small additive floor on ambient/diffuse keeps even a fully black
    rubber from looking like a flat, featureless void (matching the old
    hardcoded black-rubber special case this replaced), without needing
    a separate branch for it.
    """
    _ambient = (0.0, 0.0, 0.0)
    _diffuse = (0.0, 0.0, 0.0)
    _specular = (0.06, 0.06, 0.06)
    _shine = 10.0

    _cl_ambient = 0.0
    _cl_diffuse = 0.0
    _cl_specular = 0.06
    _cl_shininess = 10.0
    _cl_metallic = 0.0
    _cl_roughness = 0.8

    @_check_types.do
    def __init__(self, color: _color.Color):
        """Initialise the :class:`RubberMaterial` instance.

        :param color: The rubber's own color -- tints diffuse/ambient
            directly (see class docstring), not remapped or discarded.
        :type color: :class:`_color.Color`
        """
        r, g, b = color.rgb_scalar

        self._diffuse = (0.02 + r * 0.5, 0.02 + g * 0.5, 0.02 + b * 0.5)
        self._ambient = (0.02 + r * 0.03, 0.02 + g * 0.03, 0.02 + b * 0.03)

        self._cl_specular = sum(self._specular) / len(self._specular)
        self._cl_diffuse = sum(self._diffuse) / len(self._diffuse)
        self._cl_ambient = sum(self._ambient) / len(self._ambient)

        super().__init__(color)
