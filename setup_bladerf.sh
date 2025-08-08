#!/bin/bash

echo "[*] Installing BladeRF Python bindings..."

# Install pip dependencies first
pip install -r requirements.txt

# Clone and install BladeRF Python bindings
echo "[*] Cloning BladeRF repository..."
git clone https://github.com/Nuand/bladeRF.git /tmp/bladeRF

# Install Python bindings
echo "[*] Installing Python bindings..."
cd /tmp/bladeRF/host/libraries/libbladeRF_bindings/python
python setup.py install

echo "[*] Setup complete!"
echo "[*] You can now run the transmission scripts."