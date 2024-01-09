import numpy as np
import pyqtgraph as pg
from pyqtgraph.dockarea import Dock, DockArea
from pyqtgraph.parametertree import Parameter, ParameterTree
from qtpy import QtCore, QtWidgets

from imswitch.imcommon.view import PickDatasetsDialog
from .DataFrame import DataFrame
from .MultiDataFrame import MultiDataFrame
from .ReconstructionView import ReconstructionView
from .ScanParamsDialog import ScanParamsDialog
from .guitools import BetterPushButton


class ImRecMainView(QtWidgets.QMainWindow):
    sigSaveReconstruction = QtCore.Signal()
    sigSaveReconstructionAll = QtCore.Signal()
    sigSaveCoeffs = QtCore.Signal()
    sigSaveCoeffsAll = QtCore.Signal()
    sigSetDataFolder = QtCore.Signal()
    sigSetSaveFolder = QtCore.Signal()

    sigReconstuctCurrent = QtCore.Signal()
    sigReconstructMultiConsolidated = QtCore.Signal()
    sigReconstructMultiIndividual = QtCore.Signal()
    sigQuickLoadData = QtCore.Signal()
    sigUpdate = QtCore.Signal()

    sigShowScanParamsClicked = QtCore.Signal()

    sigClosing = QtCore.Signal()

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setWindowTitle('Image Reconstruction')

        # self parameters
        self.timepoints_text = 'Timepoints'

        # Actions in menubar
        menuBar = self.menuBar()
        file = menuBar.addMenu('&File')

        quickLoadAction = QtWidgets.QAction('Quick load data…', self)
        quickLoadAction.setShortcut('Ctrl+T')
        quickLoadAction.triggered.connect(self.sigQuickLoadData)
        file.addAction(quickLoadAction)

        file.addSeparator()

        saveReconAction = QtWidgets.QAction('Save reconstruction…', self)
        saveReconAction.setShortcut('Ctrl+D')
        saveReconAction.triggered.connect(self.sigSaveReconstruction)
        file.addAction(saveReconAction)
        saveReconAllAction = QtWidgets.QAction('Save all reconstructions…', self)
        saveReconAllAction.setShortcut('Ctrl+Shift+D')
        saveReconAllAction.triggered.connect(self.sigSaveReconstructionAll)
        file.addAction(saveReconAllAction)
        saveCoeffsAction = QtWidgets.QAction('Save coefficients of reconstruction…', self)
        saveCoeffsAction.setShortcut('Ctrl+A')
        saveCoeffsAction.triggered.connect(self.sigSaveCoeffs)
        file.addAction(saveCoeffsAction)
        saveCoeffsAllAction = QtWidgets.QAction('Save all coefficients…', self)
        saveCoeffsAllAction.setShortcut('Ctrl+Shift+A')
        saveCoeffsAllAction.triggered.connect(self.sigSaveCoeffsAll)
        file.addAction(saveCoeffsAllAction)

        file.addSeparator()

        setDataFolder = QtWidgets.QAction('Set default data folder…', self)
        setDataFolder.triggered.connect(self.sigSetDataFolder)
        file.addAction(setDataFolder)

        setSaveFolder = QtWidgets.QAction('Set default save folder…', self)
        setSaveFolder.triggered.connect(self.sigSetSaveFolder)
        file.addAction(setSaveFolder)

        self.dataFrame = DataFrame()
        self.multiDataFrame = MultiDataFrame()

        btnFrame = BtnFrame()
        btnFrame.sigReconstuctCurrent.connect(self.sigReconstuctCurrent)
        btnFrame.sigReconstructMultiConsolidated.connect(self.sigReconstructMultiConsolidated)
        btnFrame.sigReconstructMultiIndividual.connect(self.sigReconstructMultiIndividual)
        btnFrame.sigQuickLoadData.connect(self.sigQuickLoadData)
        btnFrame.sigUpdate.connect(self.sigUpdate)

        self.reconstructionWidget = ReconstructionView()

        self.parTree = ReconParTree()

        self.parTree.p.param('Autoreconstruct data from module').setValue(False)
        self.parTree.p.param('Reconstruction options').param('Restack before deskewing').setValue(True)

        self.pickDatasetsDialog = PickDatasetsDialog(self, allowMultiSelect=True)

        parameterFrame = QtWidgets.QFrame()
        parameterGrid = QtWidgets.QGridLayout()
        parameterFrame.setLayout(parameterGrid)
        parameterGrid.addWidget(self.parTree, 0, 0)

        DataDock = DockArea()

        self.multiDataDock = Dock('Multidata management')
        self.multiDataDock.addWidget(self.multiDataFrame)
        DataDock.addDock(self.multiDataDock)

        self.currentDataDock = Dock('Current data')
        self.currentDataDock.addWidget(self.dataFrame)
        DataDock.addDock(self.currentDataDock, 'above', self.multiDataDock)

        layout = QtWidgets.QHBoxLayout()
        self.cwidget = QtWidgets.QWidget()
        self.setCentralWidget(self.cwidget)
        self.cwidget.setLayout(layout)

        leftContainer = QtWidgets.QVBoxLayout()
        leftContainer.setContentsMargins(0, 0, 0, 0)

        rightContainer = QtWidgets.QVBoxLayout()
        rightContainer.setContentsMargins(0, 0, 0, 0)

        leftContainer.addWidget(parameterFrame, 1)
        leftContainer.addWidget(btnFrame, 0)
        leftContainer.addWidget(DataDock, 1)
        rightContainer.addWidget(self.reconstructionWidget)

        layout.addLayout(leftContainer, 1)
        layout.addLayout(rightContainer, 3)

        pg.setConfigOption('imageAxisOrder', 'row-major')

    def requestFilePathFromUser(self, caption=None, defaultFolder=None, nameFilter=None,
                                isSaving=False):
        func = (QtWidgets.QFileDialog().getOpenFileName if not isSaving
                else QtWidgets.QFileDialog().getSaveFileName)

        return func(self, caption=caption, directory=defaultFolder, filter=nameFilter)[0]

    def requestFolderPathFromUser(self, caption=None, defaultFolder=None):
        return QtWidgets.QFileDialog.getExistingDirectory(caption=caption, directory=defaultFolder)

    def raiseCurrentDataDock(self):
        self.currentDataDock.raiseDock()

    def raiseMultiDataDock(self):
        self.multiDataDock.raiseDock()

    def addNewReconstruction(self, reconObj, name):
        self.reconstructionWidget.addNewData(reconObj, name)

    def getMultiDatas(self):
        dataList = self.multiDataFrame.dataList
        for i in range(dataList.count()):
            yield dataList.item(i).data(1)

    def showScanParamsDialog(self, blocking=False):
        if blocking:
            result = self.scanParamsDialog.exec_()
            return result == QtWidgets.QDialog.Accepted
        else:
            self.scanParamsDialog.show()

    def showPickDatasetsDialog(self, blocking=False):
        if blocking:
            result = self.pickDatasetsDialog.exec_()
            return result == QtWidgets.QDialog.Accepted
        else:
            self.pickDatasetsDialog.show()

    def getComputeDevice(self):
        return self.parTree.p.param('CPU/GPU').value()

    def getPixelSizeNm(self):
        return self.parTree.p.param('Pixel size').value()

    def getDeltaY(self):
        return self.parTree.p.param('Acquisition parameters').param('Delta-Y step size').value()

    def getSkewAngleRad(self):
        return np.deg2rad(self.parTree.p.param('Acquisition parameters').param('Skew angle').value())

    def getCycles(self):
        return self.parTree.p.param('Acquisition parameters').param('Cycles').value()

    def getPosScanDirection(self):
        return self.parTree.p.param('Acquisition parameters').param('Positive scan direction').value()

    def getPlanesInCycle(self):
        return self.parTree.p.param('Acquisition parameters').param('Planes in cycle').value()
    def getTimepoints(self):
        return self.parTree.p.param('Acquisition parameters').param('Timepoints').value()
    def getReconstructionVxSize(self):
        return self.parTree.p.param('Reconstruction options').param('Reconstruction vx size').value()

    def getRestackBool(self):
        return self.parTree.p.param('Reconstruction options').param('Restack before deskewing').value()

    def getBleachCorrectionBool(self):
        return self.parTree.p.param('Reconstruction options').param('Bleaching correction').value()

    def getAverageTimepointsBool(self):
        return self.parTree.p.param('Reconstruction options').param('Average timepoints').value()
    def getAutoReconstructNewDataBool(self):
        return self.parTree.p.param('Autoreconstruct data from module').value()

    def closeEvent(self, event):
        self.sigClosing.emit()
        event.accept()


