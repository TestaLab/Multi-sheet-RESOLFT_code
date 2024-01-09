import os
import sys

import numpy as np
import cupy as cp
from cupyx.scipy import signal as cpsig
from cupyx.scipy import ndimage as cpndi
from scipy import signal as ss
from numba import cuda
import math
import h5py
import tifffile as tiff

def load_data(path=None, dtype=None):

    try:
        ext = os.path.splitext(path)[1]

        if ext in ['.hdf5', '.hdf']:
            with h5py.File(path, 'r') as datafile:
                data = np.array(datafile['Images'][:])

        elif ext in ['.tiff', '.tif']:
            with tiff.TiffFile(path) as datafile:
                data = datafile.asarray()

        if dtype == None:
            return data
        else:
            return data.astype(dtype)
    except FileNotFoundError as fnf_error:
        print('Error while loading data')
        print(fnf_error)
        return None
    except:
        print('Unknown error while loading data')

import matplotlib.pyplot as plt
mempool = cp.get_default_memory_pool()
pinned_mempool = cp.get_default_pinned_memory_pool()

# """ PSF generation """
# psf_foler = r'A:\GitHub\ImSim\PSFs'
# psf_file = r'PSF_1.26NA_RW_40nmVX_large.tif'
# psf_path = os.path.join(psf_foler, psf_file)
# PSF = load_data(psf_path)

fastRecon = True
RLRecon = False


""" Forward model """
@cuda.jit
def NNTransform(dataStack, sampleVol, transformMat, offset):
    """Retrieve the nearest neighbour value from the samplevolume and place in the datastack"""
    idz, idy, idx = cuda.grid(3)
    if idz < dataStack.shape[0] and idy < dataStack.shape[1] and idx < dataStack.shape[2]:
        sampleCoords_z = transformMat[0, 0] * idz + transformMat[0, 1] * idy + transformMat[0, 2] * idx
        sampleCoords_y = transformMat[1, 0] * idz + transformMat[1, 1] * idy + transformMat[1, 2] * idx
        sampleCoords_x = transformMat[2, 0] * idz + transformMat[2, 1] * idy + transformMat[2, 2] * idx

        # Round to nearest and cast to int
        sampleIndex_z = int(round(sampleCoords_z))
        sampleIndex_y = int(round(sampleCoords_y))
        sampleIndex_x = int(round(sampleCoords_x))

        if 0 <= sampleIndex_z < sampleVol.shape[0] and 0 <= sampleIndex_y < sampleVol.shape[1] and 0 <= sampleIndex_x < \
                sampleVol.shape[2]:
            value = sampleVol[sampleIndex_z, sampleIndex_y, sampleIndex_x] + offset
            dataStack[idz, idy, idx] = value
        cuda.syncthreads()


"""Inverse model"""
@cuda.jit
def invNNTransform(dataStack, sampleVol, transformMat, offset):
    """Distribute the values in the data stack back to the sample canvas in the nearest neighbour voxel"""
    idz, idy, idx = cuda.grid(3)
    if idz < dataStack.shape[0] and idy < dataStack.shape[1] and idx < dataStack.shape[2]:
        sampleCoords_z = transformMat[0, 0] * idz + transformMat[0, 1] * idy + transformMat[0, 2] * idx
        sampleCoords_y = transformMat[1, 0] * idz + transformMat[1, 1] * idy + transformMat[1, 2] * idx
        sampleCoords_x = transformMat[2, 0] * idz + transformMat[2, 1] * idy + transformMat[2, 2] * idx

        # Round to nearest and cast to int
        sampleIndex_z = int(round(sampleCoords_z))
        sampleIndex_y = int(round(sampleCoords_y))
        sampleIndex_x = int(round(sampleCoords_x))

        if 0 <= sampleIndex_z < sampleVol.shape[0] and 0 <= sampleIndex_y < sampleVol.shape[1] and 0 <= sampleIndex_x < \
                sampleVol.shape[2]:
            value = dataStack[idz, idy, idx] - offset
            cuda.atomic.add(sampleVol, (sampleIndex_z, sampleIndex_y, sampleIndex_x), value)
        cuda.syncthreads()

"""Test full cycle"""
"""------------------------------------"""
"""Load data"""
data_path = r'\\storage3.ad.scilifelab.se\testalab\Andreas\SOLS\Data\2022-11-18\rsEGFP2(N205S)-MAP2\Cell2_pLSR_3tp_rec_Orca_timeaveraged_data_Restacked.tif'
data = load_data(data_path, dtype=float)

data = data[50:100, 50:152, 200:400]

"""Set parameters"""
flip_data = False


