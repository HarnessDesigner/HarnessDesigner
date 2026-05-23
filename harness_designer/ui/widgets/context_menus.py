from PySide6 import QtWidgets


class Rotate2DMenu(QtWidgets.QMenu):
    """Represent a rotate 2dmenu in :mod:`harness_designer.ui.widgets.context_menus`.

    UNKNOWN details are inferred from the class name and surrounding code.
    """

    def __init__(self, canvas, obj):
        """Initialise the :class:`Rotate2DMenu` instance.

        UNKNOWN details are inferred from the callable name and signature.

        :param canvas: Canvas instance.
        :type canvas: UNKNOWN
        :param obj: Object instance to operate on.
        :type obj: UNKNOWN
        """
        super().__init__(canvas)
        self.selected = obj
        self.canvas = canvas

        act = self.addAction('Clockwise 90\u00b0')
        act.triggered.connect(self.on_pos_90)

        act = self.addAction('Counter Clockwise 90\u00b0')
        act.triggered.connect(self.on_neg_90)

        self.addSeparator()
        act = self.addAction('Rotate 180\u00b0')
        act.triggered.connect(self.on_pos_180)

    def on_pos_90(self):
        """Handle the pos 90 event.

        UNKNOWN details are inferred from the callable name and signature.
        """
        pass

    def on_neg_90(self):
        """Handle the neg 90 event.

        UNKNOWN details are inferred from the callable name and signature.
        """
        pass

    def on_pos_180(self):
        """Handle the pos 180 event.

        UNKNOWN details are inferred from the callable name and signature.
        """
        pass


class Mirror2DMenu(QtWidgets.QMenu):
    """Represent a mirror 2dmenu in :mod:`harness_designer.ui.widgets.context_menus`.

    UNKNOWN details are inferred from the class name and surrounding code.
    """

    def __init__(self, canvas, obj):
        """Initialise the :class:`Mirror2DMenu` instance.

        UNKNOWN details are inferred from the callable name and signature.

        :param canvas: Canvas instance.
        :type canvas: UNKNOWN
        :param obj: Object instance to operate on.
        :type obj: UNKNOWN
        """
        super().__init__(canvas)
        self.selected = obj
        self.canvas = canvas

        act = self.addAction('X')
        act.triggered.connect(self.on_x)

        act = self.addAction('Y')
        act.triggered.connect(self.on_y)

    def on_x(self):
        """Handle the x event.

        UNKNOWN details are inferred from the callable name and signature.
        """
        pass

    def on_y(self):
        """Handle the y event.

        UNKNOWN details are inferred from the callable name and signature.
        """
        pass


class Rotate3DMenu(QtWidgets.QMenu):
    """Represent a rotate 3dmenu in :mod:`harness_designer.ui.widgets.context_menus`.

    UNKNOWN details are inferred from the class name and surrounding code.
    """

    def __init__(self, canvas, selected):
        """Initialise the :class:`Rotate3DMenu` instance.

        UNKNOWN details are inferred from the callable name and signature.

        :param canvas: Canvas instance.
        :type canvas: UNKNOWN
        :param selected: Value for ``selected``.
        :type selected: UNKNOWN
        """
        super().__init__(canvas)
        self.selected = selected
        self.canvas = canvas

        for label, slot in [('X +90\u00b0', self.on_x_pos_90),
                            ('X -90\u00b0', self.on_x_neg_90),
                            None,
                            ('Y +90\u00b0', self.on_y_pos_90),
                            ('Y -90\u00b0', self.on_y_neg_90),
                            None,
                            ('Z +90\u00b0', self.on_z_pos_90),
                            ('Z -90\u00b0', self.on_z_neg_90)]:

            if label is None:
                self.addSeparator()
            else:
                self.addAction(label).triggered.connect(slot)

    def on_x_pos_90(self):
        """Handle the x pos 90 event.

        UNKNOWN details are inferred from the callable name and signature.
        """
        pass

    def on_x_neg_90(self):
        """Handle the x neg 90 event.

        UNKNOWN details are inferred from the callable name and signature.
        """
        pass

    def on_y_pos_90(self):
        """Handle the y pos 90 event.

        UNKNOWN details are inferred from the callable name and signature.
        """
        pass

    def on_y_neg_90(self):
        """Handle the y neg 90 event.

        UNKNOWN details are inferred from the callable name and signature.
        """
        pass

    def on_z_pos_90(self):
        """Handle the z pos 90 event.

        UNKNOWN details are inferred from the callable name and signature.
        """
        pass

    def on_z_neg_90(self):
        """Handle the z neg 90 event.

        UNKNOWN details are inferred from the callable name and signature.
        """
        pass


class Mirror3DMenu(QtWidgets.QMenu):
    """Represent a mirror 3dmenu in :mod:`harness_designer.ui.widgets.context_menus`.

    UNKNOWN details are inferred from the class name and surrounding code.
    """

    def __init__(self, canvas, selected):
        """Initialise the :class:`Mirror3DMenu` instance.

        UNKNOWN details are inferred from the callable name and signature.

        :param canvas: Canvas instance.
        :type canvas: UNKNOWN
        :param selected: Value for ``selected``.
        :type selected: UNKNOWN
        """
        super().__init__(canvas)
        self.selected = selected
        self.canvas = canvas

        for label, slot in [
            ('X', self.on_x),
            ('Y', self.on_y),
            ('Z', self.on_z),
        ]:
            self.addAction(label).triggered.connect(slot)

    def on_x(self):
        """Handle the x event.

        UNKNOWN details are inferred from the callable name and signature.
        """
        pass

    def on_y(self):
        """Handle the y event.

        UNKNOWN details are inferred from the callable name and signature.
        """
        pass

    def on_z(self):
        """Handle the z event.

        UNKNOWN details are inferred from the callable name and signature.
        """
        pass
