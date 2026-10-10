# harness_designer/gl/materials/glowing.py

## Line 25-34 (`GlowingMaterial.__init__`) — one NumPy array built per material
`self.emissive = np.array(color.rgba_scalar, dtype=np.float32)` runs once when the material is constructed, not per draw. The array is small (four floats), so there is nothing to gain here. The only cost worth knowing about is that `color.rgba_scalar` builds a fresh tuple each time it is read; that happens once per material here.
