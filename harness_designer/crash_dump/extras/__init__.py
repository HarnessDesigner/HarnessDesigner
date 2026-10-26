# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

"""
Lazily-imported rendering support for optional stdlib/third-party
types. Each submodule here is only ever imported by ``render.py`` the
first time a value of its specific type is actually captured.
"""
