"""Point-and-click scraper authoring: turning a captured JSON/HTML sample
into working Python extraction code, with optional Claude API assistance.

Anything that needs Claude goes through ``harness_designer.plugins.plugins.claude_ai`` (the
application's one doorway to the API; each user supplies their own key).

See SCRAPER_DESIGN.md in the repo root for the design of the whole tool.
"""
from . import html_locate
from . import json_extract
from . import request_code
from . import snippets

__all__ = ['html_locate', 'json_extract', 'request_code', 'snippets']
