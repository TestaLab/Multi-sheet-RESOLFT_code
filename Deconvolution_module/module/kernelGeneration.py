import copy

import numpy as np
from module.DataIO_tools import DataIO_tools
from scipy.signal import fftconvolve

class KernelHandler:

    def makePLSRKernel(self, dataPropertiesDict, imFormationModelParameters, algOptionsDict):

        opticalPSFPath = imFormationModelParameters['Optical PSF path']
        vxSize = algOptionsDict['Reconstruction voxel size [nm]']
        confinedSheetFWHM_nm = imFormationModelParameters['Confined sheet FWHM [nm]']
        roSheetFWHM_nm = imFormationModelParameters['Read-out sheet FWHM [nm]']
        bgSheetRatio = imFormationModelParameters['Background sheet ratio']
        tiltAng_rad = np.deg2rad(dataPropertiesDict['Tilt angle [deg]'])
        cropToOptimizeClipFactor = algOptionsDict['Clip factor for kernel cropping']
        camPxSize_nm  = dataPropertiesDict['Camera pixel size [nm]']

        PSF = DataIO_tools.load_data(opticalPSFPath)

        """Effective PSF generation"""
        PSF_size_z = PSF.shape[0] - 1
        PSF_size_y = PSF.shape[1] - 1
        PSF_size_x = PSF.shape[2] - 1
        ePSFMesh_z, ePSFMesh_y, ePSFMesh_x = np.meshgrid(np.linspace(0, PSF_size_z, PSF_size_z + 1) - PSF_size_z / 2,
                                                         np.linspace(0, PSF_size_y, PSF_size_y + 1) - PSF_size_z / 2,
                                                         np.linspace(0, PSF_size_x, PSF_size_x + 1) - PSF_size_z / 2,
                                                         indexing='ij')
        confinedSheetSigma = confinedSheetFWHM_nm / (2.355 * vxSize)
        confocalSheetSigma = roSheetFWHM_nm / (2.355 * vxSize)
        confinedEmSheet = np.exp(-(ePSFMesh_z * np.cos(tiltAng_rad) - ePSFMesh_y * np.sin(tiltAng_rad)) ** 2 / (2 * confinedSheetSigma ** 2))
        confocalEmSheet = np.exp(-(ePSFMesh_z * np.cos(tiltAng_rad) - ePSFMesh_y * np.sin(tiltAng_rad)) ** 2 / (2 * confocalSheetSigma ** 2))
        emSheet = bgSheetRatio*confocalEmSheet + (1 - bgSheetRatio)*confinedEmSheet
        ePSF = emSheet * PSF

        if camPxSize_nm > 2*vxSize:
            pxVol = self._makePixelKernel(vxSize, camPxSize_nm, tiltAng_rad)
            finalKernel = fftconvolve(ePSF, pxVol)
        else:
            finalKernel = ePSF
        DataIO_tools.save_data(self._cropToOptimize(finalKernel, clipFactor=cropToOptimizeClipFactor), 'emSheetUsed.tif')
        return self._cropToOptimize(finalKernel, clipFactor=cropToOptimizeClipFactor)

    def _cropToOptimize(self, volume, clipFactor=0.01):

        z_max_trace = [np.max(volume[i, :, :]) for i in range(volume.shape[0])]
        y_max_trace = [np.max(volume[:, i, :]) for i in range(volume.shape[1])]
        x_max_trace = [np.max(volume[:, :, i]) for i in range(volume.shape[2])]
        cutoffInt = volume.max() * clipFactor
        z_range = np.where(z_max_trace > cutoffInt)[0]
        y_range = np.where(y_max_trace > cutoffInt)[0]
        x_range = np.where(x_max_trace > cutoffInt)[0]
        croppedVolume = volume[z_range[0]:z_range[-1] + 1, y_range[0]:y_range[-1] + 1, x_range[0]:x_range[-1] + 1]

        return croppedVolume

    def _makePixelKernel(self, sampleVxSize, camPxSize_nm, tiltAngle_rad, pxThickness_nm=80):

        px_size_x_nm = camPxSize_nm
        px_size_y_nm = camPxSize_nm * np.cos(tiltAngle_rad)
        px_size_z_nm = camPxSize_nm * np.sin(tiltAngle_rad)
        px_size_arr = np.array([px_size_z_nm, px_size_y_nm, px_size_x_nm])
        px_voxels = (np.floor((px_size_arr / sampleVxSize) / 2) * 2 + 1).astype(int)

        px_mesh = np.meshgrid(np.linspace(0, px_voxels[0], px_voxels[0]) - px_voxels[0] / 2,
                              np.linspace(0, px_voxels[1], px_voxels[1]) - px_voxels[1] / 2,
                              np.linspace(0, px_voxels[2], px_voxels[2]) - px_voxels[2] / 2, indexing='ij')
        print(px_mesh[0].shape)
        sigma_vx = pxThickness_nm / (2.355 * sampleVxSize)
        pxVol = np.exp(-(px_mesh[0] * np.cos(tiltAngle_rad) - px_mesh[1] * np.sin(tiltAngle_rad)) ** 2 / (2 * sigma_vx ** 2))

        return pxVol
