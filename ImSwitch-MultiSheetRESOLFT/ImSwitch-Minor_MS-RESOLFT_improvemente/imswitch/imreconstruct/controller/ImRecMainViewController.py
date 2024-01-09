import copy
import os

import numpy as np
import tifffile as tiff

import imswitch.imreconstruct.view.guitools as guitools
from imswitch.imcommon.controller import PickDatasetsController
from imswitch.imreconstruct.model import DataObj, ReconObj, Reconstructor
from .DataFrameController import DataFrameController
from .MultiDataFrameController import MultiDataFrameController
from .ReconstructionViewController import ReconstructionViewController
from .ScanParamsController import ScanParamsController
from .basecontrollers import ImRecWidgetController


class ImRecMainViewController(ImRecWidgetController):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.dataFrameController = self._factory.createController(
            DataFrameController, self._widget.dataFrame
        )
        self.multiDataFrameController = self._factory.createController(
            MultiDataFrameController, self._widget.multiDataFrame
        )
        self.reconstructionController = self._factory.createController(
            ReconstructionViewController, self._widget.reconstructionWidget
        )
        self.pickDatasetsController = self._factory.createController(
            PickDatasetsController, self._widget.pickDatasetsDialog
        )

        self._reconstructor = Reconstructor()

        self._currentDataObj = None
        self._dataFolder = None
        self._saveFolder = None

        self._commChannel.sigDataFolderChanged.connect(self.dataFolderChanged)
        self._commChannel.sigSaveFolderChanged.connect(self.saveFolderChanged)
        self._commChannel.sigCurrentDataChanged.connect(self.currentDataChanged)
        self._commChannel.sigNewDataAddedFromModule.connect(self.newDataFromModule)

        self._widget.sigSaveReconstruction.connect(lambda: self.saveCurrent('reconstruction'))
        self._widget.sigSaveReconstructionAll.connect(lambda: self.saveAll('reconstruction'))
        self._widget.sigSaveCoeffs.connect(lambda: self.saveCurrent('coefficients'))
        self._widget.sigSaveCoeffsAll.connect(lambda: self.saveAll('coefficients'))
        self._widget.sigSetDataFolder.connect(self.setDataFolder)
        self._widget.sigSetSaveFolder.connect(self.setSaveFolder)

        self._widget.parTree.p.param('Acquisition parameters').sigTreeStateChanged.connect(self.acquisitionParsChanged)

        self._widget.sigReconstuctCurrent.connect(self.reconstructCurrent)
        self._widget.sigReconstructMultiConsolidated.connect(
            lambda: self.reconstructMulti(consolidate=True)
        )
        self._widget.sigReconstructMultiIndividual.connect(
            lambda: self.reconstructMulti(consolidate=False)
        )
        self._widget.sigQuickLoadData.connect(self.quickLoadData)
        self._widget.sigUpdate.connect(lambda: self.updateScanParams(applyOnCurrentRecon=True))

        self.acquisitionParsChanged()
    def acquisitionParsChanged(self):
        cycles = self._widget.getCycles()
        planes_in_cycle = self._widget.getPlanesInCycle()
        self._commChannel.sigDataStackingChanged.emit(cycles, planes_in_cycle)
    def dataFolderChanged(self, dataFolder):
        self._dataFolder = dataFolder

    def saveFolderChanged(self, saveFolder):
        self._saveFolder = saveFolder

    def setDataFolder(self):
        dataFolder = guitools.askForFolderPath(self._widget)
        if dataFolder:
            self._commChannel.sigDataFolderChanged.emit(dataFolder)

    def setSaveFolder(self):
        saveFolder = guitools.askForFolderPath(self._widget)
        if saveFolder:
            self._commChannel.sigSaveFolderChanged.emit(saveFolder)

    def quickLoadData(self):
        dataPath = guitools.askForFilePath(self._widget, defaultFolder=self._dataFolder)
        if dataPath:
            self._logger.debug(f'Loading data at: {dataPath}')

            datasetsInFile = DataObj.getDatasetNames(dataPath)
            datasetToLoad = None
            if len(datasetsInFile) < 1:
                # File does not contain any datasets
                return
            elif len(datasetsInFile) > 1:
                # File contains multiple datasets
                self.pickDatasetsController.setDatasets(dataPath, datasetsInFile)
                if not self._widget.showPickDatasetsDialog(blocking=True):
                    return

                datasetsSelected = self.pickDatasetsController.getSelectedDatasets()
                if len(datasetsSelected) < 1:
                    # No datasets selected
                    return
                elif len(datasetsSelected) == 1:
                    datasetToLoad = datasetsSelected[0]
                else:
                    # Load into multi-data list
                    for datasetName in datasetsSelected:
                        self._commChannel.sigAddToMultiData.emit(dataPath, datasetName)
                    self._widget.raiseMultiDataDock()
                    return

            name = os.path.split(dataPath)[1]
            if self._currentDataObj is not None:
                self._currentDataObj.checkAndUnloadData()
            self._currentDataObj = DataObj(name, datasetToLoad, path=dataPath)
            self._currentDataObj.checkAndLoadData()
            if self._currentDataObj.dataLoaded:
                self._commChannel.sigCurrentDataChanged.emit(self._currentDataObj)
                self._logger.debug('Data loaded')
                self._widget.raiseCurrentDataDock()
            else:
                pass

    def newDataFromModule(self):
        if self._widget.getAutoReconstructNewDataBool():
            self.reconstructCurrent()

    def currentDataChanged(self, dataObj):
        self._currentDataObj = dataObj
        """Could be used in future to set recon parameters from dataAttr"""
        # Update scan params based on new data
        # TODO: What if the attribute names change in imcontrol?
        # try:
        #     stepSizesAttr = dataObj.attrs['ScanStage:axis_step_size']
        # except KeyError:
        #     pass
        # else:
        #     for i in range(0, min(4, len(stepSizesAttr))):
        #         self._scanParDict['step_sizes'][i] = str(stepSizesAttr[i] * 1000)  # convert um->nm
        #
        # self.updateScanParams()

    def reconstructCurrent(self):
        if self._currentDataObj is None:
            return

        self.reconstruct([self._currentDataObj], consolidate=False)

    def reconstructMulti(self, consolidate):
        self.reconstruct(self._widget.getMultiDatas(), consolidate)

    def reconstruct(self, dataObjs, consolidate):
        #consolidate not fully implemented now
        reconObj = None
        for index, dataObj in enumerate(dataObjs):
            preloaded = dataObj.dataLoaded
            try:
                dataObj.checkAndLoadData()

                if not consolidate or index == 0:
                    reconObj = ReconObj(dataObj.name,
                                        self._widget.timepoints_text)

                data = dataObj.data
                if self._widget.getBleachCorrectionBool():
                    data = self.bleachingCorrection(data)

                timepoints = self._widget.getTimepoints()
                if timepoints > 1 and self._widget.getAverageTimepointsBool():
                    shape = data.shape
                    reshaped = np.reshape(data, (timepoints, shape[0]//timepoints, shape[1], shape[2]))
                    data = np.mean(reshaped, axis=0)
                    timepoints = 1

                cycles = self._widget.getCycles()
                planes_in_cycle = self._widget.getPlanesInCycle()
                dataShape_tp = np.array([cycles*planes_in_cycle, data.shape[1], data.shape[2]])
                reconstructionSize = self._reconstructor.getReconstructionSize(dataShape_tp, self._widget.getPixelSizeNm(),
                                                                             self._widget.getSkewAngleRad(),
                                                                             self._widget.getDeltaY(),
                                                                             self._widget.getReconstructionVxSize())

                reconObj.allocateReconstruction(timepoints, reconstructionSize)

                for tp in range(timepoints):
                    """Restack data"""
                    slices = cycles * planes_in_cycle
                    tp_data = data[tp*slices:(tp + 1)*slices]
                    if self._widget.getRestackBool():
                        try:
                            restacked = np.zeros_like(tp_data)
                            for i in range(planes_in_cycle):
                                restacked[i * cycles:(i + 1) * cycles] = tp_data[i::planes_in_cycle]
                        except ValueError:
                            self._logger.warning('Data shape does not match given restacking parameters')
                    else:
                        restacked = tp_data
                    if self._widget.getPosScanDirection():
                        restacked = np.flip(restacked, 0)
                    self._logger.debug('Reconstructing data tp: %s' % tp)
                    recon = self._reconstructor.simpleDeskew(restacked, self._widget.getPixelSizeNm(),
                                                             self._widget.getSkewAngleRad(),
                                                             self._widget.getDeltaY(),
                                                             self._widget.getReconstructionVxSize())
                    reconObj.addReconstructionTimepoint(tp, recon)

            finally:
                if not preloaded:
                    dataObj.checkAndUnloadData()

            if not consolidate:
                self._widget.addNewReconstruction(reconObj, reconObj.name)

        if consolidate:
            self._widget.addNewReconstruction(reconObj, f'{reconObj.name}_multi')

    def bleachingCorrection(self, data):
        correctedData = data.copy()
        energy = np.sum(data, axis=(1, 2))
        for i in range(data.shape[0]):
            c = (energy[0] / energy[i]) ** 4
            correctedData[i, :, :] = data[i, :, :] * c
        return correctedData

    def saveCurrent(self, dataType):
        """ Saves the reconstructed image or coefficeints from the current
        ReconObj to a user-specified destination. """

        filePath = guitools.askForFilePath(self._widget,
                                           caption=f'Save {dataType}',
                                           defaultFolder=self._saveFolder or self._dataFolder,
                                           nameFilter='*.tiff', isSaving=True)

        if filePath:
            reconObj = self.reconstructionController.getActiveReconObj()
            if dataType == 'reconstruction':
                self.saveReconstruction(reconObj, filePath)
            elif dataType == 'coefficients':
                self.saveCoefficients(reconObj, filePath)
            else:
                raise ValueError(f'Invalid save data type "{dataType}"')

    def saveAll(self, dataType):
        """ Saves the reconstructed image or coefficeints from all available
        ReconObj objects to a user-specified directory. """

        dirPath = guitools.askForFolderPath(self._widget,
                                            caption=f'Save all {dataType}',
                                            defaultFolder=self._saveFolder or self._dataFolder)

        if dirPath:
            for name, reconObj in self.reconstructionController.getAllReconObjs():
                # Avoid overwriting
                filePath = os.path.join(dirPath, f'{name}.{dataType}.tiff')
                filePathNew = filePath
                numExisting = 0
                while os.path.exists(filePathNew):
                    numExisting += 1
                    pathWithoutExt, pathExt = os.path.splitext(filePath)
                    filePathNew = f'{pathWithoutExt}_{numExisting}{pathExt}'
                filePath = filePathNew

                # Save
                if dataType == 'reconstruction':
                    self.saveReconstruction(reconObj, filePath)
                elif dataType == 'coefficients':
                    self.saveCoefficients(reconObj, filePath)
                else:
                    raise ValueError(f'Invalid save data type "{dataType}"')

    def saveReconstruction(self, reconObj, filePath):
        # scanParDict = reconObj.getScanParams()
        # vxsizec = int(float(
        #     scanParDict['step_sizes'][scanParDict['dimensions'].index(
        #         self._widget.r_l_text
        #     )]
        # ))
        # vxsizer = int(float(
        #     scanParDict['step_sizes'][scanParDict['dimensions'].index(
        #         self._widget.u_d_text
        #     )]
        # ))
        # vxsizez = int(float(
        #     reconObj.scanParDict['step_sizes'][scanParDict['dimensions'].index(
        #         self._widget.b_f_text
        #     )]
        # ))
        # dt = int(float(
        #     scanParDict['step_sizes'][scanParDict['dimensions'].index(
        #         self._widget.timepoints_text
        #     )]
        # ))

        self._logger.debug(f'Trying to save to: {filePath}, Vx size: {self._widget.getReconstructionVxSize(), self._widget.getReconstructionVxSize(), self._widget.getReconstructionVxSize()},'
                           f' dt: -')
        # Reconstructed image
        reconstrData = reconObj.getReconstruction() #Not good for memory limitations
        reconstrData = np.array([reconstrData])
        reconstrData = np.swapaxes(reconstrData, 1, 2)
        tiff.imwrite(filePath, reconstrData,
                     imagej=True, resolution=(1 / self._widget.getReconstructionVxSize(), 1 / self._widget.getReconstructionVxSize()),
                     metadata={'spacing': self._widget.getReconstructionVxSize(), 'unit': 'nm', 'axes': 'TZCYX'})
        """Reshape back to original, since we do not deep copy from reconObj"""
        reconstrData = np.swapaxes(reconstrData, 1, 2)
        reconstrData = reconstrData[0]
    def saveCoefficients(self, reconObj, filePath):
        coeffs = copy.deepcopy(reconObj.getCoeffs())
        self._logger.debug(f'Shape of coeffs: {coeffs.shape}')
        coeffs = np.swapaxes(coeffs, 1, 2)
        tiff.imwrite(filePath, coeffs,
                     imagej=True, resolution=(1, 1),
                     metadata={'spacing': 1, 'unit': 'px', 'axes': 'TZCYX'})


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
