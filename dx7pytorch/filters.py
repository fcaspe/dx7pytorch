import numpy as np

def filter_operator_frequencies_are_ratio(patch):
    '''
    Check that all operators work in OSC MODE = ratio = 0.
    This is done by verifying each OSC MODE BIT for each patch.
    '''
    idx = 15 # OP6 ratio data is at byte 15
    check = np.uint8(0x00)
    for i in range(6):
        check = ( check | patch[idx] ) & 0x01
        idx +=17 #Advance next OP

    if(check == 0x00):
        return True

    return False

def filter_operator_frequencies_are_fixed(patch):
    '''
    Check that all operators work in OSC MODE = fixed = 1.
    This is done by verifying each OSC MODE BIT for each patch.
    '''
    idx = 15 # OP6 ratio data is at byte 15
    check = np.uint8(0x00)
    for i in range(6):
        check = ( check | (not (patch[idx] & 0x01 ) ) ) & 0x01
        idx +=17 #Advance next OP

    if(check == 0x00):
        return True
    
    return False

def filter_none(patch):
    return True
