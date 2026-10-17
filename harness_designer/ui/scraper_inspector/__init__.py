# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

from . import inspector as _inspector
from . import insertion as _insertion


ScraperInspector = _inspector.ScraperInspector
SnippetSink = _insertion.SnippetSink
insert_snippet = _insertion.insert_snippet


del _inspector
del _insertion
