# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

from PySide6 import QtWidgets

from ... import check_types as _check_types


class Category(QtWidgets.QScrollArea):
    """Represent a category in :mod:`harness_designer.ui.prop_ctrls.category`.

    UNKNOWN details are inferred from the class name and surrounding code.
    """

    @_check_types.do
    def __init__(self, parent: QtWidgets.QWidget, label: str) -> None:
        """Initialise the :class:`Category` instance.

        UNKNOWN details are inferred from the callable name and signature.

        :param parent: Parent object.
        :type parent: UNKNOWN
        :param label: Value for ``label``.
        :type label: UNKNOWN
        """
        QtWidgets.QScrollArea.__init__(self, parent)
        self._label = label

        self._container = QtWidgets.QWidget()
        self._sizer = QtWidgets.QVBoxLayout()
        self._sizer.setContentsMargins(3, 3, 3, 3)
        self._sizer.addStretch(1)
        self._container.setLayout(self._sizer)

        self.setWidget(self._container)
        self.setWidgetResizable(True)

    @_check_types.do
    def GetLabel(self) -> str:
        """Execute the get label operation.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Return value. UNKNOWN details.
        :rtype: UNKNOWN
        """
        return self._label

    @_check_types.do
    def SetLabel(self, value: str) -> None:
        """Execute the set label operation.

        UNKNOWN details are inferred from the callable name and signature.

        :param value: Value to store or process.
        :type value: UNKNOWN
        """
        self._label = value

    @_check_types.do
    def addWidget(self, widget: QtWidgets.QWidget) -> None:
        """Add a property widget to this category."""
        pos = self._sizer.count() - 1
        self._sizer.insertWidget(pos, widget)

