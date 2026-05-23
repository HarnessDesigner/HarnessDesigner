# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

"""Compatibility stub preserved for legacy imports."""

# monkey_patch.py
#
# Under wxPython on Windows 10/11, there was a bug in wxWidgets where window
# size and position were not calculated correctly due to invisible window
# borders. This entire module existed to work around that bug by patching
# wx.Frame and wx.Dialog with corrected geometry methods.
#
# Under PySide6 / Qt, this bug does not exist. Qt's QMainWindow and QDialog
# handle geometry correctly on all platforms natively. This module is kept as
# a no-op stub so that the import in __init__.py continues to work without
# modification.

# Previously exported by this module — kept as a no-op for any callers.
def get_offsets(_hwnd):
    """Return zero window-border offsets for Qt compatibility.

    :param _hwnd: Legacy native window handle. UNKNOWN under Qt.
    :type _hwnd: UNKNOWN
    :returns: Four zero offsets.
    :rtype: tuple[int, int, int, int]
    """
    return 0, 0, 0, 0