class ReconParTree(ParameterTree):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Parameter tree for the reconstruction
        params = [
            {'name': 'Pixel size', 'type': 'float', 'value': 116, 'suffix': 'nm'},
            {'name': 'CPU/GPU', 'type': 'list', 'values': ['GPU', 'CPU']},
            {'name': 'Acquisition parameters', 'type': 'group', 'children': [
                {'name': 'Delta-Y step size', 'type': 'float', 'value': 210, 'limits': (0, 9999)},
                {'name': 'Skew angle', 'type': 'float', 'value': 35, 'limits': (0, 9999)},
                {'name': 'Cycles', 'type': 'int', 'value': 10, 'limits': (0, 9999)},
                {'name': 'Planes in cycle', 'type': 'int', 'value': 20, 'limits': (0, 9999)},
                {'name': 'Positive scan direction', 'type': 'bool'},
                {'name': 'Timepoints', 'type': 'int', 'value': 1, 'limits': (0, 9999)}]},
            {'name': 'Reconstruction options', 'type': 'group', 'children': [
                {'name': 'Reconstruction vx size', 'type': 'float', 'value': 100, 'limits': (0, 9999),
                 'suffix': 'nm'},
                {'name': 'Bleaching correction', 'type': 'bool'},
                {'name': 'Restack before deskewing', 'type': 'bool'},
                {'name': 'Average timepoints', 'type': 'bool'}]},
            {'name': 'Autoreconstruct data from module', 'type': 'bool'}]

        self.p = Parameter.create(name='params', type='group', children=params)
        self.setParameters(self.p, showTop=False)
        self._writable = True