c_px = 116
alpha = np.deg2rad(35)
dy = 210
sample_vx_size = 40
camera_offset = 100
""" optical PSF generation/loading """
psf_folder = r'\\storage3.ad.scilifelab.se\testalab\Andreas\SOLS\Scripts\PSFs'
psf_file = r'PSF_1.26NA_RW_40nmVX_large.tif'
psf_path = os.path.join(psf_folder, psf_file)
PSF = load_data(psf_path)
# PSF = np.random.uniform(0,10,size=(20,20,20))

"""Tilted detection adjustments"""


"""Effective PSF generation"""
PSF_size_z = PSF.shape[0] - 1
PSF_size_y = PSF.shape[1] - 1
PSF_size_x = PSF.shape[2] - 1
ePSFMesh_z, ePSFMesh_y, ePSFMesh_x = np.meshgrid(np.linspace(0, PSF_size_z, PSF_size_z + 1) - PSF_size_z / 2,
                                                 np.linspace(0, PSF_size_y, PSF_size_y + 1) - PSF_size_z / 2,
                                                 np.linspace(0, PSF_size_x, PSF_size_x + 1) - PSF_size_z / 2,
                                                 indexing='ij')
emSheetWidth_nm = 400 #In FWHM
emSheetSigma = emSheetWidth_nm / (2.355*sample_vx_size)
emSheet  = np.exp(-(ePSFMesh_z*np.cos(alpha) - ePSFMesh_y*np.sin(alpha))**2/(2*emSheetSigma**2))
ePSF = emSheet * PSF
"""Crop PSF to save memory"""
z_max_trace = [np.max(ePSF[i,:,:]) for i in range(ePSF.shape[0])]
y_max_trace = [np.max(ePSF[:,i,:]) for i in range(ePSF.shape[1])]
x_max_trace = [np.max(ePSF[:,:,i]) for i in range(ePSF.shape[2])]
cutoffInt = ePSF.max() * 0.01
z_range = np.where(z_max_trace > cutoffInt)[0]
y_range = np.where(y_max_trace > cutoffInt)[0]
x_range = np.where(x_max_trace > cutoffInt)[0]
cropped_ePSF = ePSF[z_range[0]:z_range[-1], y_range[0]:y_range[-1], x_range[0]:x_range[-1]]

"""Make pixel "volume" """
px_thickness_nm = 80 #measured as FWHM
px_size_x_nm = c_px
px_size_y_nm = c_px*np.cos(alpha)
px_size_z_nm = c_px*np.sin(alpha)
px_voxels = np.ceil(np.divide([px_size_z_nm, px_size_y_nm, px_size_x_nm], sample_vx_size) + 1).astype(int)
px_mesh = np.meshgrid(np.linspace(0, px_voxels[0], px_voxels[0]) - px_voxels[0]/2,
                      np.linspace(0, px_voxels[1], px_voxels[1]) - px_voxels[1]/2,
                      np.linspace(0, px_voxels[2], px_voxels[2]) - px_voxels[2]/2, indexing='ij')

sigma_vx = px_thickness_nm / (2.355*sample_vx_size)
px_vol = np.exp(-(px_mesh[0]*np.cos(alpha) - px_mesh[1]*np.sin(alpha))**2/(2*sigma_vx**2))
"""Make convolution kernels"""
cupy_px_vol = cp.array(px_vol)
cupy_epsf = cp.array(cropped_ePSF)
K = cpsig.fftconvolve(cupy_px_vol, cupy_epsf, mode='full').clip(0)
K = cp.divide(K, cp.sum(K)) #Normalize to sum=1
Kt = cp.flipud(cp.fliplr(K[::-1])) #Flip K in all dimensions, could also fo K[::-1,::-1,::-1]
"""Adjust data"""
if flip_data:
    flipped_data = data[::-1]
else:
    flipped_data = data
permuted_axis = (1, 0, 2)
data_correct_axes = np.transpose(flipped_data, axes=permuted_axis)
adjustedData = cp.array(data_correct_axes - camera_offset).clip(0)  # Basic RL-algorithm requires a model where the data is a linear function of the sample, i.e. any offset needs to be removed before data injected into the algorithm
"""Make coordiate transformation matrix such that sampleCoordinates = M * dataCoordinates"""
transformation_mat = cp.array([[c_px * np.sin(alpha), 0, 0], [c_px * np.cos(alpha), dy, 0], [0, 0, c_px]])
voxelize_scale_mat = cp.array([[1 / sample_vx_size, 0, 0], [0, 1 / sample_vx_size, 0], [0, 0, 1 / sample_vx_size]])

M = cp.matmul(voxelize_scale_mat, transformation_mat)

