#!/usr/bin/env python3

import numpy as np
import bladerf
from bladerf import _bladerf
import signal
import sys
import time

# Config settings - change these as needed
FREQUENCY_MHZ = 1176.45  # L5 band center freq
BANDWIDTH_MHZ = 2.0
SAMPLE_RATE_MSPS = 5.0
TX_GAIN_DB = 60  # max

# BladeRF needs Hz not MHz
FREQUENCY_HZ = int(FREQUENCY_MHZ * 1e6)
BANDWIDTH_HZ = int(BANDWIDTH_MHZ * 1e6)
SAMPLE_RATE_HZ = int(SAMPLE_RATE_MSPS * 1e6)

# flag for ctrl-c handling
running = True

def signal_handler(sig, frame):
    global running
    print("\n[*] Stopping transmission...")
    running = False

def generate_white_noise(num_samples):
    """Generate complex white noise samples at maximum amplitude"""
    # generate random IQ data at full scale
    # 12-bit DAC so we use nearly the whole range
    i_samples = np.random.randint(-2047, 2048, num_samples, dtype=np.int16)
    q_samples = np.random.randint(-2047, 2048, num_samples, dtype=np.int16)
    
    # scale down just a tiny bit to avoid clipping
    i_samples = (i_samples * 0.95).astype(np.int16)
    q_samples = (q_samples * 0.95).astype(np.int16)
    
    # interleave IQ for bladerf's expected format
    samples = np.empty(2 * num_samples, dtype=np.int16)
    samples[0::2] = i_samples
    samples[1::2] = q_samples
    
    return samples

def main():
    print(f"[*] BladeRF White Noise Transmitter")
    print(f"[*] Frequency: {FREQUENCY_MHZ} MHz")
    print(f"[*] Bandwidth: {BANDWIDTH_MHZ} MHz")
    print(f"[*] Sample Rate: {SAMPLE_RATE_MSPS} MSPS")
    print(f"[*] TX Gain: {TX_GAIN_DB} dB")
    print(f"[*] Press Ctrl+C to stop\n")
    
    # catch ctrl-c gracefully
    signal.signal(signal.SIGINT, signal_handler)
    
    dev = None
    try:
        # connect to the bladerf
        dev = _bladerf.BladeRF()
        print(f"[*] Opened BladeRF: {dev.board_name}")
        
        # tx channel 0
        channel = _bladerf.CHANNEL_TX(0)
        
        # tune to target freq
        dev.set_frequency(channel, FREQUENCY_HZ)
        actual_freq = dev.get_frequency(channel)
        print(f"[*] Set frequency to {actual_freq/1e6:.2f} MHz")
        
        # set sampling rate
        dev.set_sample_rate(channel, SAMPLE_RATE_HZ)
        actual_rate = dev.get_sample_rate(channel)
        print(f"[*] Set sample rate to {actual_rate/1e6:.2f} MSPS")
        
        # filter bandwidth
        dev.set_bandwidth(channel, BANDWIDTH_HZ)
        actual_bw = dev.get_bandwidth(channel)
        print(f"[*] Set bandwidth to {actual_bw/1e6:.2f} MHz")
        
        # max out the tx power
        # check what gain stages we have
        gain_stages = dev.get_gain_stages(channel)
        print(f"[*] Available gain stages: {gain_stages}")
        
        # set main gain
        dev.set_gain(channel, TX_GAIN_DB)
        actual_gain = dev.get_gain(channel)
        print(f"[*] Set TX gain to {actual_gain} dB")
        
        # configure each gain stage
        for stage in gain_stages:
            try:
                # DSA is an attenuator so 0 = max power output
                if 'dsa' in stage.lower():
                    dev.set_gain_stage(channel, stage, 0)
                    print(f"[*] Set {stage} to 0 (minimum attenuation = maximum power)")
                else:
                    dev.set_gain_stage(channel, stage, 60)  # max for amplifier stages
                    print(f"[*] Set {stage} to maximum")
            except:
                pass
        
        # try to enable bias tee for external amp power
        try:
            dev.set_bias_tee(channel, True)
            print("[*] Bias tee enabled for maximum power")
        except:
            print("[*] Bias tee not available or not needed")
        
        # setup streaming params
        num_buffers = 16
        buffer_size = 8192
        num_transfers = 8
        timeout_ms = 3500
        
        dev.sync_config(layout=_bladerf.ChannelLayout.TX_X1,
                       fmt=_bladerf.Format.SC16_Q11,
                       num_buffers=num_buffers,
                       buffer_size=buffer_size,
                       num_transfers=num_transfers,
                       stream_timeout=timeout_ms)
        
        # turn on transmitter
        dev.enable_module(channel, True)
        print("[*] TX channel enabled")
        
        # pre-generate noise for speed
        num_samples = buffer_size
        noise_buffer = generate_white_noise(num_samples)
        
        print("[*] Starting transmission...")
        print("[*] Transmitting white noise... (Press Ctrl+C to stop)")
        
        # tx loop
        while running:
            # blast the noise
            dev.sync_tx(noise_buffer, timeout_ms)
            
            # refresh noise buffer occasionally
            if np.random.randint(0, 100) == 0:
                noise_buffer = generate_white_noise(num_samples)
            
            # tiny sleep to not hammer CPU
            time.sleep(0.001)
        
    except _bladerf.BladeRFError as e:
        print(f"[!] BladeRF Error: {e}")
        return 1
    except Exception as e:
        print(f"[!] Error: {e}")
        return 1
    finally:
        if dev:
            try:
                # shut down tx
                channel = _bladerf.CHANNEL_TX(0)
                dev.enable_module(channel, False)
                print("[*] TX channel disabled")
                
                # disconnect
                dev.close()
                print("[*] BladeRF closed")
            except:
                pass
    
    print("[*] Shutdown complete")
    return 0

if __name__ == "__main__":
    sys.exit(main())