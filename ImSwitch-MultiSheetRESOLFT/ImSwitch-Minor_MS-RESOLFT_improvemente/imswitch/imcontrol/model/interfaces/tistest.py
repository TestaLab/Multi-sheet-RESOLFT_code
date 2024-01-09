from imswitch.imcontrol.model.interfaces.pyicic import IC_ImagingControl
import matplotlib.pyplot as plt
import numpy as np

cameraNo = 0

ic_ic = IC_ImagingControl.IC_ImagingControl()
ic_ic.init_library()
cam_names = ic_ic.get_unique_device_names()
model = cam_names[cameraNo]
cam = ic_ic.get_device(model)
cam.open()
cam.enable_continuous_mode(True)
cam.colorenable = 0
cam.enable_trigger(False)

roi_filter = cam.create_frame_filter('ROI')
cam.add_frame_filter_to_device(roi_filter)

cam.prepare_live()
cam.start_live()
frame, width, height, depth = cam.get_image_data()
frame = np.array(frame, dtype='float64')
frame = np.reshape(frame, (height, width, depth))[:, :, 0]
cam.stop_live()
plt.imshow(frame)