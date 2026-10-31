# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

"""Light source helpers for the ray tracer.

Lights are flattened into arrays so they can be uploaded to the OpenCL kernel
used by :mod:`harness_designer.ray_tracing.renderer`.
"""

from collections.abc import Sequence

import numpy as np

from .. import check_types as _check_types


class Light:
    """Point light source"""

    @_check_types.do
    def __init__(self, position: Sequence[float] = (0.0, 0.0, 0.0), intensity: float = 1.0,
                 color: Sequence[float] = (1.0, 1.0, 1.0)):
        """Initialize a light definition.

        :param position: Light position in world space.
        :type position: Sequence[float]
        :param intensity: Scalar intensity multiplier for the light.
        :type intensity: float
        :param color: RGB light color components.
        :type color: Sequence[float]
        """
        self.position = np.array(position, dtype=np.float32)
        self.intensity = float(intensity)
        self.color = np.array(color, dtype=np.float32)

    @_check_types.do
    def to_array(self) -> np.ndarray:
        """Flatten the light into the layout of ``Light`` in ``kernel.cl``.

        :returns: ``x, y, z, intensity, r, g, b`` as a float32 array.
        :rtype: :class:`numpy.ndarray`
        """
        return np.concatenate((self.position, [self.intensity], self.color)).astype(np.float32)
