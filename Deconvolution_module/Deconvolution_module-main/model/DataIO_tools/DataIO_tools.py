# -*- coding: utf-8 -*-
"""
Created on Tue May 14 12:41:27 2019

@author: andreas.boden
"""
import os

import tifffile as tiff
import h5py
import numpy as np
import scipy.io as sio
import pickle
import matplotlib.pyplot as plt
from pyqtgraph.Qt import QtGui
import csv

def load_data(path=None, h5dataset=None, dtype=None):
    if path is None:
        dlg = QtGui.QFileDialog()
        path =  dlg.getOpenFileName()[0]
    try:
        ext = os.path.splitext(path)[1]

        if ext in ['.hdf5', '.hdf']:
            with h5py.File(path, 'r') as datafile:
                data = np.array(datafile[h5dataset][:])

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
    except KeyError as ke:
        print('Probably wrong name of dataset')
        print(ke)
    except:
        print('Unknown error while loading data')


def save_data(data, path=None, dtype=None, vx_size=None, unit='px'):

    dimensions = len(data.shape)

    newshape = np.append(np.ones(5-dimensions), data.shape).astype(np.int)
    data.shape = newshape[1], newshape[2], newshape[0], newshape[3], newshape[4]

    if not dtype is None:
        try:
            data = data.astype(dtype)
        except:
            print('Could not convert data to specified type')
    else:
        data = data.astype(np.float32)

    if data.dtype == np.float64:
        data = data.astype(np.float32)
        print('WARNING: Converted float64 data to float32 to enable saving')

    if path is None:
        dlg = QtGui.QFileDialog()
        path = dlg.getSaveFileName(directory=os.getcwd(), filter='*.tif')[0]
        print('Path chosen is:', path)

    print('Saving data in: ' + path)

    if vx_size is None:
        tiff.imwrite(path, data,
            imagej=True, metadata={'unit': unit,
                                   'axes': 'TZCYX'})
    else:
        vx_size = np.asarray(vx_size)
        if len(vx_size) == 1:
            tiff.imwrite(path, data, resolution=(1/vx_size[0], 1/vx_size[0]),
                imagej=True, metadata={'unit': unit,
                                       'axes': 'TZCYX'})
            print('Finished saving')
        elif len(vx_size) == 2:
            tiff.imwrite(path, data, resolution=(1/vx_size[0], 1/vx_size[1]),
                imagej=True, metadata={'unit': unit,
                                       'axes': 'TZCYX'})
            print('Finished saving')
        elif len(vx_size) == 3:
            tiff.imwrite(path, data, resolution=(1/vx_size[0], 1/vx_size[1]),
                imagej=True, metadata={'spacing': vx_size[2],
                                       'unit': unit,
                                       'axes': 'TZCYX'})
            print('Finished saving')


def stack2tifs(stackpath=None):

    if stackpath is None:
        dlg = QtGui.QFileDialog()
        stackpath =  dlg.getOpenFileName()[0]

    stack = load_data(stackpath)

    newdir = os.path.split(stackpath)[0] + '/ims_from_stack'
    os.mkdir(newdir)
    for i in range(len(stack)):
        im = stack[i]
        save_data(im, newdir + '/' + 'im' + str(i+1) + '.' + 'tif')

def stack2figs_pcolormesh(xi1=None, xi2=None, yi=None, stackpath=None, level_range=[None, None], ylog=False, xlog=False, figs=None, ylab=None, xlab=None):

    if stackpath is None:
        dlg = QtGui.QFileDialog()
        stackpath =  dlg.getOpenFileName()[0]

    stack = load_data(stackpath)

    if xi1 is None:
        xi1 = np.linspace(0, stack.shape[2]-1, stack.shape[2])
    if yi is None:
        yi = np.linspace(0, stack.shape[1]-1, stack.shape[1])

    newdir = os.path.split(stackpath)[0] + '/ims_from_stack'
    os.mkdir(newdir)
    for i in range(len(stack)):
        fig = plt.figure(figsize=figs)
        plt.ylabel(ylab)
        plt.xlabel(xlab)
        plt.pcolormesh(xi1, yi, stack[i], vmin=level_range[0], vmax=level_range[1])
        if ylog:
            plt.yscale('log')
        if xlog:
            plt.xscale('log')
        plt.savefig(newdir + '/' + 'im' + str(i+1) + '.' + 'jpeg',
                    bbox_inches='tight', dpi=500)
        plt.close(fig)

def stack2figs_imshow(stackpath=None, level_range=None):

    if stackpath is None:
        dlg = QtGui.QFileDialog()
        stackpath =  dlg.getOpenFileName()[0]

    stack = load_data(stackpath)

    newdir = os.path.split(stackpath)[0] + '/ims_from_stack'
    os.mkdir(newdir)
    for i in range(len(stack)):
        fig = plt.figure()
        plt.imshow(stack[i], vmin=level_range[0], vmax=level_range[1])
        plt.savefig(newdir + '/' + 'im' + str(i+1) + '.' + 'tif',
                    bbox_inches='tight', dpi=500)
        plt.close(fig)

def load_variable_from_matfile(filepath=None, variable_name=None):
    
    data = sio.loadmat(filepath)[variable_name]
    
    return data
    
def load_array_from_csv(filepath=None):
    if filepath is None:
        dlg = QtGui.QFileDialog()
        filepath =  dlg.getOpenFileName()[0]

    with open(filepath) as csv_file:
           csv_reader = csv.reader(csv_file, delimiter=',')
           
           arr = []
           for row in csv_reader:
               arr.append(np.float(row[0]))
               
    return arr


def load_raw_from_csv(filepath=None):
    if filepath is None:
        dlg = QtGui.QFileDialog()
        filepath =  dlg.getOpenFileName()[0]

    with open(filepath) as csv_file:
           csv_reader = csv.reader(csv_file, delimiter=',')
           
           arr = []
           for row in csv_reader:
               arr.append(row)
               
    return arr

def load_csvXYdata(filepath=None):
    
    if filepath is None:
        dlg = QtGui.QFileDialog()
        filepath =  dlg.getOpenFileName()[0]

    with open(filepath) as csv_file:
        csv_reader = csv.reader(csv_file, delimiter=',')
        x = []
        y = []
        for row in csv_reader:
            if csv_reader.line_num == 1:
                data_sets = len(row)/2
            else:
                temp_x = []
                temp_y = []
                for s in range(np.int(data_sets)):
                    try:
                        temp_x.append(np.float(row[2*s]))
                    except ValueError:
                        temp_x.append(np.nan)
                    try:
                        temp_y.append(np.float(row[1+2*s]))
                    except ValueError:
                        temp_y.append(np.nan)
                    
                x.append(temp_x)
                y.append(temp_y)
                
        x = np.asarray(x)
        y = np.asarray(y)
                
        x = x.transpose()
        y = y.transpose()
        
    return x, y


def load_pickle_to_locals(path=None):
    
    if path is None:
        dlg = QtGui.QFileDialog()
        path =  dlg.getOpenFileName()[0]
    
    with open(path, 'rb') as variablefile:
        variables = pickle.load(variablefile)
        locals().update(variables)
    

#if __name__ == '__main__':
#    stack2figs_pcolormesh()
