# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

"""
Crash-dump diagnostics: schema-driven, severity-gated capture of
application object state for render-failure and fatal-crash dumps.
"""

from .schema import Attr, dump_property
from .registry import capturable, capture_groups_for, CaptureGroup
from .render import iter_render_children
from .writer import dumps_for_script_embed, HtmlDumpWriter
from .walker import walk, dump_to_html
from .entrypoints import (dump_state_on_fatal_exception, dump_render_failure,
                          dump_visible_objects)

__all__ = ['Attr', 'dump_property', 'capturable', 'capture_groups_for',
           'CaptureGroup', 'iter_render_children', 'dumps_for_script_embed',
           'HtmlDumpWriter', 'walk', 'dump_to_html', 'dump_render_failure',
           'dump_state_on_fatal_exception', 'dump_visible_objects']
