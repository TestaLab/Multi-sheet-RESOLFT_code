import os
import h5py
import tifffile as tiff
import matplotlib.pyplot as plt
import numpy as np
import copy
from module.DataIO_tools import DataIO_tools
import scipy.ndimage as ndi

class DataFiddler:

    def __init__(self):
        self.dataPath = None
        self.rawData = None
        self.adjustedData = None
        self.dataPropertiesDict = None

    def loadData(self, path, dataPropertiesDict, h5dataset=None):

        ext = os.path.splitext(path)[1]
        if ext in ['.hdf5', '.hdf']:
            with h5py.File(path, 'r') as datafile:
                if h5dataset is None:
                    print('No dataset given, loading first one')
                    h5dataset = list(datafile.keys())[0]
                self.rawData = np.array(datafile[h5dataset][:]).astype(float)

        elif ext in ['.tiff', '.tif']:
            with tiff.TiffFile(path) as datafile:
                self.rawData = datafile.asarray().astype(float)

        self.dataPropertiesDict = dataPropertiesDict

    def checkData(self):
        expectedLength = self.dataPropertiesDict['Timepoints'] * \
                         self.dataPropertiesDict['Cycles'] * \
                         self.dataPropertiesDict['Planes in cycle']

        if expectedLength != len(self.rawData):
            print('Frames in data does not match given data properties')
            return False
        else:
            return True

    def getDataTimepointShape(self):
        framesInTimepoint = self.dataPropertiesDict['Cycles'] * self.dataPropertiesDict['Planes in cycle']
        return (framesInTimepoint,
                self.rawData.shape[1],
                self.rawData.shape[2])

    def getNrOfTimepoints(self):
        return self.dataPropertiesDict['Timepoints']

    def getDataPropertiesDict(self):
        return self.dataPropertiesDict

    def _correctPxOffsets(self, data):
        print('Correcting pixel offsets')
        axialMean = np.mean(data, 0)
        pxOffset = copy.copy(axialMean)
        for i in range(-1, 2):
            for j in range(-1, 2):
                if i == j == 0:
                    continue
                pxOffset -= (1 / 8) * np.roll(axialMean, (i, j))

        data[:] -= pxOffset

    def _adjustForOffset(self, data):
        print('Adjusting for camera offset')
        data[:] = (data - self.dataPropertiesDict['Camera offset']).clip(0)

    def _correctFirstCycle(self, data):
        print('Correcting first cycle')
        planesInCycle = self.dataPropertiesDict['Planes in cycle']

        averageFirstCycle = np.mean(data[:planesInCycle])
        averageSecondCycle = np.mean(data[planesInCycle:2 * planesInCycle])
        averageLastCycle = np.mean(data[-planesInCycle:])

        corrFac = (averageSecondCycle + averageLastCycle) / (2 * averageFirstCycle)
        data[:planesInCycle] *= corrFac

    def _restackData(self, data):
        print('Restacking data')
        planesInCycle = self.dataPropertiesDict['Planes in cycle']
        cycles = self.dataPropertiesDict['Cycles']

        restacked = np.zeros_like(data)
        for i in range(planesInCycle):
            restacked[i * cycles:(i + 1) * cycles] = data[i::planesInCycle]

        data[:] = restacked
        del restacked

    def _correctSkewedScan(self, data, pxPerCycleShift):
        """Takes in restacked data"""
        print('Correcting for skewed scan')
        #Below some attempt to automatically get correct axis, but not sure its relevant
        shiftAxis = 2 - self.dataPropertiesDict['Tilt axis']
        shift = [0,0]
        for i in range(len(data)):
            cycleIndex = np.mod(i, self.dataPropertiesDict['Cycles'])
            shift[shiftAxis] = cycleIndex*pxPerCycleShift
            data[i] = ndi.shift(data[i], shift, mode='constant').clip(0) #Clipping since shift may cause small negative due to interpolation

    def getPreprocessedData(self, timepoint=None):
        if timepoint is None:
            if self.getNrOfTimepoints() != 0:
                print('Must specify timepoint for data with more than one timepoint')
                return False
            startFrame = 0
            endFrame = len(self.rawData)
        else:
            startFrame = timepoint * self.getDataTimepointShape()[0]
            endFrame = (timepoint + 1) * self.getDataTimepointShape()[0]

        self.processedData = copy.copy(self.rawData[startFrame:endFrame])
        if self.dataPropertiesDict['Correct pixel offsets']:
            self._correctPxOffsets(self.processedData)
        self._adjustForOffset(self.processedData)
        if self.dataPropertiesDict['Correct first cycle']:
            self._correctFirstCycle(self.processedData)
        if self.dataPropertiesDict['Data stacking'] == 'PLSR Interleaved':
            self._restackData(self.processedData)
        if self.dataPropertiesDict['Skew correction pixel per cycle'] != 0:
            self._correctSkewedScan(self.processedData,
                                    pxPerCycleShift=self.dataPropertiesDict['Skew correction pixel per cycle'])
        if self.dataPropertiesDict['Pos/Neg scan direction'] == 'Neg':
            return np.flip(self.processedData, self.dataPropertiesDict['Scan axis'])
        else:
            return self.processedData


# dataPath = r'ActinChromo_HeLa_N205S_cell7_plsr_rec_Orca.hdf5'
# data = DataIO_tools.load_data(dataPath, h5dataset='Orca', dtype=float)
#
# import copy
# axialMean = np.mean(data, 0)
# pxOffset = copy.copy(axialMean)
# fig, (ax1, ax2) = plt.subplots(2,1)
# ax1.imshow(axialMean)
# for i in range(-1,2):
#     for j in range(-1,2):
#         if i == j == 0:
#             continue
#         print(i,j)
#         pxOffset -= (1/8)*np.roll(axialMean, (i,j))
#
# corrMean = axialMean - pxOffset
#
# ax2.imshow(corrMean)
