import os
import time

import cupy
import numpy as np
import numba
from numba import cuda
from numba.cuda.random import xoroshiro128p_uniform_float32, create_xoroshiro128p_states
import cupy as cp
from model.kernelGeneration import KernelHandler
from model.transformMatGeneration import TransformMatHandler
from model.gpuTransforms import gaussDistribTransform, convTransform, invConvTransform
from model.dataFiddler import DataFiddler
from model.DataIO_tools import DataIO_tools
import json
import math
import copy
import time
class Deconvolver:

    def __init__(self):

        self.DF = DataFiddler()
        self.KH = KernelHandler()
        self.tMatHandler = TransformMatHandler()

        self.mempool = cp.get_default_memory_pool()

    def setAndLoadData(self, path, dataPropertiesDict):
        self.DF.loadData(path, dataPropertiesDict)

    def setDataPropertiesDict(self, dataPropertiesDict):
        self.DF.setDataPropertiesDict(dataPropertiesDict)

    def simpleDeskew(self, algOptionsDict, reconOptionsDict, saveOptions):
        """Deskew the data in one step transform"""

        startTime = time.time()
        saveToDisc = saveOptions['Save to disc']
        if saveToDisc:
            try:
                saveFolder = saveOptions['Save folder']
                saveName = saveOptions['Save name']
            except KeyError:
                print('Save folder and/or name missing')
        else:
            saveMode = None

        M = self.tMatHandler.makeSOLSTransformMatrix(self.DF.getDataPropertiesDict(), algOptionsDict, reconOptionsDict)
        cpM = cuda.to_device(M)
        """Calculate reconstruction canvas size"""
        print('Timepoint shape = ', self.DF.getDataTimepointShape())
        dataShape = self.DF.getDataTimepointShape()
        reconShape = np.ceil(np.matmul(M, dataShape)).astype(int)
        """Prepare GPU blocks for shape of data"""
        threadsperblock = 8
        data_blocks_per_grid_z = (dataShape[0] + (threadsperblock - 1)) // threadsperblock
        data_blocks_per_grid_y = (dataShape[1] + (threadsperblock - 1)) // threadsperblock
        data_blocks_per_grid_x = (dataShape[2] + (threadsperblock - 1)) // threadsperblock

        sigma_z, sigma_y, sigma_x = self.KH.makeGaussianSigmas(self.DF.getDataPropertiesDict(), reconOptionsDict)

        """Reconstruct"""
        print('Before allocating')
        dataOnes = cp.ones(dataShape)
        invTransfOnes = cp.zeros(reconShape)
        print('After allocating')
        gaussDistribTransform[(data_blocks_per_grid_z, data_blocks_per_grid_y, data_blocks_per_grid_x),
                              (threadsperblock, threadsperblock, threadsperblock)](dataOnes, invTransfOnes, cpM,
                                                                                   sigma_z, sigma_y, sigma_x,
                                                                                   int(np.ceil(sigma_z)),
                                                                                   int(np.ceil(sigma_y)),
                                                                                   int(np.ceil(sigma_x)))
        print('After transform')
        del dataOnes

        invTransfOnes = invTransfOnes.clip(0.01)
        """Prepare how to process timepoints"""
        timepoints = self._getTimepointsList(reconOptionsDict)
        print('Timepoints = ', timepoints)
        for tp in timepoints:
            adjustedData = cp.array(self.DF.getPreprocessedData(reconOptionsDict, timepoints=tp))
            recon_canvas = cp.zeros(reconShape, dtype=float)
            gaussDistribTransform[(data_blocks_per_grid_z, data_blocks_per_grid_y, data_blocks_per_grid_x),
                                  (threadsperblock, threadsperblock, threadsperblock)](adjustedData, recon_canvas, M,
                                                                                       sigma_z, sigma_y, sigma_x,
                                                                                   int(np.ceil(sigma_z)),
                                                                                   int(np.ceil(sigma_y)),
                                                                                   int(np.ceil(sigma_x)))
            finalReconstruction = cp.asnumpy(cp.divide(recon_canvas, invTransfOnes))
            print('Reconstruction finished at t = ', time.time() - startTime)
            if saveToDisc:
                vx_size = (reconOptionsDict['Reconstruction voxel size [nm]'],) * 3
                saveDataPath = os.path.join(saveFolder, saveName + '_Timepoint_' + str(tp) + '_SimpleDeskew.tif')
                DataIO_tools.save_data(finalReconstruction, saveDataPath, vx_size=vx_size, unit='nm')
                saveParamsPath = os.path.join(saveFolder, saveName + '_ReconstructionParameters.json')
                saveParamDict = {'Data Parameters': dataPropertiesDict,
                                 'Reconstruction parameters': reconOptionsDict,
                                 'Image formation model parameters': imFormationModelParameters,
                                 'Algorithmic parameters': algOptionsDict}
                with open(saveParamsPath, 'w') as fp:
                    json.dump(saveParamDict, fp, indent=4)
                    fp.close()

        del adjustedData
        del recon_canvas
        del invTransfOnes
        self.mempool.free_all_blocks()


    def Deconvolve(self, reconOptionsDict, algOptionsDict, imFormationModelParameters, saveOptions):
        startTime = time.time()
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
        try:
            gradientConsent = algOptionsDict['Gradient consent']
        except KeyError:
            gradientConsent = False

        K = self.KH.makePLSRKernel(self.DF.getDataPropertiesDict(), imFormationModelParameters, algOptionsDict,
                                   reconOptionsDict)
        M = self.tMatHandler.makeSOLSTransformMatrix(self.DF.getDataPropertiesDict(), algOptionsDict, reconOptionsDict)

        dataShape = self.DF.getDataTimepointShape()
        reconShape = np.ceil(np.matmul(M, dataShape)).astype(int)
        """Prepare GPU blocks for shape of data"""
        threadsperblock = 8
        data_blocks_per_grid_z = (dataShape[0] + (threadsperblock - 1)) // threadsperblock
        data_blocks_per_grid_y = (dataShape[1] + (threadsperblock - 1)) // threadsperblock
        data_blocks_per_grid_x = (dataShape[2] + (threadsperblock - 1)) // threadsperblock

        """Prepare arrays"""
        dev_dataOnes = cp.ones(dataShape, dtype=float)
        dev_Ht_of_ones = cp.zeros(reconShape, dtype=float)
        dev_K = cp.array(K)
        dev_M = cp.array(M)
        invConvTransform[
            (data_blocks_per_grid_z, data_blocks_per_grid_y, data_blocks_per_grid_x), (
                threadsperblock, threadsperblock, threadsperblock)](
            dev_dataOnes, dev_Ht_of_ones, dev_K, dev_M)
        del dev_dataOnes
        dev_Ht_of_ones = dev_Ht_of_ones.clip(
            0.3 * cp.max(dev_Ht_of_ones))  # Avoid divide by zero and crazy high guesses outside measured region, 0.3 is emperically chosen
        self.mempool.free_all_blocks()
        dev_dataCanvas = cp.zeros(dataShape, dtype=float)
        dev_sampleCanvas = cp.zeros(reconShape, dtype=float)
        if gradientConsent:
            dev_dataCanvas2 = cp.zeros(dataShape, dtype=float)
            dev_sampleCanvas2 = cp.zeros(reconShape, dtype=float)

        """Prepare GPU blocks for shape of samples guess"""
        sample_blocks_per_grid_z = (reconShape[0] + (threadsperblock - 1)) // threadsperblock
        sample_blocks_per_grid_y = (reconShape[1] + (threadsperblock - 1)) // threadsperblock
        sample_blocks_per_grid_x = (reconShape[2] + (threadsperblock - 1)) // threadsperblock

        """Prepare saving"""
        if saveMode == 'Progression':
            saveRecons = []
            if progressionMode == 'Logarithmic':
                indices = (iterations - np.arange(0, np.floor(np.log2(iterations)))**2)[::-1]

        """Prepare how to process timepoints"""
        timepoints = self._getTimepointsList(reconOptionsDict)

        """Run deconvolution iteration"""
        for tp in timepoints:
            data = self.DF.getPreprocessedData(reconOptionsDict, timepoints=tp) #timepoint is zero-indexed
            assert self._checkData(data), "Something wrong with data"

            dev_data = cp.array(data)
            if gradientConsent:
                dev_dataBin1 = cp.zeros_like(dev_data)
                dev_dataBin2 = cp.zeros_like(dev_data)
            dev_currentReconstruction = cp.ones(reconShape, dtype=float)
            for i in range(iterations):
                print('Timepoint: ', tp, ', Iteration: ', i)
                """Zero arrays"""
                print('Made arrays')
                t1 = time.time()
                convTransform[
                    (data_blocks_per_grid_z, data_blocks_per_grid_y, data_blocks_per_grid_x), (
                        threadsperblock, threadsperblock, threadsperblock)](
                    dev_dataCanvas, dev_currentReconstruction, dev_K, dev_M)
                cuda.synchronize()
                t2 = time.time()
                elapsed = t2-t1
                print('Calculated dfg, elapsed = ', elapsed)

                if gradientConsent:
                    dev_dataBin1 = cp.zeros_like(dev_data)
                    dev_dataBin2 = cp.zeros_like(dev_data)
                    rng_states = create_xoroshiro128p_states(
                        threadsperblock**3 * data_blocks_per_grid_z * data_blocks_per_grid_y * data_blocks_per_grid_x, seed=i+tp*iterations)
                    gpuBinomialSplit[
                        (data_blocks_per_grid_z, data_blocks_per_grid_y, data_blocks_per_grid_x), (
                            threadsperblock, threadsperblock, threadsperblock)](dev_data, dev_dataBin1, dev_dataBin2, 0.5, rng_states)
                    cp.divide(dev_dataCanvas, 2, dev_dataCanvas) #since data is devided into two bins
                    cp.divide(dev_dataBin2, dev_dataCanvas, dev_dataCanvas2)
                    cp.divide(dev_dataBin1, dev_dataCanvas, dev_dataCanvas) #dataCanvas now stores the error

                    print('Calculated error in gradient consent')
                    invConvTransform[
                        (data_blocks_per_grid_z, data_blocks_per_grid_y, data_blocks_per_grid_x), (
                            threadsperblock, threadsperblock, threadsperblock)](
                        dev_dataCanvas, dev_sampleCanvas, dev_K, dev_M)  # Sample canvas now stores the 1st distributed error
                    cuda.synchronize()
                    cp.divide(dev_sampleCanvas, dev_Ht_of_ones,
                              out=dev_sampleCanvas)  # Sample canvas now stores the 1st "correction factor"
                    invConvTransform[
                        (data_blocks_per_grid_z, data_blocks_per_grid_y, data_blocks_per_grid_x), (
                            threadsperblock, threadsperblock, threadsperblock)](
                        dev_dataCanvas2, dev_sampleCanvas2, dev_K, dev_M)  # Sample canvas now stores the 2nd distributed error
                    cp.divide(dev_sampleCanvas2, dev_Ht_of_ones,
                              out=dev_sampleCanvas2)  # Sample canvas now stores the 2nd "correction factor"
                    cuda.synchronize()
                    if i == 99:
                        DataIO_tools.save_data(cp.asnumpy(dev_sampleCanvas), 'Sample_Canvas.tif')
                        DataIO_tools.save_data(cp.asnumpy(dev_sampleCanvas2), 'Sample_Canvas2.tif')
                    """Check for which voxels the update factors agree. If they agree, take the mean, else take 1."""
                    gpuDoGradientConsent[
                        (sample_blocks_per_grid_z, sample_blocks_per_grid_y, sample_blocks_per_grid_x), (
                            threadsperblock, threadsperblock, threadsperblock)](dev_sampleCanvas, dev_sampleCanvas2)
                    cuda.synchronize()
                    if i == 15:
                        DataIO_tools.save_data(cp.asnumpy(dev_sampleCanvas), 'Sample_Canvas_after.tif')
                else:
                    cp.divide(dev_data, dev_dataCanvas, dev_dataCanvas) #dataCanvas now stores the error
                    print('Calculated error')
                    t1 = time.time()
                    invConvTransform[
                        (data_blocks_per_grid_z, data_blocks_per_grid_y, data_blocks_per_grid_x), (
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
            print('Deconvolution finished at t = ', time.time() - startTime)
            if saveToDisc:
                vx_size = (reconOptionsDict['Reconstruction voxel size [nm]'],)*3
                if saveMode == 'Final':
                    saveDataPath = os.path.join(saveFolder, saveName + '_Timepoint_' + str(tp) + '_FinalDeconvolved.tif')
                    DataIO_tools.save_data(finalReconstruction, saveDataPath, vx_size=vx_size, unit='nm')
                elif saveMode == 'Progression':
                    saveRecons = np.asarray(saveRecons)
                    saveDataPath = os.path.join(saveFolder, saveName + '_DeconvolutionProgression.tif')
                    DataIO_tools.save_data(saveRecons, saveDataPath, vx_size=vx_size, unit='nm')
                saveParamsPath = os.path.join(saveFolder, saveName + '_DeconvolutionParameters.json')
                saveParamDict = {'Data Parameters': dataPropertiesDict,
                                 'Reconstruction parameters': reconOptionsDict,
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

    def _checkData(self, data):
        #ToDo: Insert relevent checks here
        if np.min(data) < 0:
            return False
        else:
            return True

    def _getTimepointsList(self, reconOptionsDict):

        timepoints = reconOptionsDict['Process timepoints']
        if timepoints == 'All':
            timepoints = np.arange(self.DF.getNrOfTimepoints(), dtype=int)
            print('Processing all timepoints in data, which is: ', timepoints)
        elif isinstance(timepoints, (np.ndarray, list, tuple)):
            assert np.all([i == int(i) for i in timepoints]), 'Timepoints needs to be given as integers'
            timepoints = np.array(timepoints, dtype='int32')
            print('Processing the following timepoints in data: ', timepoints)
        else:
            print('Unknown format of timpoints to process, should be "All" or array specifying timepoints')

        if reconOptionsDict['Average timepoints']:
            timepoints = [timepoints]

        return timepoints

@cuda.jit
def gpuBinomialSplit(rawData, bin1Data, bin2Data, p, rng_states):
    idz, idy, idx = cuda.grid(3)
    if idz < rawData.shape[0] and idy < rawData.shape[1] and idx < rawData.shape[2]:
        n = idz*cuda.gridsize(3)[1]*cuda.gridsize(3)[2] + idy*cuda.gridsize(3)[2] + idx
        for _ in range(rawData[idz, idy, idx]):
            r = xoroshiro128p_uniform_float32(rng_states, n)
            if r < p:
                bin1Data[idz, idy, idx] += 1
            else:
                bin2Data[idz, idy, idx] += 1

@cuda.jit
def gpuDoGradientConsent(updateFactors1, updateFactors2):
    idz, idy, idx = cuda.grid(3)
    if idz < updateFactors1.shape[0] and idy < updateFactors1.shape[1] and idx < updateFactors1.shape[2]:
        uf1 = updateFactors1[idz, idy, idx]
        uf2 = updateFactors2[idz, idy, idx]
        s1 = uf1 - 1
        s2 = uf2 - 1
        if s1 / abs(s1) == s2 / abs(s2):
            updateFactors1[idz, idy, idx] = 0.5*(uf1 + uf2)
        else:
            updateFactors1[idz, idy, idx] = 1


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





dataPropertiesDict = {'Camera pixel size [nm]': 116,
                      'Camera offset': 100,
                      'Scan step size [nm]': 105, #105 or 210
                      'Tilt angle [deg]': 35,
                      'Scan axis': 0,
                      'Tilt axis': 2,
                      'Data stacking': 'PLSR Interleaved',
                      'Planes in cycle': 30, # 30 planes for 60 um and 20 planes for 40 um
                      'Cycles': 20, #if 105 nm step size -> 20 cycles, 210 nm -> 10 cycles
                      'Timepoints': 3,
                      'Pos/Neg scan direction': 'Pos'} #Neg in most simulations, Pos in real data

reconOptionsDict = {'Reconstruction voxel size [nm]': 100,
                    'Correct first cycle': True,
                    'Correct pixel offsets': False,
                    'Skew correction pixel per cycle': 0,#~-0.3 used for skewed stage scan
                    'Process timepoints': 'All',
                    'Average timepoints': True}

algOptionsDict = {'Gradient consent': False,
                  'Clip factor for kernel cropping': 0.01,
                  'Iterations': 10}

reconPxSize = str(reconOptionsDict['Reconstruction voxel size [nm]'])
detNA = 1.1#1.1 or 1.26 available now
psfPath = os.path.join(r'PSFs', str(detNA)+'NA', reconPxSize + 'nm', 'PSF_RW_'+str(detNA)+'_' + reconPxSize + 'nmPx_101x101x101.tif')

imFormationModelParameters = {'Optical PSF path': psfPath,
                              'Detection NA': detNA,
                              'Confined sheet FWHM [nm]': 200,
                              'Read-out sheet FWHM [nm]': 1200,
                              'Background sheet ratio': 0.1}

saveOptions = {'Save to disc': True,
               'Save mode': 'Final',
               'Progression mode': 'All',
               'Save folder': r'D:\SnoutyData\2023-07-14',
               'Save name': 'After_fixation_Attempt2_PLSR_3rdSynapse_Car-T+Target_NB-N205S_rec_Orca'}

import matplotlib.pyplot as plt

deconvolver = Deconvolver()
deconvolver.setAndLoadData(r'D:\SnoutyData\2023-07-14\After_fixation_Attempt2_PLSR_3rdSynapse_Car-T+Target_NB-N205S_rec_Orca.hdf5', dataPropertiesDict)

# deconvolved = deconvolver.Deconvolve(reconOptionsDict, algOptionsDict, imFormationModelParameters, saveOptions)
# deconvolver.simpleDeskew(algOptionsDict, reconOptionsDict, saveOptions)

# import napari
# viewer = napari.Viewer()
# new_layer = viewer.add_image(deconvolved, rgb=True)

# data = cp.random.poisson(10*np.ones([10,10,10]))
# bin1 = cp.zeros_like(data)8
# bin2 = cp.zeros_like(data)
# dataShape = np.shape(data)

# threadsperblock = 8
# data_blocks_per_grid_z = (dataShape[0] + (threadsperblock - 1)) // threadsperblock
# data_blocks_per_grid_y = (dataShape[1] + (threadsperblock - 1)) // threadsperblock
# data_blocks_per_grid_x = (dataShape[2] + (threadsperblock - 1)) // threadsperblock
#
# rng_states = create_xoroshiro128p_states(
#                         threadsperblock**3 * data_blocks_per_grid_z * data_blocks_per_grid_y * data_blocks_per_grid_x, seed=0)
#
# gpuBinomialSplit[(data_blocks_per_grid_z, data_blocks_per_grid_y, data_blocks_per_grid_x), (
#                         threadsperblock, threadsperblock, threadsperblock)](data, bin1, bin2, 0.2, rng_states)