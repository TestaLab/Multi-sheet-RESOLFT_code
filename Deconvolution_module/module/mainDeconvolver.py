import os
import time
import numpy as np
import numba
from numba import cuda
import cupy as cp
from module.kernelGeneration import KernelHandler
from module.transformMatGeneration import TransformMatHandler
from module.gpuTransforms import convTransform, invConvTransform
from module.dataFiddler import DataFiddler
from module.DataIO_tools import DataIO_tools
import json

class Deconvolver:

    def __init__(self):

        self.DF = DataFiddler()
        self.KH = KernelHandler()
        self.tMatHandler = TransformMatHandler()

        self.mempool = cp.get_default_memory_pool()

    def setAndLoadData(self, path, dataPropertiesDict):
        self.DF.loadData(path, dataPropertiesDict)

    def Deconvolve(self, imFormationModelParameters, algOptionsDict, saveOptions):

        """Unpack options"""
        saveToDisc = saveOptions['Save to disc']
        if saveToDisc:
            try:
                saveMode = saveOptions['Save mode']
                if saveMode == 'Progression':
                    try:
                        progressionMode = saveOptions['Progression mode']
                    except KeyError:
                        print('Progression mode missing')
            except KeyError:
                print('Save mode missing')
            try:
                saveFolder = saveOptions['Save folder']
                saveName = saveOptions['Save name']
            except KeyError:
                print('Save folder and/or name missing')
        else:
            saveMode = None
            progressionMode = None

        iterations = algOptionsDict['Iterations']

        K = self.KH.makePLSRKernel(self.DF.getDataPropertiesDict(), imFormationModelParameters, algOptionsDict)
        M = self.tMatHandler.makeSOLSTransformMatrix(self.DF.getDataPropertiesDict(), algOptionsDict)

        dataShape = self.DF.getDataTimepointShape()
        reconShape = np.ceil(np.matmul(M, dataShape)).astype(int)
        """Prepare GPU blocks"""
        threadsperblock = 8
        blocks_per_grid_z = (dataShape[0] + (threadsperblock - 1)) // threadsperblock
        blocks_per_grid_y = (dataShape[1] + (threadsperblock - 1)) // threadsperblock
        blocks_per_grid_x = (dataShape[2] + (threadsperblock - 1)) // threadsperblock

        """Prepare arrays"""
        dev_dataOnes = cp.ones(dataShape, dtype=float)
        dev_Ht_of_ones = cp.zeros(reconShape, dtype=float)
        dev_K = cp.array(K)
        dev_M = cp.array(M)
        invConvTransform[
            (blocks_per_grid_z, blocks_per_grid_y, blocks_per_grid_x), (
                threadsperblock, threadsperblock, threadsperblock)](
            dev_dataOnes, dev_Ht_of_ones, dev_K, dev_M)
        del dev_dataOnes
        dev_Ht_of_ones = dev_Ht_of_ones.clip(
            0.3 * cp.max(dev_Ht_of_ones))  # Avoid divide by zero and crazy high guesses outside measured region, 0.3 is emperically chosen
        self.mempool.free_all_blocks()
        dev_dataCanvas = cp.zeros(dataShape, dtype=float)
        dev_sampleCanvas = cp.zeros(reconShape, dtype=float)

        """Prepare saving"""
        if saveMode == 'Progression':
            saveRecons = []
            if progressionMode == 'Logarithmic':
                indices = (iterations - np.arange(0, np.floor(np.log2(iterations)))**2)[::-1]

        for tp in range(self.DF.getNrOfTimepoints()):
            data = self.DF.getPreprocessedData(timepoint=tp) #timepoint is zero-indexed
            assert self.checkData(data), "Something wrong with data"
            dev_data = cp.array(data)
            dev_currentReconstruction = cp.ones(reconShape, dtype=float)
            for i in range(iterations):
                print('Timepoint: ', tp, ', Iteration: ', i)
                """Zero arrays"""
                print('Made arrays')
                t1 = time.time()
                convTransform[
                    (blocks_per_grid_z, blocks_per_grid_y, blocks_per_grid_x), (
                    threadsperblock, threadsperblock, threadsperblock)](
                    dev_dataCanvas, dev_currentReconstruction, dev_K, dev_M)
                cuda.synchronize()
                t2 = time.time()
                elapsed = t2-t1
                print('Calculated dfg, elapsed = ', elapsed)
                cp.divide(dev_data, dev_dataCanvas, dev_dataCanvas) #dataCanvas now stores the error
                print('Calculated error')
                t1 = time.time()
                invConvTransform[
                    (blocks_per_grid_z, blocks_per_grid_y, blocks_per_grid_x), (
                    threadsperblock, threadsperblock, threadsperblock)](
                    dev_dataCanvas, dev_sampleCanvas, dev_K, dev_M) #Sample canvas now stores the distributed error
                cuda.synchronize()
                t2 = time.time()
                elapsed = t2-t1
                print('Distributed error, elapsed = ', elapsed)
                cp.divide(dev_sampleCanvas, dev_Ht_of_ones, out=dev_sampleCanvas) #Sample canvas now stores the "correction factor"
                cp.multiply(dev_currentReconstruction, dev_sampleCanvas, out=dev_currentReconstruction)
                if saveMode == 'Progression' and (progressionMode == 'All' or i in indices):
                    saveRecons.append(cp.asnumpy(dev_currentReconstruction))

            finalReconstruction = cp.asnumpy(dev_currentReconstruction)

            if saveToDisc:
                if saveMode == 'Final':
                    saveDataPath = os.path.join(saveFolder, saveName + '_Timepoint_' + str(tp) + '_FinalDeconvolved.tif')
                    DataIO_tools.save_data(finalReconstruction, saveDataPath)
                elif saveMode == 'Progression':
                    saveRecons = np.asarray(saveRecons)
                    saveDataPath = os.path.join(saveFolder, saveName + '_DeconvolutionProgression.tif')
                    DataIO_tools.save_data(saveRecons, saveDataPath)
                saveParamsPath = os.path.join(saveFolder, saveName + '_DeconvolutionParameters.json')
                saveParamDict = {'Data Parameters': dataPropertiesDict,
                                 'Image formation model parameters': imFormationModelParameters,
                                 'Algorithmic parameters': algOptionsDict}
                with open(saveParamsPath, 'w') as fp:
                    json.dump(saveParamDict, fp, indent=4)
                    fp.close()

        del dev_currentReconstruction
        del dev_dataCanvas
        del dev_sampleCanvas
        self.mempool.free_all_blocks()

        return finalReconstruction

    def checkData(self, data):
        #ToDo: Insert relevent checks here
        if np.min(data) < 0:
            return False
        else:
            return True

