import numpy as np


class Light:
    """Light source"""

    def __init__(self, position=(0, 0, 0), intensity=1.0, color=(1, 1, 1)):
        self.position = np.array(position, dtype=np.float32)
        self.intensity = intensity
        self.color = np.array(color, dtype=np.float32)

    def to_array(self):
        return np.array([
            self.position[0], self.position[1], self.position[2],
            self.intensity,
            self.color[0], self.color[1], self.color[2]
        ], dtype=np.float32)
