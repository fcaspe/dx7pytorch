import ctypes
import numpy.ctypeslib as npct
import numpy as np
from ctypes import cdll

'''
Extracted from: https://homepages.abdn.ac.uk/d.j.benson/pages/dx7/sysex-format.txt

SYSEX Message: Bulk Data for 32 Voices
--------------------------------------
       bits    hex  description

     11110000  F0   Status byte - start sysex
     0iiiiiii  43   ID # (i=67; Yamaha)
     0sssnnnn  00   Sub-status (s=0) & channel number (n=0; ch 1)
     0fffffff  09   format number (f=9; 32 voices)
     0bbbbbbb  20   byte count MS byte
     0bbbbbbb  00   byte count LS byte (b=4096; 32 voices)
     0ddddddd  **   data byte 1

        |       |       |

     0ddddddd  **   data byte 4096  (there are 128 bytes / voice)
     0eeeeeee  **   checksum (masked 2's comp. of sum of 4096 bytes)
     11110111  F7   Status - end sysex

'''
DX7_DUMP_SIZE_VOICE_BULK = 4096+8
DX7_VOICE_SIZE_PACKED = 128

# FUNCTION TO GET 32VOICE BULK DUMP FROM SYSEX (32X128 BYTES) (THIS FORMAT IS GOOD FOR LOADING PATCHES INTO SYNTH)
# FUNCTION TO UNPACK 128BYTES VOICE TO 155 (Disentangle it, transform to a vector which is easier to train)

def open_bulk_patches(filename,selection=None):
    ''' filename: string
        selection: number of patches to pick. 
            selection == none, return all patches
    '''
    if(selection == None):
        selection = range(32)
        
    selection = np.asarray(selection)
    sysex_bulk = np.fromfile(filename, dtype=np.uint8)
    if(sysex_bulk.size != DX7_DUMP_SIZE_VOICE_BULK):
        raise ValueError("ERROR: Sysex bulk should be {} bytes. {} is {} bytes.".format(DX7_DUMP_SIZE_VOICE_BULK,filename,sysex_bulk.size))
        
    patches = sysex_bulk[6:6+4096]
    patches = patches.reshape((32,DX7_VOICE_SIZE_PACKED))
    return patches[selection,:]
    

