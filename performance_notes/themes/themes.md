# harness_designer/themes/themes.py

## Line 10-13 (`get_themes`) — one directory listing
Lists the themes folder. Called on demand (for example when a theme menu is built). Fine.

## Line 16-32 (`load_theme`) — reads a stylesheet and reapplies it to the whole application
Reads one `.qss` file, replaces an icon-path placeholder, and calls `setStyleSheet` on the application. Re-applying a stylesheet is expensive in Qt because it re-polishes every widget, so it should run only when the user changes theme. It does, so no change is needed. The `import harness_designer as hd` inside the function is there to avoid an import cycle.

**Typing (fixed in this pass):** `get_themes` returns `list[str]`, `load_theme` takes `theme_name: str` and returns `None`.
