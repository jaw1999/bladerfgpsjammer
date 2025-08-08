# BladeRF GPS Jammer 

Testing suite for GPS signal disruption using BladeRF xA9 SDR.


## Hardware Requirements
- BladeRF xA9 SDR 
- Host computer with USB 3.0

## Software Prerequisites

### System Dependencies
```bash
# Ubuntu/Debian
sudo apt-get update
sudo apt-get install libbladerf-dev libbladerf2 bladerf
```

### Python Setup

Easy setup with script:
```bash
# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Run setup script - installs everything including BladeRF bindings
chmod +x setup_bladerf.sh
./setup_bladerf.sh
```

Or manual setup:
```bash
source venv/bin/activate
pip install -r requirements.txt
# Then manually install BladeRF Python bindings from source
```

## Quick Start

### Single Band Jamming
Each script targets a specific GPS band:

```bash
# L1 Band - 1575.42 MHz 
python transmit_gps_l1.py

# L2 Band - 1227.60 MHz 
python transmit_gps_l2.py

# L5 Band - 1176.45 MHz 
python transmit_gps_l5.py
```

### Dual Band Jamming
Simultaneous transmission on two bands (power is split):

```bash
# L1 + L2 combo
python transmit_gps_l1_l2_dual.py

# L1 + L5 combo
python transmit_gps_l1_l5_dual.py

# L2 + L5 combo
python transmit_gps_l2_l5_dual.py
```

**Note:** Dual mode splits power between channels, resulting in weaker signals per band.

## Configuration

Default settings (edit at top of each script):
- **Bandwidth:** 2 MHz per channel
- **Sample Rate:** 5 MSPS
- **TX Gain:** 60 dB (maximum)
- **Signal Type:** White noise

### Adjusting Power Levels
```python
# In script headers
TX_GAIN_DB = 60  # Range: -15 to 60 dB
```

### Frequency Adjustment
```python
# Modify at top of scripts
FREQUENCY_MHZ = 1575.42  # Your target frequency
```

## Technical Details

### GPS Bands
- **L1:** 1575.42 MHz - Used by all consumer GPS devices
- **L2:** 1227.60 MHz - Military P(Y) code + Civilian L2C
- **L5:** 1176.45 MHz - Newest civilian band, higher precision

### Power Output
- Maximum gain: 60 dB
- Output power: ~20 dBm (100mW) at max gain
- Lower frequencies (L5/L2) naturally output more power than L1

### Signal Generation
- Generates pseudo-random noise at full DAC scale
- 12-bit I/Q samples (SC16_Q11 format)
- Continuous transmission until interrupted

## Troubleshooting

### BladeRF Not Found
```bash
# Check device connection
bladeRF-cli -p

# Add udev rules if needed
sudo wget https://www.nuand.com/fpga/88-nuand-bladerf.rules -O /etc/udev/rules.d/88-nuand-bladerf.rules
sudo udevadm control --reload-rules
```

### FPGA Version Warning
This warning is normal and can be ignored:
```
[INFO @ host/libraries/libbladeRF/src/helpers/version.c:103] FPGA version (v0.16.0) is newer than entries...
```
### Weak L1 Signal
L1 (1575 MHz) has naturally lower power output than L2/L5. This is a hardware characteristic of the BladeRF amplifier chain.

### Python Import Errors
Ensure BladeRF Python bindings are properly installed:
```bash
python -c "import bladerf; print('Success')"
```
## Stop Transmission
Press `Ctrl+C` to cleanly stop any running script.

## Project Structure
```
├── README.md                    # This file
├── requirements.txt             # Python dependencies
├── setup_bladerf.sh            # BladeRF setup helper
├── transmit_gps_l1.py          # L1 band jammer
├── transmit_gps_l2.py          # L2 band jammer
├── transmit_gps_l5.py          # L5 band jammer
├── transmit_gps_l1_l2_dual.py  # Dual L1+L2
├── transmit_gps_l1_l5_dual.py  # Dual L1+L5
└── transmit_gps_l2_l5_dual.py  # Dual L2+L5
```

## Disclaimer
This software is provided for educational and research purposes only. Users are solely responsible for compliance with all applicable laws and regulations. The authors assume no liability for misuse or damage caused by this software.
