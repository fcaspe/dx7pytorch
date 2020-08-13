echo "[INFO] Downloading patch compilation . . ."
wget http://bobbyblues.recup.ch/yamaha_dx7/patches/DX7_AllTheWeb.zip
unzip DX7_AllTheWeb.zip

mkdir all_patches
echo "[INFO] Searching for all DX7 patch files  . . ."
find ./DX7_AllTheWeb -name '*.SYX' -exec mv -f {} ./all_patches/ \;
find ./DX7_AllTheWeb -name '*.syx' -exec mv -f {} ./all_patches/ \;
echo "[INFO] Packing patches onto a single file. This may take a while. . . "
python3 patchpacker.py ./all_patches

echo "[INFO] Cleaning up . . ."
rm -f DX7_AllTheWeb.zip
rm -r -f all_patches
rm -r -f DX7_AllTheWeb
echo "[INFO] Done! You should have a new collection.bin file! "