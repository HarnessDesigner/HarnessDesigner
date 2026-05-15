from PySide6 import QtWidgets


class Rotate2DMenu(QtWidgets.QMenu):

    def __init__(self, canvas, obj):
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
        pass

    def on_neg_90(self):
        pass

    def on_pos_180(self):
        pass


class Mirror2DMenu(QtWidgets.QMenu):

    def __init__(self, canvas, obj):
        super().__init__(canvas)
        self.selected = obj
        self.canvas = canvas

        act = self.addAction('X')
        act.triggered.connect(self.on_x)

        act = self.addAction('Y')
        act.triggered.connect(self.on_y)

    def on_x(self):
        pass

    def on_y(self):
        pass


class Rotate3DMenu(QtWidgets.QMenu):

    def __init__(self, canvas, selected):
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
        pass

    def on_x_neg_90(self):
        pass

    def on_y_pos_90(self):
        pass

    def on_y_neg_90(self):
        pass

    def on_z_pos_90(self):
        pass

    def on_z_neg_90(self):
        pass


class Mirror3DMenu(QtWidgets.QMenu):

    def __init__(self, canvas, selected):
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
        pass

    def on_y(self):
        pass

    def on_z(self):
        pass
