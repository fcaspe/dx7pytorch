'''
DX7 pytorch dataset test. Loads the synthesizer and generates 50 samples of 2s
'''

import numpy as np
from dx7pytorch import DXDataset
import torch.utils.data as data
import torch

sr = 48000
collection_path = '../dataset/collection.bin'
dataset = DXDataset(sr,
    collection_path,
    valid_notes=[i for i in range(12,70,1)],
    valid_velocities=[i for i in range(1,99,1)],
    note_on_len= sr,
    note_off_len=sr,
    subsample_ratio = 0.1,
    transpose_extra = -12)

n_train_examples = int(len(dataset)*0.7)
n_valid_examples = int(len(dataset)*0.2)
n_test_examples =  len(dataset) - n_train_examples - n_valid_examples

train_data, valid_data, test_data = torch.utils.data.random_split(dataset, 
    [n_train_examples, n_valid_examples, n_test_examples])

train_loader = data.DataLoader(train_data,batch_size = 4, shuffle = True)


print("Dataset length: {}. Read 50 synthesized batches. . .".format(len(train_data)+len(valid_data)+len(test_data)))

i = 0
for instance in train_loader:
    if(i==50): break
    i = i + 1
    note = instance['audio'] #Retrieve audio
    print(instance['name'])
    note = note.numpy()
    # Ensure that highest value is in 16-bit range
    for j in range(note.shape[0]):
        instance_max = np.max(np.abs(note[j,:,:]))
        if instance_max != 0.0:
            audio = note[j,:,:] * (2**15 - 1) / instance_max
        # Convert to 16-bit data
        audio = audio.astype(np.int16)

print("Done.")