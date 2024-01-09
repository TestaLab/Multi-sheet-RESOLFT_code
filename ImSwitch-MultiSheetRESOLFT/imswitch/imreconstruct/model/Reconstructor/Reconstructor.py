
import numpy as np
import cupy as cp
from cupyx.scipy import signal as cpsig
from cupyx.scipy.ndimage import affine_transform
from numba import cuda
from .gpu_kernels import gaussDistribTransform
from imswitch.imcommon.model import dirtools, initLogger

mempool = cp.get_default_memory_pool()
pinned_mempool = cp.get_default_pinned_memory_pool()

class Reconstructor:
    """ This class takes the raw data together with pre-set
    parameters and recontructs and stores the final images (for the different
    bases).
    """

    def __init__(self):
        self.__logger = initLogger(self)

    def getReconstructionSize(self, dataShape, cam_px_size, alpha_rad, dy_step_size, recon_vx_size):
        """Get size of reconstruction, this is just a very ugly temp solution"""

        camera_offset = 100

        """Make coordiate transformation matrix such that sampleCoordinates = M * dataCoordinates"""
        transformation_mat = cp.array([[cam_px_size * np.sin(alpha_rad), 0, 0],
                                       [cam_px_size * np.cos(alpha_rad), dy_step_size, 0],
                                       [0, 0, cam_px_size]])
        voxelize_scale_mat = cp.array(
            [[1 / recon_vx_size, 0, 0], [0, 1 / recon_vx_size, 0], [0, 0, 1 / recon_vx_size]])

        M = cp.matmul(voxelize_scale_mat, transformation_mat)

        """Reshape data"""
        permuted_axis = np.array([1, 0, 2])
        size_data = dataShape[permuted_axis]
        """Calculate reconstruction canvas size"""
        cp_size_data = cp.array(size_data)
        cp_size_sample = cp.ceil(cp.matmul(M, cp_size_data)).astype(int)
        size_sample = cp.asnumpy(cp_size_sample)

        return size_sample

    def simpleDeskew(self, data, cam_px_size, alpha_rad, dy_step_size, recon_vx_size):
        """Deskew the data in one step transform"""

        camera_offset = 100

        """Make coordiate transformation matrix such that sampleCoordinates = M * dataCoordinates"""
        transformation_mat = cp.array([[cam_px_size * np.sin(alpha_rad), 0, 0],
                                       [cam_px_size * np.cos(alpha_rad), dy_step_size, 0],
                                       [0, 0, cam_px_size]])
        voxelize_scale_mat = cp.array(
            [[1 / recon_vx_size, 0, 0], [0, 1 / recon_vx_size, 0], [0, 0, 1 / recon_vx_size]])

        M = cp.matmul(voxelize_scale_mat, transformation_mat)

        """Reshape data"""
        permuted_axis = (1, 0, 2)
        data_correct_axes = np.transpose(data, axes=permuted_axis)
        size_data = data_correct_axes.shape
        """Calculate reconstruction canvas size"""
        cp_size_data = cp.array(size_data)
        cp_size_sample = cp.ceil(cp.matmul(M, cp_size_data)).astype(int)
        size_sample = cp.asnumpy(cp_size_sample)

        interp_size_fac = 1 # 1 means gauss FWHM = distance to nearest datapoint
        x_dist_px = cam_px_size / recon_vx_size  # px size in vx
        y_dist_px = dy_step_size / recon_vx_size
        z_dist_px = dy_step_size * np.tan(alpha_rad) / recon_vx_size  # distance between planes in vx
        z_halfsize = int(np.ceil(0.5 * z_dist_px))
        y_halfsize = int(np.ceil(0.5 * y_dist_px))
        x_halfsize = int(np.ceil(0.5 * x_dist_px))
        sigma_z = z_dist_px / 2.355
        sigma_y = y_dist_px / 2.355
        sigma_x = x_dist_px / 2.355
        sigma_z, sigma_y, sigma_x = interp_size_fac * sigma_z, interp_size_fac * sigma_y, interp_size_fac * sigma_x

        free_mem = cuda.current_context().get_memory_info()[0]
        needed_sample_volumes = 2
        needed_data_volumes = 1
        tot_data_elements = needed_sample_volumes*np.prod(size_sample) + needed_data_volumes*np.prod(size_data)
        f32memusage = 4*tot_data_elements
        if f32memusage > free_mem:
            dt = 'float16'
            print('Low on memory, using 16-bit precision float')
        else:
            dt = 'float32'
        """Reconstruct"""
        threadsperblock = 8
        blocks_per_grid_z = (size_data[0] + (threadsperblock - 1)) // threadsperblock
        blocks_per_grid_y = (size_data[1] + (threadsperblock - 1)) // threadsperblock
        blocks_per_grid_x = (size_data[2] + (threadsperblock - 1)) // threadsperblock
        try:
            dataOnes = cp.ones(data_correct_axes.shape)
            invTransfOnes = cp.zeros(size_sample, dtype=dt)
            gaussDistribTransform[(blocks_per_grid_z, blocks_per_grid_y, blocks_per_grid_x),
                                  (threadsperblock, threadsperblock, threadsperblock)](dataOnes, invTransfOnes, M, sigma_z, sigma_y, sigma_x, z_halfsize, y_halfsize, x_halfsize)
            del dataOnes
            invTransfOnes = invTransfOnes.clip(0.01)
            adjustedData = cp.array(data_correct_axes, dtype=dt)
            adjustedData = cp.subtract(adjustedData, camera_offset).clip(0)
            recon_canvas = cp.zeros(size_sample, dtype=dt)
            gaussDistribTransform[(blocks_per_grid_z, blocks_per_grid_y, blocks_per_grid_x),
                                  (threadsperblock, threadsperblock, threadsperblock)](adjustedData, recon_canvas, M, sigma_z, sigma_y, sigma_x, z_halfsize, y_halfsize, x_halfsize)
            reconstructed = cp.asnumpy(cp.divide(recon_canvas, invTransfOnes))
            del adjustedData
            del recon_canvas
            del invTransfOnes
            mempool.free_all_blocks()
        except cp.cuda.memory.OutOfMemoryError:
            print('Out of memory')
            return None

        return reconstructed


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
