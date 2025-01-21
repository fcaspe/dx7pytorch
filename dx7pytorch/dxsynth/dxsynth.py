import os
import platform
import ctypes
import numpy as np
import numpy.ctypeslib as npct
from ctypes import cdll

# dx7 sysex format: https://homepages.abdn.ac.uk/d.j.benson/pages/dx7/sysex-format.txt
# Constants for DX7
DX7_DUMP_SIZE_VOICE_BULK = 4096 + 8
DX7_VOICE_SIZE_PACKED = 128


def open_bulk_patches(filename, selection=None):
    """
    Load and return patches from a SysEx bulk file.

    :param filename: Path to the SysEx bulk file.
    :param selection: Indices of patches to select. If None, return all patches.
    :return: Selected patches as a NumPy array.
    """
    if selection is None:
        selection = range(32)
    selection = np.asarray(selection)

    sysex_bulk = np.fromfile(filename, dtype=np.uint8)
    if sysex_bulk.size != DX7_DUMP_SIZE_VOICE_BULK:
        raise ValueError(
            f"ERROR: Sysex bulk should be {DX7_DUMP_SIZE_VOICE_BULK} bytes. "
            f"{filename} is {sysex_bulk.size} bytes."
        )

    patches = sysex_bulk[6:6 + 4096].reshape((32, DX7_VOICE_SIZE_PACKED))
    return patches[selection, :]


class DXSynth:
    def __init__(self, sampling_frequency):
        """
        Initialize the DX7 Synth with the specified sampling frequency.

        :param sampling_frequency: The sampling frequency for the synthesizer.
        """
        # Determine the shared library path based on the OS
        system = platform.system().lower()
        lib_extension = {"windows": "dll", "darwin": "dylib"}.get(system, "so")
        lib_name = f"dxcore.{lib_extension}"

        # Build the full path to the shared library
        my_path = os.path.dirname(os.path.abspath(__file__))
        dll_path = os.path.join(my_path, '../../', lib_name)

        if not os.path.exists(dll_path):
            raise FileNotFoundError(f"Shared library not found at {dll_path}")

        # Load the shared library
        self.lib = cdll.LoadLibrary(dll_path)

        # Initialize the synthesizer library
        hexter_init = self.lib.hexter_init
        hexter_init.restype = ctypes.POINTER(ctypes.c_ubyte)
        hexter_init.argtypes = [ctypes.c_long, ctypes.POINTER(ctypes.c_ubyte)]

        # Define other library functions
        self.do_run_synth = self.lib.synthesize
        self.do_run_synth.argtypes = [ctypes.POINTER(ctypes.c_ubyte),
                                      ctypes.POINTER(ctypes.c_float),
                                      ctypes.c_long, ctypes.c_long]

        self.do_note_on = self.lib.hexter_instance_note_on
        self.do_note_on.argtypes = [ctypes.POINTER(ctypes.c_ubyte), ctypes.c_ubyte, ctypes.c_ubyte]

        self.do_note_off = self.lib.hexter_instance_note_off
        self.do_note_off.argtypes = [ctypes.POINTER(ctypes.c_ubyte), ctypes.c_ubyte, ctypes.c_ubyte]

        self.do_program_change = self.lib.hexter_instance_select_program
        self.do_program_change.argtypes = [ctypes.POINTER(ctypes.c_ubyte), ctypes.c_ubyte, ctypes.c_ubyte]

        self.do_reset = self.lib.reset_synth
        self.do_reset.argtypes = [ctypes.POINTER(ctypes.c_ubyte)]

        self.do_patch_pack = self.lib.dx7_patch_pack
        self.do_patch_pack.argtypes = [ctypes.POINTER(ctypes.c_ubyte),
                                       ctypes.POINTER(ctypes.c_ubyte), ctypes.c_ubyte]

        # Patch buffer for patches
        self.patch_buffer = np.ascontiguousarray(
            np.zeros((128, DX7_VOICE_SIZE_PACKED), dtype=np.uint8)
        )
        self.patch_buffer_pointer = self.patch_buffer.ctypes.data_as(ctypes.POINTER(ctypes.c_ubyte))

        # Initialize hexter
        self.instance = hexter_init(np.uint32(sampling_frequency), self.patch_buffer_pointer)

    def note_on(self, note, velocity):
        self.do_note_on(self.instance, note.astype(np.uint8), velocity.astype(np.uint8))

    def note_off(self, note, velocity):
        self.do_note_off(self.instance, note.astype(np.uint8), velocity.astype(np.uint8))

    def program_change(self, program):
        self.do_program_change(self.instance, 0, program)

    def run_synth(self, output, sample_start, sample_end):
        output_pointer = output.ctypes.data_as(ctypes.POINTER(ctypes.c_float))
        self.do_run_synth(self.instance, output_pointer, sample_start, sample_end)

    def reset_synth(self):
        self.do_reset(self.instance)

    def pack_patch(self, in_patch):
        packed = np.zeros(128, dtype=np.uint8)
        unpacked = np.zeros(155, dtype=np.uint8)
        unpacked[0:145] = in_patch
        packed_pointer = packed.ctypes.data_as(ctypes.POINTER(ctypes.c_ubyte))
        unpacked_pointer = unpacked.ctypes.data_as(ctypes.POINTER(ctypes.c_ubyte))
        self.do_patch_pack(unpacked_pointer, packed_pointer, 0)
        return packed

    def synthesize(self, patches, notes, velocities, nsamples_noteon, nsamples_noteoff):
        notes = np.asarray(notes)
        velocities = np.asarray(velocities)
        ninstances = patches.shape[0]

        if notes.size not in (1, ninstances):
            raise ValueError(f"ERROR: Notes shape {notes.size} is unexpected!")
        if velocities.size not in (1, ninstances):
            raise ValueError("ERROR: Velocity shape is unexpected!")

        nsamples = nsamples_noteon + nsamples_noteoff
        self.patch_buffer[0:ninstances, :] = patches

        x = np.zeros((ninstances, nsamples), dtype=np.float32)
        if notes.size == 1:
            notes = np.tile(notes, ninstances)
        if velocities.size == 1:
            velocities = np.tile(velocities, ninstances)

        for i in range(ninstances):
            self.reset_synth()
            self.program_change(i)
            self.note_on(notes[i], velocities[i])
            self.run_synth(x[i, :], 0, nsamples_noteon)
            self.note_off(notes[i], velocities[i])
            self.run_synth(x[i, :], nsamples_noteon, nsamples)

        return x

    def __del__(self):
        self.lib.hexter_clean_and_exit(self.instance)
