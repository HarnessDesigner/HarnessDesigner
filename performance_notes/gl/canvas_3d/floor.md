# harness_designer/gl/canvas_3d/floor.py

## Line 72-97 (`Floor._initialize_grid`) — GPU buffers rebuilt only on toggle
Runs when the floor is enabled (`set(True)`), not per frame. Builds one quad and one index buffer. Nothing to gain.

## Line 101-124 (`Floor.set`) — teardown and rebuild on every toggle
Deletes the VAO and two buffers before rebuilding. That is correct when the floor is turned off, but when `flag` is True and a VAO already exists, the old one is deleted and a new one built, which is wasted work. It also calls `Refresh(False)` on every toggle. Low frequency (user action), so this is minor.

## Line 128-189 (`Floor.render`) — about 13 uniform writes and two draws every frame
`render` runs every frame. It writes `mvp`, the tile/minor-grid parameters, the four colours, the two line widths and the two stipple values, then draws the same six-index quad twice (opaque pass, then transparent pass). The uniform values come from config and change rarely. Caching the last-written values per program (see `shaders/program.md`) would drop most of these writes. Two draws are needed because of the depth-mask ordering, so they stay.

Also `int(cfg.secondary_line_pattern)` and `int(cfg.secondary_line_shift)` convert per frame; they could be converted when the config changes.
