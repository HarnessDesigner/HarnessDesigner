# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

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

        self.addAction('X +90\u00b0').triggered.connect(self.on_x_pos_90)
        self.addAction('X -90\u00b0').triggered.connect(self.on_x_neg_90)
        self.addSeparator()
        self.addAction('Y +90\u00b0').triggered.connect(self.on_y_pos_90)
        self.addAction('Y -90\u00b0').triggered.connect(self.on_y_neg_90)
        self.addSeparator()
        self.addAction('Z +90\u00b0').triggered.connect(self.on_z_pos_90)
        self.addAction('Z -90\u00b0').triggered.connect(self.on_z_neg_90)

    def on_x_pos_90(self):
        """Handle the x pos 90 event.

        UNKNOWN details are inferred from the callable name and signature.
        """
        x = self.selected.obj3d.angle.x
        x += 90.0
        if x > 180.0:
            x -= 360.0

        self.selected.obj3d.angle.x = x

    def on_x_neg_90(self):
        """Handle the x neg 90 event.

        UNKNOWN details are inferred from the callable name and signature.
        """
        x = self.selected.obj3d.angle.x
        x -= 90.0
        if x < -180.0:
            x += 360.0

        self.selected.obj3d.angle.x = x

    def on_y_pos_90(self):
        """Handle the y pos 90 event.

        UNKNOWN details are inferred from the callable name and signature.
        """
        y = self.selected.obj3d.angle.y
        y += 90.0
        if y > 180.0:
            y -= 360.0

        self.selected.obj3d.angle.y = y

    def on_y_neg_90(self):
        """Handle the y neg 90 event.

        UNKNOWN details are inferred from the callable name and signature.
        """
        y = self.selected.obj3d.angle.y
        y -= 90.0
        if y < -180.0:
            y += 360.0

        self.selected.obj3d.angle.y = y

    def on_z_pos_90(self):
        """Handle the z pos 90 event.

        UNKNOWN details are inferred from the callable name and signature.
        """
        z = self.selected.obj3d.angle.z
        z += 90.0
        if z > 180.0:
            z -= 360.0

        self.selected.obj3d.angle.z = z

    def on_z_neg_90(self):
        """Handle the z neg 90 event.

        UNKNOWN details are inferred from the callable name and signature.
        """
        z = self.selected.obj3d.angle.z
        z -= 90.0
        if z < -180.0:
            z += 360.0

        self.selected.obj3d.angle.z = z


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
        self.addAction('X').triggered.connect(self.on_x)
        self.addAction('Y').triggered.connect(self.on_y)
        self.addAction('Z').triggered.connect(self.on_z)

    def on_x(self):
        """Handle the x event.

        UNKNOWN details are inferred from the callable name and signature.
        """

        x = self.selected.obj3d.angle.x
        x += 180.0
        if x > 180.0:
            x -= 360.0

        self.selected.obj3d.angle.x = x

    def on_y(self):
        """Handle the y event.

        UNKNOWN details are inferred from the callable name and signature.
        """
        y = self.selected.obj3d.angle.y
        y += 180.0
        if y > 180.0:
            y -= 360.0

        self.selected.obj3d.angle.y = y

    def on_z(self):
        """Handle the z event.

        UNKNOWN details are inferred from the callable name and signature.
        """
        z = self.selected.obj3d.angle.z
        z += 180.0
        if z > 180.0:
            z -= 360.0

        self.selected.obj3d.angle.z = z
