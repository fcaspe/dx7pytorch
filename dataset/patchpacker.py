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
from zlib import crc32


def get_unique(hashlist,patches,n_similar):
    
    n_patches = int(len(patches)/128)
    patches = patches.reshape((n_patches,128)).astype(np.uint8)
    unique_patches = np.empty(0)
    
    for i in range(n_patches):
        patch_hash = crc32(patches[i,0:118])
        if(sum(np.isin(hashlist, patch_hash)) == 0):
            hashlist = np.append(hashlist,patch_hash)
            unique_patches = np.append(unique_patches,patches[i,:])
        else:
            n_similar += 1
    return hashlist,unique_patches,n_similar

mypath = os.path.abspath(sys.argv[1])

onlyfiles = [f for f in listdir(mypath) if isfile(join(mypath, f))]

print("Processing {} files. Please wait . . .".format(len(onlyfiles)))

collection = np.empty(0)
hashlist = np.empty(0)
n_total_processed = 0
n_similar = 0

for i in range(len(onlyfiles)):
    filearray = np.fromfile(mypath + '/' + onlyfiles[i], dtype=np.uint8)
    #Check DX7 MK1 sysex header.
    compare = filearray[0:6] == np.array([0xF0, 0x43, 0x00, 0x09, 0x20, 0x00])
    #Check file size.
    if(len(filearray) != 4104):
        #print("Error in file {}. Unexpected sysex header. Skipping".format(onlyfiles[i],filearray[0:6]))
        continue
    if(compare.all() == False):
        continue
    
    hashlist,unique_patches,n_similar = get_unique(hashlist,filearray[6:4102],n_similar)
    collection = np.append(collection,unique_patches)
    n_total_processed += 32
    if(i % 50 == 0 and i != 0):
        print("Processed {} files.".format(i))

print("Processed {} patches. {} similar patches filtered.".format(n_total_processed,n_similar))
print("Compiled patch dataset contains {} patches.".format(int(len(collection)/128)))

collection.astype('uint8').tofile("collection.bin")
