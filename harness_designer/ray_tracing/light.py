# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

"""Light source helpers for the ray tracer.

Lights are flattened into arrays so they can be uploaded to the OpenCL kernel
used by :mod:`harness_designer.ray_tracing.renderer`.
"""

import numpy as np


class Light:
    """Light source"""

    def __init__(self, position=(0, 0, 0), intensity=1.0, color=(1, 1, 1)):
        """Initialize a light definition.

        :param position: Light position in world space.
        :type position: tuple[float, float, float]
        :param intensity: Scalar intensity multiplier for the light.
        :type intensity: float
        :param color: RGB light color components.
        :type color: tuple[float, float, float]
        """
        self.position = np.array(position, dtype=np.float32)
        self.intensity = intensity
        self.color = np.array(color, dtype=np.float32)

    def to_array(self):
        """Flatten the light into a GPU-friendly array.

        :returns: Array containing position, intensity, and color values.
        :rtype: :class:`numpy.ndarray`
        """
        return np.array([
            self.position[0], self.position[1], self.position[2],
            self.intensity,
            self.color[0], self.color[1], self.color[2]
        ], dtype=np.float32)
