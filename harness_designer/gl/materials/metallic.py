# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

from ... import color as _color
from . import material as _material
from ... import check_types as _check_types


class MetallicMaterial(_material.GLMaterial):
    """Represent a metallic material in :mod:`harness_designer.gl.materials.metallic`.

    Ambient/diffuse carry the metal's true color at the same full-
    strength convention every material in this renderer uses (see
    ``PlasticMaterial``/``GenericMaterial``, which both set ambient AND
    diffuse straight to the raw input color, undimmed) -- this renderer
    has no exposure/tonemapping step, so crushing diffuse toward zero the
    way a strict physically-based metallic-roughness model would (real
    metal has almost no diffuse term) just reads as flat black instead of
    "metallic." A metal's distinct look comes instead from a brighter,
    color-tinted specular highlight layered on top -- a dielectric's
    specular stays a fixed, uncolored grey regardless of its own color
    (see ``PlasticMaterial``/``RubberMaterial``), while a metal's
    highlight takes on its own hue and runs hotter.

    Either way this is still the real input color doing the tinting, not
    a blend toward some unrelated hardcoded preset (see the remap-based
    version this replaced, whose fixed per-channel output bands were
    lifted from the classic OpenGL "copper"/"gold" presets and barely
    responded to the actual color requested).
    """
    _ambient = (0.0, 0.0, 0.0)
    _diffuse = (0.0, 0.0, 0.0)
    _specular = (0.0, 0.0, 0.0)
    _shine = 90.0

    _cl_ambient = 0.0
    _cl_diffuse = 0.0
    _cl_specular = 0.0
    _cl_shininess = 90.0
    _cl_metallic = 0.8
    _cl_roughness = 0.35

    # How much brighter than the raw color the specular highlight runs,
    # scaled by how metallic this material is -- 0.8 metallic here means
    # the highlight peaks noticeably hotter than the base color instead
    # of matching it 1:1 (which would look identical to a plain diffuse
    # surface with no metal character at all).
    _specular_boost = 0.3

    @_check_types.do
    def __init__(self, color: _color.Color):
        """Initialise the :class:`MetallicMaterial` instance.

        :param color: The metal's own color -- tints ambient/diffuse/
            specular directly (see class docstring), not remapped or
            discarded.
        :type color: :class:`_color.Color`
        """
        r, g, b = color.rgb_scalar

        self._ambient = (r, g, b)
        self._diffuse = (r, g, b)

        boost = 1.0 + self._cl_metallic * self._specular_boost
        self._specular = (min(r * boost, 1.0), min(g * boost, 1.0), min(b * boost, 1.0))

        self._cl_specular = sum(self._specular) / len(self._specular)
        self._cl_diffuse = sum(self._diffuse) / len(self._diffuse)
        self._cl_ambient = sum(self._ambient) / len(self._ambient)

        super().__init__(color)
