import numpy as np

from imswitch.imcommon.model import initLogger


class ReconObj:
    def __init__(self, name, timepoints_text, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.__logger = initLogger(self, instanceName=name)

        self.timepoints_text = timepoints_text

        self.name = name
        self.reconstructed = None

        self.dispLevels = None


    def allocateReconstruction(self, timepoints, size):
        self._reconSize = size
        arraySize = np.insert(size, 0, timepoints)
        self.reconstructed = np.zeros(arraySize, dtype='float32')

    def setReconstruction(self, reconstruction):
        #Here one could maybe preallocate an array big enough for all timepoints
        self.reconstructed = np.array([reconstruction], dtype='float32')

    def addReconstructionTimepoint(self, timepoint, new_reconstruction):
        if not new_reconstruction is None:
            self.reconstructed[timepoint] = new_reconstruction
            self.__logger.debug('Added timepoint, ndim of reconstruction is %s', self.reconstructed.ndim)
        else:
            self.__logger.warning('Tried to add reconstruction that is None')
    def setDispLevels(self, levels):
        self.dispLevels = levels

    def getDispLevels(self):
        return self.dispLevels

    def getReconstruction(self):
        return self.reconstructed

    def getScanParams(self):
        return self.scanParDict

    def updateScanParams(self, scanParDict):
        self.scanParDict = scanParDict



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
