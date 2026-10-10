# harness_designer/gl/materials/material.py

## Line 91-124 (`GLMaterial.__init__`) — NumPy arrays built once per material
Builds `ambient`, `diffuse`, `specular` and `emissive` arrays when the material is constructed. Not per draw. Fine.

## Line 126-144 (`GLMaterial.cl_array`) — builds an array each read
A property that builds a new 12-float array each time it is read. Used by the ray tracer's material packing, not by the rasterizer. If the ray tracer reads it once per material per render, the cost is negligible. Caching would only matter if it is read per ray.

## Line 146-164 (`color_scalar`, `is_opaque`) — cheap reads
`color_scalar` calls `rgba_scalar` on the colour each time, which builds a tuple. `is_opaque` returns a stored bool. Neither is on a hot path that I could confirm from this file alone.

## Line 166-193 (`GLMaterial.set`) — per-draw uniform push and a string round-trip
This is called for each object on each draw (from the faces and edges render paths). Each call:
- writes five uniforms (`material_ambient`, `material_diffuse`, `material_specular`, `material_shininess`, `material_emissive`);
- for emissive materials, computes the rim value with `float(str(v))` on each of three values (line 188). This is the same string round-trip noted in `vbo.md`. It is pure waste on the draw path. `sum(float(v) for v in self.emissive[:-1])` would give the same result without the string conversion, and the rim value could be computed once in `__init__`, since the emissive colour does not change after construction.

The uniform writes repeat for every object that shares a material. Caching the last material per program would skip the writes when consecutive objects use the same material.
