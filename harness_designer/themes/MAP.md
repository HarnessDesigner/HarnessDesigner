## FILES

#### __init__.py

Re-exports `get_themes` and `load_theme` from `themes.py`.

#### themes.py

`get_themes()` — lists the subdirectories of this package (each one a theme, see `Dark/`/`Light/` below).
`load_theme(theme_name)` — reads `<theme_name>/<theme_name>.qss`, rewrites the `:/qss_icons/dark/rc` resource
prefix baked into the stylesheet to point at that theme's own `icons/` directory on disk (forward slashes,
since Qt stylesheet URLs don't accept backslashes even on Windows), and applies it with
`QApplication.setStyleSheet` via the app singleton (`import harness_designer as hd; hd._app.setStyleSheet
(...)`). Silently does nothing if the named theme's `.qss` file doesn't exist.

## FOLDERS

#### Dark/

One `.qss` stylesheet (`Dark.qss`) and nothing else — unlike `Light/`, it has no `icons/` subdirectory of
its own, so whatever icon references its stylesheet contains resolve against Light's icon set or a Qt
resource path rather than a per-theme icon folder. Worth double-checking against `themes.py`'s
`:/qss_icons/dark/rc` rewrite if dark-theme icons ever look wrong.

#### Light/

`Light.qss` plus a large `icons/` subdirectory of the UI chrome glyphs (window controls, tree-view
branch/arrow icons, etc., each usually in `@1x`/`@2x` and normal/disabled/focus/pressed variants) that
`themes.py`'s path rewrite points the stylesheet at.
