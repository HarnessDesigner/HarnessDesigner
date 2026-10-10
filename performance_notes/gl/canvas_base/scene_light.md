# harness_designer/gl/canvas_base/scene_light.py

## Line 32-49 (`SceneLight.render`) — three NumPy arrays and four uniform writes every frame
`render` is called on the frame path. Each call:
- builds three new `np.array(..., dtype=np.float32)` from `config.ambient`, `config.diffuse` and `config.specular`;
- enters the faces program context and writes four uniforms (`light_position`, `light_ambient`, `light_diffuse`, `light_specular`).

The light config changes only when the user edits lighting settings, so the three arrays could be built once (on config change) and reused. The uniform writes could skip when the values are unchanged (see `program.md` for the uniform setter note). For a single light this is small, but it runs every frame.
