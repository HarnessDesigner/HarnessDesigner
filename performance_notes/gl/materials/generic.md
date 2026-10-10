# harness_designer/gl/materials/generic.py

## Whole file — class attributes only
`GenericMaterial` only overrides the class-level weights (`_ambient_weight`, `_diffuse_weight`, `_specular_weight`, `_metallic`, `_shine`). These are read when the material's colour arrays are built, not per draw, so there is no hot-path cost.
