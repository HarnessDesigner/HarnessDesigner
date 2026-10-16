"""Streaming output: JSON record serialization and HTML file assembly."""
from .json_writer import dumps_for_script_embed
from .html_writer import HtmlDumpWriter

__all__ = ['dumps_for_script_embed', 'HtmlDumpWriter']
