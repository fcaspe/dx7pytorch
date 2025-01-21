'''
DX7 pytorch dataset test. Loads the synthesizer and generates 50 samples of 2s @16kHz

You can install the pip 'simpleaudio' package and uncomment the audio lines
to hear the synthesized samples.
'''

# FOR UNBUFFERED OUTPUT run: export PYTHONUNBUFFERED=1

import numpy as np
from dx7pytorch.dxdataset import DXDataset
import torch.utils.data as data
import torch
import simpleaudio as sa #UNCOMMENT FOR AUDIO LISTENING

dataset = DXDataset(16000 ,'../dataset/collection.bin',
                           (48,50),(127,),16000,16000,subsample_ratio = 0.1,random_seed=1234,filter_function='all_ratio',debug=False)

n_train_examples = int(len(dataset)*0.7)
n_valid_examples = int(len(dataset)*0.2)
n_test_examples =  len(dataset) - n_train_examples - n_valid_examples

train_data, valid_data, test_data = torch.utils.data.random_split(dataset, 
                                                       [n_train_examples, n_valid_examples, n_test_examples])

train_loader = data.DataLoader(train_data,batch_size = 32,shuffle = True)


print("Dataset length: {}. \nNow iterating to read 50 synthesized batches. . .".format(len(train_data)+len(valid_data)+len(test_data)))

i = 0
for instance in train_loader:
    if(i==50): break
    i = i + 1
    note = instance['audio'] #Retrieve audio
    note = note.numpy()
    # Ensure that highest value is in 16-bit range
    for j in range(note.shape[0]):
        instance_max = np.max(np.abs(note[j,:,:]))
        if instance_max != 0.0:
            audio = note[j,:,:] * (2**15 - 1) / instance_max
        # Convert to 16-bit data
        audio = audio.astype(np.int16)
        # Start playback
        play_obj = sa.play_buffer(audio, 1, 2, 16000) #UNCOMMENT FOR AUDIO LISTENING

        # Wait for playback to finish before exiting
        play_obj.wait_done()                          #UNCOMMENT FOR AUDIO LISTENING

print("Done.")