"""Make sample canvas"""
size_data = cp.array(adjustedData.shape)
size_data_host = cp.asnumpy(size_data)
size_sample = cp.ceil(cp.matmul(M, size_data)).astype(int)
invTransfOnes = cp.zeros(cp.asnumpy(size_sample))

dataOnes = cp.ones_like(adjustedData)

threadsperblock = 8
blocks_per_grid_z = (size_data_host[0] + (threadsperblock - 1)) // threadsperblock
blocks_per_grid_y = (size_data_host[1] + (threadsperblock - 1)) // threadsperblock
blocks_per_grid_x = (size_data_host[2] + (threadsperblock - 1)) // threadsperblock
invNNTransform[(blocks_per_grid_z, blocks_per_grid_y, blocks_per_grid_x),
               (threadsperblock, threadsperblock, threadsperblock)](dataOnes, invTransfOnes, M, 0)

Ht_of_ones = cpsig.fftconvolve(invTransfOnes, Kt, mode='same')
Ht_of_ones = Ht_of_ones.clip(0.1 * cp.max(Ht_of_ones)) #Avoid divide by zero and crazy high guesses outsude measured region

"""Single-step deskew"""
"""Make interplation kernel"""
if fastRecon:
    recon_canvas = cp.zeros(cp.asnumpy(size_sample))
    lateral_ratio = c_px / sample_vx_size #px size in vx
    axial_ratio = dy * np.tan(alpha) / sample_vx_size #distance between planes in vx
    z_halfsize = 2*axial_ratio
    y_halfsize = 2*lateral_ratio
    x_halfsize = 2*lateral_ratio
    k_mesh = np.meshgrid(np.linspace(-z_halfsize, z_halfsize, int(np.ceil(2*z_halfsize))),
                         np.linspace(-y_halfsize, y_halfsize, int(np.ceil(2*y_halfsize))),
                         np.linspace(-x_halfsize, x_halfsize, int(np.ceil(2*x_halfsize))), indexing='ij')

    k_prime_z = k_mesh[0] #*np.cos(alpha) - k_mesh[1]*np.sin(alpha)
    k_prime_y = k_mesh[1]#k_mesh[0]*np.sin(alpha) + k_mesh[1]*np.cos(alpha)
    k_prime_x = k_mesh[2]
    sigma_lat = lateral_ratio / 2.355
    sigma_ax = axial_ratio / 2.355

    kernel = np.exp(-(k_prime_x**2/(2*sigma_lat**2) + k_prime_y**2/(2*sigma_lat**2) + k_prime_z**2/(2*sigma_ax**2)))
    kernel = (np.ones_like(k_prime_x) - np.sqrt((k_prime_x/lateral_ratio)**2 + (k_prime_y/lateral_ratio)**2 + (k_prime_z/axial_ratio)**2)).clip(0)
    cupy_kernel = cp.array(kernel)
    """Reconstruct"""
    invNNTransform[(blocks_per_grid_z, blocks_per_grid_y, blocks_per_grid_x),
                   (threadsperblock, threadsperblock, threadsperblock)](adjustedData, recon_canvas, M, 0)

    interpolatedData = cpsig.fftconvolve(recon_canvas, cupy_kernel, mode='same')
    interpolatedHtFromOnes = cpsig.fftconvolve(invTransfOnes, cupy_kernel, mode='same').clip(0.1) #Avoid divide by zero
    recon = cp.asnumpy(cp.divide(interpolatedData, interpolatedHtFromOnes))

if RLRecon:
    sample_guess = cp.ones(cp.asnumpy(size_sample))
    dfg = cp.zeros_like(adjustedData)
    iterations = 10
    for i in range(iterations):
        print('Iteration: ', i)
        convolved_sample_guess = cpsig.fftconvolve(sample_guess, K, mode='same')

        NNTransform[
          (blocks_per_grid_z, blocks_per_grid_y, blocks_per_grid_x), (threadsperblock, threadsperblock, threadsperblock)](
          dfg, convolved_sample_guess, M, 0)

        err = cp.divide(adjustedData, dfg)
        distributedError = cp.zeros_like(sample_guess)
        invNNTransform[(blocks_per_grid_z, blocks_per_grid_y, blocks_per_grid_x),
                       (threadsperblock, threadsperblock, threadsperblock)](err, distributedError, M, 0)
        convolvedDistError = cpsig.fftconvolve(distributedError, Kt, mode='same').clip(0)
        correction = cp.divide(convolvedDistError, Ht_of_ones)
        sample_guess = cp.multiply(sample_guess, correction)


mempool.free_all_blocks()
