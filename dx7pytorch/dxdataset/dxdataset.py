import torch
from torch import dtype as torch_dtype
from torch.utils import data
import numpy as np
from dx7pytorch import dxsynth as dxs
from os import path

class dxdataset(data.Dataset):
    """DX7 sound patch dataset."""

    def __init__(self, sample_rate:int,
            collection:str, valid_notes, valid_velocities,
            note_on_len:int,
            note_off_len:int,
            subsample_ratio=None,
            random_seed=None,
            filter_function=None,
            debug=True,):
        """
        Args:
            sample_rate (int): Sample frequency of synthesizer.
            collection (string): Path to dataset patch collection.
            valid_notes: Allowed MIDI notes we synthesize.
            valid_velocities: Allowed MIDI velocities we can synthesize.
            
            note_on_len  (int): Number of samples to synthesize on note_on.
            note_off_len (int): Number of samples to synthesize on note_off.
            
            subsample_ratio (float): Used to randomly subsample the available patches.
            random_seed (int): Seeds the random generator.
            
            filter_function (string): Selects a patch filter function. Available: 'all_ratio' and 'all_fixed'.
            debug (Bool): Enables verbose output.
            
        """
        np.random.seed(random_seed)
        self.debug = debug
        
        #Instantiate Synthesizer
        self.synth = dxs.dxsynth(sampling_frequency=sample_rate)
        
        print("dx7pytorch: FM Synthesizer for deep learning. Loading dataset . . . ")
        
        patch_file = path.abspath(collection)
        
        # Open file list to process patches. 
        # I think the easiest way is to store everythig in RAM, to minimize disk access.
        self.patches = np.empty(0)
        
        bulk_patches = np.fromfile(patch_file, dtype=np.uint8)
        n_patches = int(len(bulk_patches)/dxs.DX7_VOICE_SIZE_PACKED)
        if(self.debug): print("[DEBUG] Total patches: {}".format(n_patches))
        
        if(filter_function == 'all_ratio'):
            my_filter = self.filter_get_all_op_ratio
        elif(filter_function == 'all_fixed'):
            my_filter = self.filter_get_all_op_fixed
        else:
            my_filter = self.filter_allpass
        
        for i in range(n_patches):
            patch = bulk_patches[i*128:(i+1)*128]
            
            # Process Patch Name. Keep only names below 128 and decide to ascii.
            patch_name = patch[118:127]
            patch_name = patch_name * ( patch_name < 128)
            patch_name = patch_name.tostring().decode('ascii')
            
            if(self.debug):
                print("Processing {}:{} ...".format(i,patch_name),end='')
            
            if(my_filter(patch) == True):
                if(subsample_ratio!= None):
                    if(np.random.rand() < subsample_ratio):
                        self.patches = np.append(self.patches,patch)
                else:
                    self.patches = np.append(self.patches,patch)

        #Reshape patches
        patch_byte_count = self.patches.size
        n_patches = patch_byte_count // dxs.DX7_VOICE_SIZE_PACKED
        self.patches = self.patches.reshape((n_patches, dxs.DX7_VOICE_SIZE_PACKED)).astype(np.uint8)
        # Store synthesis parameters
        self.notes = np.asarray(valid_notes)
        self.velocities = np.asarray(valid_velocities)
        self.note_on_len = note_on_len
        self.note_off_len = note_off_len
        print("Starting with {} patches. \n\tnotes: {} \tvelocities: {} \n\
        sample_rate: {} Hz \tnote_on_len: {} \tnote_off_len: {}".format(n_patches,self.notes,self.velocities,sample_rate,self.note_on_len,self.note_off_len))
        
    def __len__(self):
        n_notes = self.notes.size
        n_velocities = self.velocities.size
        n_patches = self.patches.shape[0]
        return n_notes * n_velocities * n_patches

    def __getitem__(self, idx: int):
        # Obtain patch number,note and velocity from idx
        n_notes = self.notes.size
        n_velocities = self.velocities.size
        n_patches = self.patches.shape[0]
        idx_note = idx % (n_notes)
        idx //= (n_notes)
        idx_velocity =  idx % (n_velocities)
        idx //= (n_velocities)
        idx_patch = idx
        
        if(self.debug): print("idx_patch {} idx_note {} idx_velocity {} ".format(idx_patch,idx_note,idx_velocity))
        patch = self.patches[idx_patch:idx_patch+1,:] #Wrapper expects array with 2D shape
        note = self.notes[idx_note]
        velocity = self.velocities[idx_velocity]
        x = self.synth.synthesize(patch,note,velocity,self.note_on_len,self.note_off_len)
        y = self.unpack_packed_patch(patch[0])
        y = np.asarray(y,dtype=np.float32)
        #Extract name
        z = y[145:155]
        #REMOVE PATCH NAME AND OP ON/OFF
        y = y[0:145]
        return {'audio': x, 'patch': y,'name': z}
    
    def filter_get_all_op_ratio(self,patch):
        # Check that all OP work in OSC MODE = ratio = 0.
        # Is done verifying each OSC MODE BIT for every patch.
        idx = 15 # OP6 ratio data is at byte 15
        check = np.uint8(0x00)
        for i in range(6):
            check = ( check | patch[idx] ) & 0x01
            idx +=17 #Advance next OP

        if(check == 0x00):
            return True

        return False
    
    def filter_get_all_op_fixed(self,patch):
        # Check that all OP work in OSC MODE = ratio = 0.
        # Is done verifying each OSC MODE BIT for every patch.
        idx = 15 # OP6 ratio data is at byte 15
        check = np.uint8(0x00)
        for i in range(6):
            check = ( check | (not (patch[idx] & 0x01 ) ) ) & 0x01
            idx +=17 #Advance next OP

        if(check == 0x00):
            return True
        
        return False
    def filter_allpass(self,patch):
        return True

    # Nice unpacking method extracted from https://github.com/bwhitman/learnfm
    def unpack_packed_patch(self,p):
        # Input is a 128 byte thing from compact.bin
        # Output is a 156 byte thing that the synth knows about
        o = [0]*156
        for op in range(6):
            o[op*21:op*21 + 11] = p[op*17:op*17+11]
            leftrightcurves = p[op*17+11]
            o[op * 21 + 11] = leftrightcurves & 3
            o[op * 21 + 12] = (leftrightcurves >> 2) & 3
            detune_rs = p[op * 17 + 12]
            o[op * 21 + 13] = detune_rs & 7
            o[op * 21 + 20] = detune_rs >> 3
            kvs_ams = p[op * 17 + 13]
            o[op * 21 + 14] = kvs_ams & 3
            o[op * 21 + 15] = kvs_ams >> 2
            o[op * 21 + 16] = p[op * 17 + 14]
            fcoarse_mode = p[op * 17 + 15]
            o[op * 21 + 17] = fcoarse_mode & 1
            o[op * 21 + 18] = fcoarse_mode >> 1
            o[op * 21 + 19] = p[op * 17 + 16]
    
        o[126:126+9] = p[102:102+9]
        oks_fb = p[111]
        o[135] = oks_fb & 7
        o[136] = oks_fb >> 3
        o[137:137+4] = p[112:112+4]
        lpms_lfw_lks = p[116]
        o[141] = lpms_lfw_lks & 1
        o[142] = (lpms_lfw_lks >> 1) & 7
        o[143] = lpms_lfw_lks >> 4
        o[144:144+11] = p[117:117+11]
        o[155] = 0x3f #Seems that OP ON/OFF they are always on. Ignore.

        # Clamp the unpacked patches to a known max. 
        maxes =  [
            99, 99, 99, 99, 99, 99, 99, 99, 99, 99, 99, # osc6
            3, 3, 7, 3, 7, 99, 1, 31, 99, 14,
            99, 99, 99, 99, 99, 99, 99, 99, 99, 99, 99, # osc5
            3, 3, 7, 3, 7, 99, 1, 31, 99, 14,
            99, 99, 99, 99, 99, 99, 99, 99, 99, 99, 99, # osc4
            3, 3, 7, 3, 7, 99, 1, 31, 99, 14,
            99, 99, 99, 99, 99, 99, 99, 99, 99, 99, 99, # osc3
            3, 3, 7, 3, 7, 99, 1, 31, 99, 14,
            99, 99, 99, 99, 99, 99, 99, 99, 99, 99, 99, # osc2
            3, 3, 7, 3, 7, 99, 1, 31, 99, 14,
            99, 99, 99, 99, 99, 99, 99, 99, 99, 99, 99, # osc1
            3, 3, 7, 3, 7, 99, 1, 31, 99, 14,
            99, 99, 99, 99, 99, 99, 99, 99, # pitch eg rate & level 
            31, 7, 1, 99, 99, 99, 99, 1, 5, 7, 48, # algorithm etc
            126, 126, 126, 126, 126, 126, 126, 126, 126, 126, # name
            127 # operator on/off
        ]
        for i in range(156):
            if(o[i] > maxes[i]): o[i] = maxes[i]
            if(o[i] < 0): o[i] = 0
        return o
