import numpy as np


class TransformMatHandler:

    def makeSOLSTransformMatrix(self, dataPropertiesDict, algOptionsDict):
        """Make coordinate transformation matrix such that sampleCoordinates = M * dataCoordinates,
        This is not a fully generic approach, if the tilt eg. is negative, it is not possible to create a correct
        transform matrix with this code. If needed, it might be easier to flip the scan axis of the data first instead
        of adjusting the transformation"""
        scanAxis = dataPropertiesDict['Scan axis']
        tiltAxis = dataPropertiesDict['Tilt axis']
        tiltAng_rad = np.deg2rad(dataPropertiesDict['Tilt angle [deg]'])
        camPxSize_nm = dataPropertiesDict['Camera pixel size [nm]']
        scanStepSize_nm = dataPropertiesDict['Scan step size [nm]']

        sampleVxSize_nm = algOptionsDict['Reconstruction voxel size [nm]']

        otherAxis = 3 - (scanAxis + tiltAxis)

        otherAxisCol = [camPxSize_nm * np.sin(tiltAng_rad), camPxSize_nm * np.cos(tiltAng_rad), 0]
        tiltAxisCol = [0, 0, camPxSize_nm]
        scanAxisCol = [0, scanStepSize_nm, 0]

        # scanAxisRow = [camPxSize_nm * np.cos(tiltAng_rad), scanStepSize_nm, 0]
        # tiltAxisRow = [0, 0, camPxSize_nm]
        # otherAxisRow = [camPxSize_nm * np.sin(tiltAng_rad), 0, 0]

        transformMat = np.zeros([3,3])
        transformMat[:, scanAxis] = scanAxisCol
        transformMat[:, tiltAxis] = tiltAxisCol
        transformMat[:, otherAxis] = otherAxisCol
        voxelize_scale_mat = np.array(
            [[1 / sampleVxSize_nm, 0, 0], [0, 1 / sampleVxSize_nm, 0], [0, 0, 1 / sampleVxSize_nm]])

        M = np.matmul(voxelize_scale_mat, transformMat)

        return M