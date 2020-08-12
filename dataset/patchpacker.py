#!/usr/bin/python

'''
Simple patch packer.

This file will process all patch files within a directory and pack all valid DX7 patches into
a 'collection.bin' file which can be used by dx7pytorch.

Usage: 
    python3 patchpacker.py /path/to/syx/files

DX7 Patch sources
-----------------

http://dxsysex.com/SYSEX_DX7/A/dx7-sysex-A.php

http://bobbyblues.recup.ch/yamaha_dx7/dx7_patches.html

'''

import numpy as np
import os
from os import listdir
from os.path import isfile, join
import sys


mypath = os.path.abspath(sys.argv[1])

onlyfiles = [f for f in listdir(mypath) if isfile(join(mypath, f))]

print("Found {} files.".format(len(onlyfiles)))

collection = np.empty(0)
for i in range(len(onlyfiles)):
    filearray = np.fromfile(mypath + '/' + onlyfiles[i], dtype=np.uint8)
    compare = filearray[0:6] == np.array([0xF0, 0x43, 0x00, 0x09, 0x20, 0x00])
    if(len(filearray) != 4104):
        #print("Error in file {}. Unexpected sysex header. Skipping".format(onlyfiles[i],filearray[0:6]))
        continue
    if(compare.all() == False):
        continue
    collection = np.append(collection,filearray[6:4102])

print("Compiled patch dataset contains {} patches.".format(len(collection)/128))

collection.astype('uint8').tofile("collection.bin")