class BtnFrame(QtWidgets.QFrame):
    sigReconstuctCurrent = QtCore.Signal()
    sigReconstructMultiConsolidated = QtCore.Signal()
    sigReconstructMultiIndividual = QtCore.Signal()
    sigQuickLoadData = QtCore.Signal()
    sigUpdate = QtCore.Signal()

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.reconCurrBtn = BetterPushButton('Reconstruct current')
        self.reconCurrBtn.clicked.connect(self.sigReconstuctCurrent)
        self.quickLoadDataBtn = BetterPushButton('Quick load data')
        self.quickLoadDataBtn.clicked.connect(self.sigQuickLoadData)
        self.updateBtn = BetterPushButton('Update reconstruction')
        self.updateBtn.clicked.connect(self.sigUpdate)

        self.reconMultiBtn = QtWidgets.QToolButton()
        self.reconMultiBtn.setSizePolicy(
            QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Preferred)
        )
        self.reconMultiBtn.setText('Reconstruct multidata')
        self.reconMultiBtn.setPopupMode(QtWidgets.QToolButton.ToolButtonPopupMode.InstantPopup)
        self.reconMultiConsolidated = QtWidgets.QAction('Consolidate into a single reconstruction')
        self.reconMultiConsolidated.triggered.connect(self.sigReconstructMultiConsolidated)
        self.reconMultiBtn.addAction(self.reconMultiConsolidated)
        self.reconMultiIndividual = QtWidgets.QAction('Reconstruct data items individually')
        self.reconMultiIndividual.triggered.connect(self.sigReconstructMultiIndividual)
        self.reconMultiBtn.addAction(self.reconMultiIndividual)

        layout = QtWidgets.QGridLayout()
        self.setLayout(layout)

        layout.addWidget(self.quickLoadDataBtn, 0, 0, 1, 2)
        layout.addWidget(self.reconCurrBtn, 1, 0, 1, 2)
        layout.addWidget(self.reconMultiBtn, 2, 0, 1, 2)
        # layout.addWidget(self.updateBtn, 2, 0, 1, 2)


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
