from qtpy import QtCore, QtGui, QtWidgets
from .basewidgets import Widget
from imswitch.imcontrol.view import guitools

class BSC203Widget(Widget):
    sigHomeAll = QtCore.Signal()

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setWindowTitle('NanoMax Stepper motor controller')


        """GUI elements"""

        self.homeBtn = guitools.BetterPushButton('Home all motors')
        self.homeBtn.clicked.connect(self.homeClicked)

        self.XYVelLabel = QtWidgets.QLabel('X/Y velocity [um/s]')
        self.XYVelEdit = guitools.BetterDoubleSpinBox(allowScrollChanges=False)
        self.XYVelEdit.setMaximum(2000)
        self.XYVelEdit.setMinimum(0)

        self.ZVelLabel = QtWidgets.QLabel('Z velocity [um/s]')
        self.ZVelEdit = guitools.BetterDoubleSpinBox(allowScrollChanges=False)
        self.ZVelEdit.setMaximum(2000)
        self.ZVelEdit.setMinimum(0)

        self.setPosLabel = QtWidgets.QLabel('Set absolute position [um]')

        self.setXLabel = QtWidgets.QLabel('X')
        self.setXEdit = guitools.BetterDoubleSpinBox(allowScrollChanges=False)
        self.setXEdit.setMaximum(8000)
        self.setXEdit.setMinimum(-500)
        self.setYLabel = QtWidgets.QLabel('Y')
        self.setYEdit = guitools.BetterDoubleSpinBox(allowScrollChanges=False)
        self.setYEdit.setMaximum(8000)
        self.setYEdit.setMinimum(-500)
        self.setZLabel = QtWidgets.QLabel('Z')
        self.setZEdit = guitools.BetterDoubleSpinBox(allowScrollChanges=False)
        self.setZEdit.setMaximum(8000)
        self.setZEdit.setMinimum(-500)

        self.moveToBtn = guitools.BetterPushButton('Move to pos')
        self.stopBtn = guitools.BetterPushButton('Stop movement')

        self.pos0Label = QtWidgets.QLabel('X position [µm]')
        self.pos0EditLabel = QtWidgets.QLabel()
        self.pos1Label = QtWidgets.QLabel('Y position [µm]')
        self.pos1EditLabel = QtWidgets.QLabel()
        self.pos2Label = QtWidgets.QLabel('Z position [µm]')
        self.pos2EditLabel = QtWidgets.QLabel()

        # Add elements to GridLayout
        grid = QtWidgets.QGridLayout()
        self.setLayout(grid)

        grid.addWidget(self.XYVelLabel, 0, 0, 1, 1)
        grid.addWidget(self.XYVelEdit, 0, 1, 1, 1)
        grid.addWidget(self.ZVelLabel, 1, 0, 1, 1)
        grid.addWidget(self.ZVelEdit, 1, 1, 1, 1)
        grid.addWidget(self.setPosLabel, 2, 0, 1, 2)
        grid.addWidget(self.setXLabel, 3, 0, 1, 1)
        grid.addWidget(self.setXEdit, 3, 1, 1, 1)
        grid.addWidget(self.setYLabel, 4, 0, 1, 1)
        grid.addWidget(self.setYEdit, 4, 1, 1, 1)
        grid.addWidget(self.setZLabel, 5, 0, 1, 1)
        grid.addWidget(self.setZEdit, 5, 1, 1, 1)
        grid.addWidget(self.moveToBtn, 6, 0, 1, 2)
        grid.addWidget(self.stopBtn, 7, 0, 1, 2)
        grid.addWidget(self.pos0Label, 8, 0, 1, 1)
        grid.addWidget(self.pos0EditLabel, 8, 1, 1, 1)
        grid.addWidget(self.pos1Label, 9, 0, 1, 1)
        grid.addWidget(self.pos1EditLabel, 9, 1, 1, 1)
        grid.addWidget(self.pos2Label, 10, 0, 1, 1)
        grid.addWidget(self.pos2EditLabel, 10, 1, 1, 1)
        grid.addWidget(self.homeBtn, 11, 0, 1, 2)

        self.msg = QtWidgets.QMessageBox

        self.setFocusPolicy(QtCore.Qt.StrongFocus)

    def homeClicked(self):
        answer = self.msg.question(self, '', "Are you sure you want to home all the motors?", self.msg.Yes | self.msg.No)
        if answer == self.msg.Yes:
            self.sigHomeAll.emit()
