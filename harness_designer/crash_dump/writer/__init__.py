# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

"""
Streaming output: JSON record serialization and HTML file assembly.
"""

from .json_writer import dumps_for_script_embed
from .html_writer import HtmlDumpWriter

__all__ = ['dumps_for_script_embed', 'HtmlDumpWriter']
