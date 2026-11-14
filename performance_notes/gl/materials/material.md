# harness_designer/gl/materials/material.py

## Line 167-193 (`GLMaterial.set`) — five uniform writes per draw, and a string round trip for emissive materials
Called for each object on each draw. It writes `material_ambient`, `material_diffuse`, `material_specular`, `material_shininess` and `material_emissive` (five `glUniform` calls) and, for an emissive material, computes the rim value at line 188 with `sum(float(str(v)) for v in self.emissive[:-1].tolist()) * 2`: three string round trips per draw (about 1.2 us). The emissive colour does not change after construction, so the rim value can be computed once in `__init__` and stored (one float per material). Caching the last material per program, so consecutive objects that share a material skip the five writes, would save the uniform calls (a pointer per program).

## Line 128-144 (`cl_array`)
Builds a new 12-float array per read; used by the ray tracer's material packing only. Negligible.

## Line 92-124 (`__init__`)
Builds the ambient/diffuse/specular/emissive arrays once per material. Fine.
