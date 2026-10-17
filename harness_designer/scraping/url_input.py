# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

"""What the user typed in the address bar -> a URL to load."""

import re

from .. import check_types as _check_types

_HAS_SCHEME = re.compile(r'^[A-Za-z][A-Za-z0-9+.-]*://')
_SPECIAL_SCHEMES = ('about:', 'file:', 'data:', 'view-source:')
_LOCAL_HOST = re.compile(r'^(localhost|\d{1,3}(\.\d{1,3}){3}|\[[0-9A-Fa-f:]+\])(:\d+)?([/?#]|$)')


@_check_types.do
def normalize_url(text: str) -> str:
    """The URL for what was typed in the address bar.

    ``example.com/shop`` gets ``https://``; ``localhost:8000`` and bare
    IP addresses get ``http://``; anything with a scheme is left alone.
    Returns an empty string when the text cannot be a URL (empty, or
    containing spaces).
    """
    text = text.strip()
    if not text or any(char.isspace() for char in text):
        return ''

    if _HAS_SCHEME.match(text) or text.lower().startswith(_SPECIAL_SCHEMES):
        return text

    if _LOCAL_HOST.match(text):
        return 'http://' + text

    return 'https://' + text
