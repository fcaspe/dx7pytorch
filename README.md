# dx7pytorch

A Pytorch FM Synthesizer for your audio deep learning projects!

## Intent

Music instrument datasets are scarce and usually very large, composed by thousands of very small files, being difficult to handle and of limited versatility. 
**dx7pytorch** addresses this problem by bundling an <a href="https://en.wikipedia.org/wiki/Frequency_modulation_synthesis" target="_blank"> FM Synthesizer</a> core into a Pytorch dataset wrapper. 

The synthesizer core is a C++ emulator of the famous <a href="http://www.vintagesynth.com/yamaha/dx7.php" target="_blank">Yamaha DX7</a>, a programmable digital instrument for which
rich and varied timbres can be created by manipulating its internal parameters. Each combination of parameters is called **patch** and describes a particular timbre. 

There exist thousands of patches for this instrument. Included in the repo there is a download script that compiles a large collection of patches (140k) which can be synthesized into sound
samples at any **note** or **velocity**. Hence, the dataset only requires to store patch information, occupying only a couple of Megabytes.

## Features

- On-the-fly audio synthesis with full MIDI **note** and **velocity** support.
- Selectable **sampling frequency**.
- Arbitrary **instance lenght**.
- Annotation is automatically generated (fundamental frequency, velocity, patch vector).

## How do I use it?

**dx7pytorch** in 4 simple steps!

![](img/dx7pytorch.png)

1. In your Pytorch script, create an instance of the **dx7pytorch** dataset class, specifying:
    * Patch collection's path.
    * MIDI note and velocity range to synthesize.
    * Sampling frequency and Instance length.
    * The use of a patch filter if desired.
1. Use the dataset interface or a Pytorch *dataloader* to request audio instances.
    * A specific MIDI note and velocity within the specified range is sent to the synthesizer.
1. The audio samples are generated on-the-fly, every time a request is received.
1. The Pytorch wrapper can additionally deliver MIDI annotation or patch information.

## Try it!

1. Install this Python package: 
    ```
    pip3 install git+https://github.com/fcaspe/dx7pytorch
    ```
1. We now need a DX7 patch dataset compiled onto a single file. Go to the **dataset** directory and try:
    ```
    source download_dataset.sh
    ```
1. Now, check out the **tests** directory at this repo!

## Acknowledgements
- The synthesizer core of **dx7pytorch** is based in the <a href="https://github.com/smbolton/hexter" target="_blank">Hexter</a> DX7 emulator. Licensed under GPL-2.0
- DX7 Patch collection extracted from <a href="http://bobbyblues.recup.ch/yamaha_dx7/dx7_patches.html" target="_blank">Bobby Blues</a> webpage.
