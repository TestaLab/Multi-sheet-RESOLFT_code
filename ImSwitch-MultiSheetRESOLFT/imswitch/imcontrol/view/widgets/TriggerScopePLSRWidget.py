import pyqtgraph as pg
from qtpy import QtCore, QtWidgets

from imswitch.imcontrol.view import guitools
from .basewidgets import Widget


class TriggerScopePLSRWidget(Widget):
    """ Widget containing scanner interface and beadscan reconstruction.
            This class uses the classes GraphFrame, MultipleScanWidget and IllumImageWidget"""

    sigSaveScanClicked = QtCore.Signal()
    sigLoadScanClicked = QtCore.Signal()
    sigRunScanClicked = QtCore.Signal()
    sigParameterChanged = QtCore.Signal()
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.setMinimumHeight(200)

        self.scanInLiveviewWar = QtWidgets.QMessageBox()
        self.scanInLiveviewWar.setInformativeText(
            "You need to be in liveview to scan")

        self.digModWarning = QtWidgets.QMessageBox()
        self.digModWarning.setInformativeText(
            "You need to be in digital laser modulation and external "
            "frame-trigger acquisition mode")
        self.scannerLabel = QtWidgets.QLabel('pLS-RESOLFT scanner')
        self.scannerLabel.setStyleSheet('font-size: 14pt; font-weight: bold')

        self.saveScanBtn = guitools.BetterPushButton('Save Scan')
        self.loadScanBtn = guitools.BetterPushButton('Load Scan')


        autoStartRecLabel = QtWidgets.QLabel('Auto-start REC')
        autoStartRecLabel.setAlignment(QtCore.Qt.AlignRight)
        self.autoStartRec = QtWidgets.QCheckBox()
        autoStopRecLabel = QtWidgets.QLabel('Auto-stop REC')
        autoStopRecLabel.setAlignment(QtCore.Qt.AlignRight)
        self.autoStopRec = QtWidgets.QCheckBox()
        self.scanButton = guitools.BetterPushButton('Run Scan')

        self.scrollContainer = QtWidgets.QGridLayout()
        self.scrollContainer.setContentsMargins(0, 0, 0, 0)
        self.setLayout(self.scrollContainer)

        self.grid = QtWidgets.QGridLayout()
        self.gridContainer = QtWidgets.QWidget()
        self.gridContainer.setLayout(self.grid)

        self.scrollArea = QtWidgets.QScrollArea()
        self.scrollArea.setFrameShape(QtWidgets.QFrame.NoFrame)
        self.scrollArea.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        self.scrollArea.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarAsNeeded)
        self.scrollArea.setWidget(self.gridContainer)
        self.scrollArea.setWidgetResizable(True)
        self.scrollContainer.addWidget(self.scrollArea)
        self.gridContainer.installEventFilter(self)

        """Scan value parameters"""
        self.scanPar = {}

        timeLapsePointsLabel = QtWidgets.QLabel('Time lapse timepoints')
        self.timeLapsePointsEdit = guitools.BetterSpinBox(allowScrollChanges=False)
        self.timeLapsePointsEdit.editingFinished.connect(self.sigParameterChanged)

        timeLapseDelayLabel = QtWidgets.QLabel('Time lapse delay (sec)')
        self.timeLapseDelayEdit = guitools.BetterDoubleSpinBox(allowScrollChanges=False)
        self.timeLapseDelayEdit.setMaximum(1000)
        self.timeLapseDelayEdit.editingFinished.connect(self.sigParameterChanged)

        delayBeforeOnLabel = QtWidgets.QLabel('Delay before on-pulse (in consecutive cycles) (ms)')
        self.delayBeforeOnEdit = guitools.BetterDoubleSpinBox(allowScrollChanges=False)
        self.delayBeforeOnEdit.editingFinished.connect(self.sigParameterChanged)

        onTimeLabel = QtWidgets.QLabel('On-pulse time (ms)')
        self.onTimeEdit = guitools.BetterDoubleSpinBox(allowScrollChanges=False)
        self.onTimeEdit.setMaximum(1000)
        self.onTimeEdit.editingFinished.connect(self.sigParameterChanged)

        delayAfterOnLabel = QtWidgets.QLabel('Delay after on-pulse (ms)')
        self.delayAfterOnEdit = guitools.BetterDoubleSpinBox(allowScrollChanges=False)
        self.delayAfterOnEdit.editingFinished.connect(self.sigParameterChanged)

        offTimeLabel = QtWidgets.QLabel('Off-pulse time (ms)')
        self.offTimeEdit = guitools.BetterDoubleSpinBox(allowScrollChanges=False)
        self.offTimeEdit.setMaximum(1000)
        self.offTimeEdit.editingFinished.connect(self.sigParameterChanged)

        delayAfterOffLabel = QtWidgets.QLabel('Delay after off-pulse (ms)')
        self.delayAfterOffEdit = guitools.BetterDoubleSpinBox(allowScrollChanges=False)
        self.delayAfterOffEdit.editingFinished.connect(self.sigParameterChanged)

        delayAfterDACStepLabel = QtWidgets.QLabel('Delay after DAC step (ms)')
        self.delayAfterDACStepEdit = guitools.BetterDoubleSpinBox(allowScrollChanges=False)
        self.delayAfterDACStepEdit.editingFinished.connect(self.sigParameterChanged)

        roTimeLabel = QtWidgets.QLabel('RO-pulse time (ms)')
        self.roTimeEdit = guitools.BetterDoubleSpinBox(allowScrollChanges=False)
        self.roTimeEdit.editingFinished.connect(self.sigParameterChanged)

        delayAfterRoLabel = QtWidgets.QLabel('Delay after RO-pulse (ms)')
        self.delayAfterRoEdit = guitools.BetterDoubleSpinBox(allowScrollChanges=False)
        self.delayAfterRoEdit.editingFinished.connect(self.sigParameterChanged)

        roRestingPosUmLabel = QtWidgets.QLabel('RO scan resting position (um)')
        self.roRestingPosUmEdit = guitools.BetterDoubleSpinBox(allowScrollChanges=False)
        self.roRestingPosUmEdit.setMinimum(-200)
        self.roRestingPosUmEdit.setMaximum(200)
        self.roRestingPosUmEdit.editingFinished.connect(self.sigParameterChanged)

        roStartPosUmLabel = QtWidgets.QLabel('RO scan start (um)')
        self.roStartPosUmEdit = guitools.BetterDoubleSpinBox(allowScrollChanges=False)
        self.roStartPosUmEdit.setMinimum(-200)
        self.roStartPosUmEdit.setMaximum(200)
        self.roStartPosUmEdit.editingFinished.connect(self.sigParameterChanged)

        roStepSizeUmLabel = QtWidgets.QLabel('RO scan step size (um)')
        self.roStepSizeUmEdit = guitools.BetterDoubleSpinBox(allowScrollChanges=False)
        self.roStepSizeUmEdit.setMinimum(-10)
        self.roStepSizeUmEdit.setMaximum(10)
        self.roStepSizeUmEdit.editingFinished.connect(self.sigParameterChanged)

        roStepsLabel = QtWidgets.QLabel('RO scan steps')
        self.roStepsEdit = guitools.BetterSpinBox(allowScrollChanges=False)
        self.roStepsEdit.setMaximum(10000)
        self.roStepsEdit.editingFinished.connect(self.sigParameterChanged)

        cycleStartPosUmLabel = QtWidgets.QLabel('Cycle scan start (um)')
        self.cycleStartPosUmEdit = guitools.BetterDoubleSpinBox(allowScrollChanges=False)
        self.cycleStartPosUmEdit.setMinimum(-200)
        self.cycleStartPosUmEdit.setMaximum(200)
        self.cycleStartPosUmEdit.editingFinished.connect(self.sigParameterChanged)

        cycleStepSizeUmLabel = QtWidgets.QLabel('Cycle scan step size (um)')
        self.cycleStepSizeUmEdit = guitools.BetterDoubleSpinBox(allowScrollChanges=False)
        self.cycleStepSizeUmEdit.setMinimum(-10)
        self.cycleStepSizeUmEdit.setMaximum(10)
        self.cycleStepSizeUmEdit.setDecimals(3)
        self.cycleStepSizeUmEdit.editingFinished.connect(self.sigParameterChanged)

        cycleStepsLabel = QtWidgets.QLabel('Cycle scan steps')
        self.cycleStepsEdit = guitools.BetterSpinBox(allowScrollChanges=False)
        self.cycleStepsEdit.setMaximum(1000)
        self.cycleStepsEdit.editingFinished.connect(self.sigParameterChanged)

        onLaserLabel = QtWidgets.QLabel('On laser')
        self.onLaserEdit = guitools.BetterComboBox(allowScrollChanges=False)

        offLaserLabel = QtWidgets.QLabel('Off laser')
        self.offLaserEdit = guitools.BetterComboBox(allowScrollChanges=False)

        roLaserLabel = QtWidgets.QLabel('Read-out laser')
        self.roLaserEdit = guitools.BetterComboBox(allowScrollChanges=False)

        roScanDeviceLabel = QtWidgets.QLabel('RO scan device')
        self.roScanDeviceEdit = guitools.BetterComboBox(allowScrollChanges=False)

        cycleScanDeviceLabel = QtWidgets.QLabel('Cycle scan device is now hard coded same as RO-device')
        self.cycleScanDeviceEdit = guitools.BetterComboBox(allowScrollChanges=False)

        # Temp fix
        self.cycleScanDeviceEdit.setEnabled(False)

        currentRow = 0

        # Add space item to make the grid look nicer
        self.grid.addItem(
            QtWidgets.QSpacerItem(20, 40,
                                  QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Expanding),
            currentRow, 0, 1, -1
        )
        currentRow += 1

        # Add scanner label
        self.grid.addWidget(self.scannerLabel, currentRow, 0)
        currentRow += 1

        # Add general buttons
        self.grid.addWidget(self.loadScanBtn, currentRow, 0)
        self.grid.addWidget(self.saveScanBtn, currentRow, 1)
        self.grid.addItem(
            QtWidgets.QSpacerItem(40, 20,
                                  QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Minimum),
            currentRow, 3
        )
        self.grid.addWidget(autoStartRecLabel, currentRow, 2)
        self.grid.addWidget(self.autoStartRec, currentRow, 3)
        currentRow += 1
        self.grid.addWidget(autoStopRecLabel, currentRow, 2)
        self.grid.addWidget(self.autoStopRec, currentRow, 3)
        currentRow += 1
        self.grid.addWidget(self.scanButton, currentRow, 3)
        currentRow += 1
        self.grid.addItem(
            QtWidgets.QSpacerItem(40, 20,
                                  QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Expanding),
            currentRow, 0, 1, 4)
        currentRow += 1
        self.grid.addWidget(timeLapsePointsLabel, currentRow, 0)
        self.grid.addWidget(self.timeLapsePointsEdit, currentRow, 1)
        self.grid.addWidget(timeLapseDelayLabel, currentRow, 2)
        self.grid.addWidget(self.timeLapseDelayEdit, currentRow, 3)
        currentRow += 1
        self.grid.addItem(
            QtWidgets.QSpacerItem(40, 20,
                                  QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Expanding),
            currentRow, 0, 1, 4)
        currentRow += 1
        self.grid.addWidget(delayBeforeOnLabel, currentRow, 0)
        self.grid.addWidget(self.delayBeforeOnEdit, currentRow, 1)
        self.grid.addWidget(roRestingPosUmLabel, currentRow, 2)
        self.grid.addWidget(self.roRestingPosUmEdit, currentRow, 3)
        currentRow += 1
        self.grid.addWidget(onTimeLabel, currentRow, 0)
        self.grid.addWidget(self.onTimeEdit, currentRow, 1)
        self.grid.addWidget(roStartPosUmLabel, currentRow, 2)
        self.grid.addWidget(self.roStartPosUmEdit, currentRow, 3)
        currentRow += 1
        self.grid.addWidget(delayAfterOnLabel, currentRow, 0)
        self.grid.addWidget(self.delayAfterOnEdit, currentRow, 1)
        self.grid.addWidget(roStepSizeUmLabel, currentRow, 2)
        self.grid.addWidget(self.roStepSizeUmEdit, currentRow, 3)
        currentRow += 1
        self.grid.addWidget(offTimeLabel, currentRow, 0)
        self.grid.addWidget(self.offTimeEdit, currentRow, 1)
        self.grid.addWidget(roStepsLabel, currentRow, 2)
        self.grid.addWidget(self.roStepsEdit, currentRow, 3)
        currentRow += 1
        self.grid.addWidget(delayAfterOffLabel, currentRow, 0)
        self.grid.addWidget(self.delayAfterOffEdit, currentRow, 1)
        self.grid.addWidget(cycleStartPosUmLabel, currentRow, 2)
        self.grid.addWidget(self.cycleStartPosUmEdit, currentRow, 3)
        currentRow += 1
        self.grid.addWidget(delayAfterDACStepLabel, currentRow, 0)
        self.grid.addWidget(self.delayAfterDACStepEdit, currentRow, 1)
        self.grid.addWidget(cycleStepSizeUmLabel, currentRow, 2)
        self.grid.addWidget(self.cycleStepSizeUmEdit, currentRow, 3)
        currentRow += 1
        self.grid.addWidget(roTimeLabel, currentRow, 0)
        self.grid.addWidget(self.roTimeEdit, currentRow, 1)
        self.grid.addWidget(cycleStepsLabel, currentRow, 2)
        self.grid.addWidget(self.cycleStepsEdit, currentRow, 3)
        currentRow += 1
        self.grid.addWidget(delayAfterRoLabel, currentRow, 0)
        self.grid.addWidget(self.delayAfterRoEdit, currentRow, 1)
        currentRow += 1
        self.grid.addItem(
            QtWidgets.QSpacerItem(40, 20,
                                  QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Expanding),
            currentRow, 0, 1, 4)
        currentRow += 1
        self.grid.addWidget(onLaserLabel, currentRow, 0)
        self.grid.addWidget(self.onLaserEdit, currentRow, 1)
        self.grid.addWidget(roScanDeviceLabel, currentRow, 2)
        self.grid.addWidget(self.roScanDeviceEdit, currentRow, 3)
        currentRow += 1
        self.grid.addWidget(offLaserLabel, currentRow, 0)
        self.grid.addWidget(self.offLaserEdit, currentRow, 1)
        self.grid.addWidget(cycleScanDeviceLabel, currentRow, 2)
        self.grid.addWidget(self.cycleScanDeviceEdit, currentRow, 3)
        currentRow += 1
        self.grid.addWidget(roLaserLabel, currentRow, 0)
        self.grid.addWidget(self.roLaserEdit, currentRow, 1)

        # Connect signals
        self.saveScanBtn.clicked.connect(self.sigSaveScanClicked)
        self.loadScanBtn.clicked.connect(self.sigLoadScanClicked)
        self.scanButton.clicked.connect(self.sigRunScanClicked)


    def getTimeLapsePoints(self):
        return self.timeLapsePointsEdit.value()

    def setTimeLapsePoints(self, value):
        self.timeLapsePointsEdit.setValue(value)

    def getTimeLapseDelayS(self):
        return self.timeLapseDelayEdit.value()

    def setTimeLapseDelayS(self, value):
        self.timeLapseDelayEdit.setValue(value)

    def getDelayBeforeOnTimeMs(self):
        return self.delayBeforeOnEdit.value()

    def setDelayBeforeOnTimeMs(self, value):
        self.delayBeforeOnEdit.setValue(value)

    def getOnTimeMs(self):
        return self.onTimeEdit.value()

    def setOnTimeMs(self, value):
        self.onTimeEdit.setValue(value)

    def getDelayAfterOnTimeMs(self):
        return self.delayAfterOnEdit.value()

    def setDelayAfterOnTimeMs(self, value):
        self.delayAfterOnEdit.setValue(value)

    def getOffTimeMs(self):
        return self.offTimeEdit.value()

    def setOffTimeMs(self, value):
        self.offTimeEdit.setValue(value)

    def getDelayAfterOffTimeMs(self):
        return self.delayAfterOffEdit.value()

    def setDelayAfterOffTimeMs(self, value):
        self.delayAfterOffEdit.setValue(value)

    def getDelayAfterDACStepMs(self):
        return self.delayAfterDACStepEdit.value()

    def setDelayAfterDACStepMs(self, value):
        self.delayAfterDACStepEdit.setValue(value)

    def getRoTimeMs(self):
        return self.roTimeEdit.value()

    def setRoTimeMs(self, value):
        self.roTimeEdit.setValue(value)
    def getDelayAfterRoMs(self):
        return self.delayAfterRoEdit.value()
    def setDelayAfterRoMs(self, value):
        self.delayAfterRoEdit.setValue(value)
    def getRoRestingPosUm(self):
        return self.roRestingPosUmEdit.value()

    def setRoRestingPosUm(self, value):
        self.roRestingPosUmEdit.setValue(value)

    def getRoStartPosUm(self):
        return self.roStartPosUmEdit.value()

    def setRoStartPosUm(self, value):
        self.roStartPosUmEdit.setValue(value)

    def getRoStepSizeUm(self):
        return self.roStepSizeUmEdit.value()

    def setRoStepSizeUm(self, value):
        self.roStepSizeUmEdit.setValue(value)

    def getRoSteps(self):
        return self.roStepsEdit.value()

    def setRoSteps(self, value):
        self.roStepsEdit.setValue(value)

    def getCycleStartPosUm(self):
        return self.cycleStartPosUmEdit.value()

    def setCycleStartPosUm(self, value):
        self.cycleStartPosUmEdit.setValue(value)

    def getCycleStepSizeUm(self):
        return self.cycleStepSizeUmEdit.value()

    def setCycleStepSizeUm(self, value):
        self.cycleStepSizeUmEdit.setValue(value)

    def getCycleSteps(self):
        return self.cycleStepsEdit.value()

    def setCycleSteps(self, value):
        self.cycleStepsEdit.setValue(value)

    def getOnLaser(self):
        return self.onLaserEdit.currentText()

    def setOnLaser(self, value):
        ind = self.onLaserEdit.findText(value)
        self.onLaserEdit.setCurrentIndex(ind)

    def getOffLaser(self):
        return self.offLaserEdit.currentText()

    def setOffLaser(self, value):
        ind = self.offLaserEdit.findText(value)
        self.offLaserEdit.setCurrentIndex(ind)

    def getRoLaser(self):
        return self.roLaserEdit.currentText()

    def setRoLaser(self, value):
        ind = self.roLaserEdit.findText(value)
        self.roLaserEdit.setCurrentIndex(ind)

    def getRoScanDevice(self):
        return self.roScanDeviceEdit.currentText()

    def setRoScanDevice(self, value):
        ind = self.roScanDeviceEdit.findText(value)
        self.roScanDeviceEdit.setCurrentIndex(ind)

    def getCycleScanDevice(self):
        return self.cycleScanDeviceEdit.currentText()

    def setCycleScanDevice(self, value):
        ind = self.cycleScanDeviceEdit.findText(value)
        self.cycleScanDeviceEdit.setCurrentIndex(ind)

    def setScanButtonChecked(self, checked):
        self.scanButton.setEnabled(not checked)
        self.scanButton.setCheckable(checked)
        self.scanButton.setChecked(checked)



    def plotSignalGraph(self, areas, signals, colors):
        if len(areas) != len(signals) or len(signals) != len(colors):
            raise ValueError('Arguments "areas", "signals" and "colors" must be of equal length')

        self.graph.plot.clear()
        for i in range(len(areas)):
            self.graph.plot.plot(areas[i], signals[i], pen=pg.mkPen(colors[i]))

        self.graph.plot.setYRange(-0.1, 1.1)

    def eventFilter(self, source, event):
        if source is self.gridContainer and event.type() == QtCore.QEvent.Resize:
            # Set correct minimum width (otherwise things can go outside the widget because of the
            # scroll area)
            width = self.gridContainer.minimumSizeHint().width() \
                    + self.scrollArea.verticalScrollBar().width()
            self.scrollArea.setMinimumWidth(width)
            self.setMinimumWidth(width)

        return False


class GraphFrame(pg.GraphicsLayoutWidget):
    """Creates the plot that plots the preview of the pulses."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.plot = self.addPlot(row=1, col=0)


# Copyright (C) 2020-2021 ImSwitch developers
# This file is part of ImSwitch.
#
# ImSwitch is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# ImSwitch is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.
