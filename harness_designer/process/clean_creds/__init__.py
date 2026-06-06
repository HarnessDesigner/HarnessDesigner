# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

"""Platform-specific helpers for removing cached database credentials."""

import sys

if sys.platform.startswith('win'):
    from . import win as module

run = module.run
