import os
import sys

if not os.environ['GITHUB'] in sys.path:
  sys.path.append(os.environ['GITHUB'])

from Python_Utilities import DataIO_tools

data = DataIO_tools.load_data(r'D:\SnoutyData\2022-12-19\ActinChromo_HeLa_data.shapeN205S_cell1_plsr_timelapse_30tp_1min_rec_Orca.hdf5', h5dataset='Orca')