# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

# Importing this package imports QtWebEngine (Chromium). Import it only when
# the browser is first opened, never at application start.

from . import browser_dock as _browser_dock


ScraperBrowser = _browser_dock.ScraperBrowser
ScraperBrowserPanel = _browser_dock.ScraperBrowserPanel


del _browser_dock