class dxsynth:
    def __init__(self, sampling_frequency):
        '''Doc - __init__ Constructor'''
        import os
        # We expect the synth lib is installed two directories up.
        MY_PATH = os.path.dirname(os.path.abspath(__file__))
        dll_path = os.path.join(MY_PATH, '../../dxcore.so')
        self.lib = cdll.LoadLibrary(dll_path)
        self.lib = cdll.LoadLibrary('dxcore.so')
        hexter_init = self.lib.hexter_init
        hexter_init.restype = ctypes.POINTER(ctypes.c_ubyte)
        hexter_init.argtypes = [ctypes.c_long, ctypes.POINTER(ctypes.c_ubyte)]
        
        # Synthesizer function IF declaration.
        self.do_run_synth = self.lib.synthesize
        self.do_run_synth.argtypes = [ctypes.POINTER(ctypes.c_ubyte),ctypes.POINTER(ctypes.c_float),ctypes.c_long,ctypes.c_long]
        
        self.do_note_on = self.lib.hexter_instance_note_on
        self.do_note_on.argtypes = [ctypes.POINTER(ctypes.c_ubyte),ctypes.c_ubyte,ctypes.c_ubyte]
        
        self.do_note_off = self.lib.hexter_instance_note_off
        self.do_note_off.argtypes = [ctypes.POINTER(ctypes.c_ubyte),ctypes.c_ubyte,ctypes.c_ubyte]
        
        self.do_program_change = self.lib.hexter_instance_select_program
        self.do_program_change.argtypes = [ctypes.POINTER(ctypes.c_ubyte),ctypes.c_ubyte,ctypes.c_ubyte]
        
        self.do_reset = self.lib.reset_synth
        self.do_reset.argtypes = [ctypes.POINTER(ctypes.c_ubyte)]
        
        self.do_patch_pack = self.lib.dx7_patch_pack
        self.do_patch_pack.argtypes = [ctypes.POINTER(ctypes.c_ubyte),ctypes.POINTER(ctypes.c_ubyte),ctypes.c_ubyte]
        
        self.patch_buffer = np.ascontiguousarray( np.zeros((128,DX7_VOICE_SIZE_PACKED),dtype=np.uint8) )
        self.patch_buffer_pointer = self.patch_buffer.ctypes.data_as(ctypes.POINTER(ctypes.c_ubyte))

        # INIT HEXTER
        self.instance = hexter_init(np.uint32(sampling_frequency),self.patch_buffer_pointer)
    
    def note_on(self,note,velocity):
        self.do_note_on(self.instance,note.astype(np.uint8),velocity.astype(np.uint8))

    def note_off(self,note,velocity):
        self.do_note_off(self.instance,note.astype(np.uint8),velocity.astype(np.uint8))
    
    def program_change(self,program):
        self.do_program_change(self.instance,0,program)

    def run_synth(self,output,sample_start,sample_end):
        output_pointer = output.ctypes.data_as(ctypes.POINTER(ctypes.c_float)) #c_float is 4 bytes.
        #print("Pointer is {:02x}".format(output.ctypes.data))
        self.do_run_synth(self.instance,output_pointer,sample_start,sample_end)
    
    def reset_synth(self):
        self.do_reset(self.instance)
    
    def pack_patch(self,in_patch):
        packed = np.zeros(128,dtype=np.uint8)
        unpacked = np.zeros(155,dtype=np.uint8)
        unpacked[0:145] = in_patch
        packed_pointer = packed.ctypes.data_as(ctypes.POINTER(ctypes.c_ubyte))
        unpacked_pointer = unpacked.ctypes.data_as(ctypes.POINTER(ctypes.c_ubyte))
        self.do_patch_pack(unpacked_pointer,packed_pointer,0)
        return packed
    
    def synthesize(self,patches,notes,velocities,nsamples_noteon,nsamples_noteoff):
        ''' patches shape (N_INSTANCES X DX7_VOICE_SIZE_PACKED)
            notes shape (1) or (N_INSTANCES x 1)
            velocity shape (1) or (N_INSTANCES x 1)'''
        notes = np.asarray(notes)
        velocities = np.asarray(velocities)

        ninstances = patches.shape[0]
        if(not (notes.size == 1 or notes.size == ninstances)):
            raise ValueError("ERROR: Notes shape {} is unexpected!.".format(notes.size))
        if(not (velocities.size == 1 or velocities.size == ninstances)):
            raise ValueError("ERROR: Velocity shape unexpected!.")            
        nsamples = nsamples_noteon + nsamples_noteoff
        
        #print("synthesize() patches_shape: {} notes: {} velocity: {} noteon_len {} noteoff_len {}".\
        #    format(patches.shape,notes,velocities,nsamples_noteon,nsamples_noteoff))
        
        #Copy patches
        self.patch_buffer[0:ninstances,:] = patches
        #print("ninstances: {} copying patches".format(ninstances))
        #Create buffer to put data in
        x = np.zeros((ninstances,nsamples),dtype=np.float32) #np.float32 is 4 bytes but np.float is 8 bytes long!
        
        # Generate the notes to play
        if(notes.size == 1):
            notes = np.tile(notes,ninstances)

        # Generate the notes to play
        if(velocities.size == 1):
            velocities = np.tile(velocities,ninstances)
        
        # Call synthesizer library functions.
        for i in range(ninstances):
            #Reset LFOs and stop all voices.
            self.reset_synth()
            self.program_change(i)
            
            self.note_on(notes[i],velocities[i])
            self.run_synth(x[i,:],0,nsamples_noteon)
            
            self.note_off(notes[i],velocities[i])
            self.run_synth(x[i,:],nsamples_noteon,nsamples_noteon+nsamples_noteoff)

        return x

    def __del__(self):
        self.lib.hexter_clean_and_exit(self.instance)
