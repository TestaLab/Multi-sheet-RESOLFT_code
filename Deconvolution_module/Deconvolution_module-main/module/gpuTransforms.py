from numba import cuda

@cuda.jit
def convTransform(dataStack, sampleVol, kernel, transformMat):
    """Retrieve the value from the sample guess as if a convolution with the kernel was performed first"""
    idz, idy, idx = cuda.grid(3)
    if idz < dataStack.shape[0] and idy < dataStack.shape[1] and idx < dataStack.shape[2]:
        sampleCoords_z = transformMat[0, 0] * idz + transformMat[0, 1] * idy + transformMat[0, 2] * idx
        sampleCoords_y = transformMat[1, 0] * idz + transformMat[1, 1] * idy + transformMat[1, 2] * idx
        sampleCoords_x = transformMat[2, 0] * idz + transformMat[2, 1] * idy + transformMat[2, 2] * idx

        # Round to nearest and cast to int
        sampleIndex_z = int(round(sampleCoords_z))
        sampleIndex_y = int(round(sampleCoords_y))
        sampleIndex_x = int(round(sampleCoords_x))

        volume_size = kernel.shape

        finalValue = 0
        for zk in range(0, volume_size[0]):
            z = sampleIndex_z + zk - (volume_size[0] // 2)
            for yk in range(0, volume_size[1]):
                y = sampleIndex_y + yk - (volume_size[1] // 2)
                for xk in range(0, volume_size[2]):
                    x = sampleIndex_x + xk - (volume_size[2] // 2)
                    if 0 <= z < sampleVol.shape[0] and 0 <= y < sampleVol.shape[
                        1] and 0 <= x < sampleVol.shape[2]:
                        finalValue += sampleVol[z, y, x] * kernel[-zk-1, -yk-1, -xk-1] #Minus for the flipping in convolution
        dataStack[idz, idy, idx] = finalValue



"""Inverse model"""
@cuda.jit
def invConvTransform(dataStack, sampleVol, kernel, transformMat):
    """Distribute the values in the data stack back to the sample canvas according to the kernel values
    NOTE: this function is seems to be very slow, probably due to atomicAdd operation."""
    idz, idy, idx = cuda.grid(3)
    if idz < dataStack.shape[0] and idy < dataStack.shape[1] and idx < dataStack.shape[2]:
        sampleCoords_z = transformMat[0, 0] * idz + transformMat[0, 1] * idy + transformMat[0, 2] * idx
        sampleCoords_y = transformMat[1, 0] * idz + transformMat[1, 1] * idy + transformMat[1, 2] * idx
        sampleCoords_x = transformMat[2, 0] * idz + transformMat[2, 1] * idy + transformMat[2, 2] * idx

        # Round to nearest and cast to int
        sampleIndex_z = int(round(sampleCoords_z))
        sampleIndex_y = int(round(sampleCoords_y))
        sampleIndex_x = int(round(sampleCoords_x))

        dataValue = dataStack[idz, idy, idx]
        volume_size = kernel.shape
        for zk in range(0, volume_size[0]):
            z = sampleIndex_z + zk - (volume_size[0] // 2)
            for yk in range(0, volume_size[1]):
                y = sampleIndex_y + yk - (volume_size[1] // 2)
                for xk in range(0, volume_size[2]):
                    x = sampleIndex_x + xk - (volume_size[2] // 2)
                    if 0 <= z < sampleVol.shape[0] and 0 <= y < sampleVol.shape[
                        1] and 0 <= x < sampleVol.shape[2]:
                        """The minus remains here below since we 1. want to convolve with the flipped PSF and
                        2. are performing the convolution in the opposite way i.e. distributing the value according to
                        the kernel and not retrieving the value according to the kernel as usually in convolution. These 
                        two facts both flip the kernel and cancel out, so we keep the minus as we have in the forward model"""
                        value = dataValue * kernel[-zk-1, -yk-1, -xk-1]
                        cuda.atomic.add(sampleVol, (z, y, x), value)