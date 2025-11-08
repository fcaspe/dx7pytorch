import numpy as np

def filter_get_all_op_ratio(patch):
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

def filter_get_all_op_fixed(patch):
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

def filter_allpass(patch):
    return True
