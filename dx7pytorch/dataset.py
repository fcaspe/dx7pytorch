from torch.utils import data
import numpy as np
from dx7pytorch import DX7_VOICE_SIZE_PACKED, DXSynth
from dx7pytorch.filters import filter_allpass
from os import path


class DXDataset(data.Dataset):
    """DX7 sound patch dataset."""

    #define chord dictionaries as class vars
    BASE_CHORDS = {
        #triads 
        'maj': [0,4,7], 
        'min': [0,3,7], 
        'dim': [0,3,6], 
        'aug': [0,4,8], 
        'sus2': [0,2,7], 
        'sus4': [0,5,7], 

        #seventh chords
        'maj7': [0,4,7,11], 
        'dom7': [0,4,7,10], 
        'min7': [0,3,7,10], 
        'min7b5': [0,3,6,10], 
        'dim7': [0,3,6,9], 
        '7sus4': [0,5,7,10], 

        #extended chords
        'maj9': [0,4,7,11,14], 
        'min9': [0,3,7,10,14], 
        'dom9': [0,4,7,10,14], 
        'domsharp9': [0,4,7,10,15], 
        'domflat9': [0,4,7,10,13], 
    }

    ARTIST_VOICINGS = {
        #specific voicings, no inversions here
        #k.barron, k.jarrett, b.evans
        'min11_barron': [0, 7, 14, 15, 22, 29],  # 1, 5, 9, m3, 11, m7
        'maj_sharp11_barron': [0, 7, 14, 16, 18, 23], #1, 5, 9, M3, #11 , M7
        'min11_jarrett': [7,12,15,17,22,26,31], #5, 1, m3, 11, m7, 9, 5
        'maj9_evans_sowhat': [4,9,14,19,23], #M3, 6, 9, 5, M7
    }

    def __init__(self, sample_rate:int,
            collection:str, 
            valid_notes, 
            valid_velocities,
            note_on_len:int,
            note_off_len:int,
            subsample_ratio=None,
            random_seed=None,
            filter_function=None,
            chord_probability=0.5):
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
            chord_probability (float): Probability of generating chords vs single notes (0.0 to 1.0).
            
        """
        np.random.seed(random_seed)
        #self.debug = debug
        
        #Instantiate Synthesizer
        self.synth = DXSynth(sampling_frequency=sample_rate)
        
        #print("dx7pytorch: FM Synthesizer for deep learning. Loading dataset . . . ")
        
        patch_file = path.abspath(collection)
        
        # Open file list to process patches. 
        # I think the easiest way is to store everythig in RAM, to minimize disk access.
        self.patches = np.empty(0)
        
        bulk_patches = np.fromfile(patch_file, dtype=np.uint8)
        n_patches = int(len(bulk_patches)/DX7_VOICE_SIZE_PACKED)
        #if(self.debug): print("[DEBUG] Total patches: {}".format(n_patches))
        
        if filter_function is None:
            my_filter = filter_allpass
        else:
            my_filter = filter_function
        
        for i in range(n_patches):
            patch = bulk_patches[i*128:(i+1)*128]
            
            # Process Patch Name. Keep only names below 128 and decode to ascii.
            patch_name = patch[118:127]
            patch_name = patch_name * ( patch_name < 128)
            patch_name = patch_name.tobytes().decode('ascii')
            
            #if(self.debug):
            #    print("Processing {}:{} ...".format(i,patch_name),end='')
            
            if(my_filter(patch) == True):
                if(subsample_ratio!= None):
                    if(np.random.rand() < subsample_ratio):
                        self.patches = np.append(self.patches,patch)
                else:
                    self.patches = np.append(self.patches,patch)

        #Reshape patches
        patch_byte_count = self.patches.size
        n_patches = patch_byte_count // DX7_VOICE_SIZE_PACKED
        self.patches = self.patches.reshape((n_patches, DX7_VOICE_SIZE_PACKED)).astype(np.uint8)
        # Store synthesis parameters
        self.valid_notes = np.asarray(valid_notes)
        self.valid_velocities = np.asarray(valid_velocities)
        self.note_on_len = note_on_len
        self.note_off_len = note_off_len
        #print("Starting with {} patches. \n\tnotes: {} \tvelocities: {} \n\
        #sample_rate: {} Hz \tnote_on_len: {} \tnote_off_len: {}".format(n_patches,self.valid_notes,self.valid_velocities,sample_rate,self.note_on_len,self.note_off_len))
        
        #generate chord voicings
        self.chord_voicings = self._generate_all_chord_voicings()
        self.chord_probability = chord_probability
        
        #pre-determine which indices will be chords
        total_items = self.__len__()
        np.random.seed(random_seed if random_seed else 42)
        self.is_chord = np.random.rand(total_items) < chord_probability
        
        print(f"Generated {len(self.chord_voicings)} chord voicings")
        print(f"Dataset will use {chord_probability*100}% chords")
        
    def _generate_inversions(self, chord_name, intervals):
        """Generate inversions for a chord without bass notes"""
        result = {}
        
        #root position
        result[chord_name] = intervals
        
        #create each inversion
        for inversion_num in range(1, len(intervals)):
            #notes from inversion_num
            high_notes = intervals[inversion_num:]
            
            #take the first notes and shift them an octave up
            low_notes = [note + 12 for note in intervals[:inversion_num]]
            
            #combine
            inverted = high_notes + low_notes
            
            #save
            result[f"{chord_name}_inv{inversion_num}"] = inverted
        
        return result
    
    def _generate_all_chord_voicings(self):
        """Generate all chord voicings with inversions"""
        voicings = {}
        
        #generate inversions for base chords
        for chord_name, intervals in self.BASE_CHORDS.items():
            voicings.update(self._generate_inversions(chord_name, intervals))
        
        #artistic-specific voicings remain as is
        voicings.update(self.ARTIST_VOICINGS)
        
        return voicings
        
    def __len__(self):
        n_notes = self.valid_notes.size
        n_velocities = self.valid_velocities.size
        n_patches = self.patches.shape[0]
        return n_notes * n_velocities * n_patches

    def __getitem__(self, idx: int):
        # Obtain patch number, note and velocity from idx
        n_notes = self.valid_notes.size
        n_velocities = self.valid_velocities.size
        n_patches = self.patches.shape[0]
        idx_note = idx % (n_notes)
        temp_idx = idx // (n_notes)
        idx_velocity = temp_idx % (n_velocities)
        idx_patch = temp_idx // (n_velocities)
        
        #print("idx_patch {} idx_note {} idx_velocity {} ".format(idx_patch,idx_note,idx_velocity))
        patch = self.patches[idx_patch:idx_patch+1,:] #Wrapper expects array with 2D shape
        velocity = self.valid_velocities[idx_velocity]
        
        # check if this index should be a chord
        if self.is_chord[idx]:
            # pick a chord based on idx
            chord_list = list(self.chord_voicings.items())
            chord_idx = idx % len(chord_list)
            chord_name, intervals = chord_list[chord_idx]
            
            # use note from idx as root
            root_note = self.valid_notes[idx_note]
            chord_notes = [root_note + interval for interval in intervals]
            
            # filter out notes that are too high (>127) or too low (<0)
            chord_notes = [n for n in chord_notes if 0 <= n <= 127]
            
            # synthesise chord using mixing approach
            x = self.synth.synthesise_chord(patch, chord_notes, velocity, 
                                           self.note_on_len, self.note_off_len)
            
            y = self.unpack_packed_patch(patch[0])
            y = np.asarray(y, dtype=np.float32)
            
            #name extraction
            patch_name = bytearray()
            for p in y[145:155]:
                p = int(p) & 0x7F
                patch_name.append(p)
            patch_name = patch_name.decode('ascii')
            
            #REMOVE PATCH NAME AND OP ON/OFF
            y = y[0:145]
            
            return {
                'audio': x,
                'patch': y,
                'name': patch_name,
                'note': root_note,  #root note
                'velocity': velocity,
                'chord': chord_name  #chord type
            
            }
        else:
            # original single note behavior
            note = self.valid_notes[idx_note]
            x = self.synth.synthesize(patch, note, velocity, 
                                     self.note_on_len, self.note_off_len)
            
            y = self.unpack_packed_patch(patch[0])
            y = np.asarray(y, dtype=np.float32)
            
            #extract name
            patch_name = bytearray()
            for p in y[145:155]:
                p = int(p) & 0x7F
                patch_name.append(p)
            patch_name = patch_name.decode('ascii')
            
            #REMOVE PATCH NAME AND OP ON/OFF
            y = y[0:145]
            
            return {
                'audio': x,
                'patch': y,
                'name': patch_name,
                'note': note,
                'velocity': velocity,
                'chord': ''  #empty string instead of None for single notes
                # Removed chord_notes - it causes batching issues
            }

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