def fuseTimePoints(folderPath, fileNamePart1, nrArray, fileNamePart2, averageTimepoints=False):
    fullPath = os.path.join(folderPath, fileNamePart1 + str(nrArray[0]) + fileNamePart2)
    print('Loading path: ', fullPath)
    dataTimePoint = DataIO_tools.load_data(fullPath)
    fullShape = [len(nrArray), dataTimePoint.shape[0], dataTimePoint.shape[1], dataTimePoint.shape[2]]
    allDataTimePoints = np.zeros(fullShape)
    allDataTimePoints[0] = dataTimePoint
    for i in nrArray[1:]:
        fullPath = os.path.join(folderPath, fileNamePart1 + str(nrArray[i]) + fileNamePart2)
        print('Loading path: ', fullPath)
        allDataTimePoints[i] = DataIO_tools.load_data(fullPath)
    if averageTimepoints:
        savePath = os.path.join(folderPath, fileNamePart1 + fileNamePart2.split('.')[0] + '_AveragedTimeLapse.tif')
        DataIO_tools.save_data(np.mean(allDataTimePoints, axis=0), savePath)
    else:
        savePath = os.path.join(folderPath, fileNamePart1 + fileNamePart2.split('.')[0] + '_FusedTimeLapse.tif')
        DataIO_tools.save_data(allDataTimePoints, savePath)





dataPropertiesDict = {'Camera pixel size [nm]': 95.7,
                      'Camera offset': 100,
                      'Scan step size [nm]': 210,
                      'Tilt angle [deg]': 35,
                      'Scan axis': 0,
                      'Tilt axis': 2,
                      'Data stacking': 'PLSR Interleaved',
                      'Planes in cycle': 5,
                      'Cycles': 10,
                      'Pos/Neg scan direction': 'Neg',
                      'Correct first cycle': True,
                      'Correct pixel offsets': False,
                      'Skew correction pixel per cycle': 0}

algOptionsDict = {'Reconstruction voxel size [nm]': 40,
                  'Clip factor for kernel cropping': 0.01,
                  'Iterations': 15}

reconPxSize = str(algOptionsDict['Reconstruction voxel size [nm]'])
psfPath = os.path.join(r'PSFs', reconPxSize + 'nm', 'PSF_RW_1.26_' + reconPxSize + 'nmPx_101x101x101.tif')

imFormationModelParameters = {'Optical PSF path': psfPath,
                              'Confined sheet FWHM [nm]': 300,
                              'Read-out sheet FWHM [nm]': 1200,
                              'Background sheet ratio': 1}

saveOptions = {'Save to disc': True,
               'Save mode': 'Final',
               'Progression mode': 'All',
               'Save folder': r'A:\GitHub\ImSim\Saved_data\PLSR_data_160123',
               'Save name': 'Mixed_Sampple_PLSR_rsEGFP2'}

import matplotlib.pyplot as plt

deconvolver = Deconvolver()
deconvolver.setAndLoadData(r'A:\GitHub\ImSim\Saved_data\PLSR_data_160123\Mixed_Sampple_PLSR_rsEGFP2.tif', dataPropertiesDict)
deconvolved = deconvolver.Deconvolve(imFormationModelParameters, algOptionsDict, saveOptions)

# import napari
# viewer = napari.Viewer()
# new_layer = viewer.add_image(deconvolved, rgb=True)