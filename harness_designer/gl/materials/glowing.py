# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

import numpy as np

from . import material as _material
from ... import color as _color
from ... import check_types as _check_types


class GlowingMaterial(_material.GLMaterial):
    """LED-like emissive material.

    The fragment shader's emissive branch (``gl/shaders/faces/
    fragment.frag``) replaces ambient/diffuse/specular shading entirely
    once ``materialEmissive`` is non-zero, so this class only needs to
    add the emissive term itself on top of a plain :class:`GenericMaterial`-like
    fill -- that fill is effectively unused while glowing, but keeps
    this material sane if something ever reads it before the emissive
    branch takes over.
    """
    _ambient_weight = 0.35
    _diffuse_weight = 0.55
    _specular_weight = 0.25

    @_check_types.do
    def __init__(self, color: _color.Color):
        """Initialise the :class:`GlowingMaterial` instance.

        :param color: The glow's own color, used as-is for the
            emissive term.
        :type color: :class:`_color.Color`
        """
        super().__init__(color)
        self.emissive = np.array(color.rgba_scalar, dtype=np.float32)
