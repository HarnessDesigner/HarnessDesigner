# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

"""Reading and writing the scraper scripts the user edits.

Writes are atomic: the text goes to a temporary file in the same folder and
is then swapped into place, so a crash or a full disk in the middle of a
save leaves the previous version of the script intact rather than half a
file.
"""

import os
import tempfile

from .. import check_types as _check_types

ENCODING = 'utf-8'
SCRATCH_NAME = 'scratch_script.py'


@_check_types.do
def read_script(path: str) -> str:
    """The script at *path*. Line endings are normalized to ``\\n``.

    :raises OSError: It cannot be read.
    :raises UnicodeDecodeError: It is not UTF-8 text.
    """
    with open(path, 'r', encoding=ENCODING, newline=None) as handle:
        return handle.read()


@_check_types.do
def write_script(path: str, text: str) -> None:
    """Save *text* as the script at *path*, replacing it atomically.

    :raises OSError: It cannot be written; the existing file is untouched.
    """
    folder = os.path.dirname(os.path.abspath(path))
    os.makedirs(folder, exist_ok=True)

    handle, temporary = tempfile.mkstemp(prefix='.script-', suffix='.tmp', dir=folder)
    try:
        with os.fdopen(handle, 'w', encoding=ENCODING, newline='\n') as stream:
            stream.write(text)

        os.replace(temporary, path)
    except BaseException:
        if os.path.exists(temporary):
            os.remove(temporary)

        raise


@_check_types.do
def scratch_path(app_data: str) -> str:
    """Where the unsaved working script is kept between sessions."""
    return os.path.join(app_data, 'scraper', SCRATCH_NAME)
