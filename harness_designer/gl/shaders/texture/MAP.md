## FILES

#### __init__.py

`from . import texture as _texture` — re-exports `compile_program`.

#### fragment.frag

Samples `imageTexture` (texture unit 0) and `discard`s below 1% alpha rather than blending, so a
texture with a hard transparent edge doesn't leave a translucent halo.

#### texture.py

`compile_program()` — compiles+links `vertex.vert` + `fragment.frag` (no geometry stage) into
`program.TextureProgram`. Not documented anywhere in the repo-root `CODEBASE_MAP.md`'s older
"## `gl/`" section — a later addition. Draws a single GL texture across a unit quad, unlit.
Ported from a proven scratch implementation
(`scratches/pegboard_spreadsheet_widget/gl_spreadsheet_test.py`, built/visually verified there for
a wire-icon column), same GLSL and same compile/link pattern as every other shader in this
package, moved here once it got a second real consumer: `objects.objects_pegboard.table.Table`
renders a peg-board floating wire table by capturing a hidden `QMdiSubWindow` to a `QImage` and
uploading it as this shader's texture each time its content changes.

#### vertex.vert

Unit-quad vertex stage — no per-object 3D transform needed, since the quad is unlit and
screen-aligned.
