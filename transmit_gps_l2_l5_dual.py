#!/usr/bin/env python3

import numpy as np
import bladerf
from bladerf import _bladerf
import signal
import sys
import time

# dual band config
FREQ1_MHZ = 1227.60  # L2 
FREQ2_MHZ = 1176.45  # L5 
BANDWIDTH_MHZ = 2.0
SAMPLE_RATE_MSPS = 5.0
TX_GAIN_L2_DB = 60  # L2
TX_GAIN_L5_DB = 60  # L5

# convert to Hz since thats what bladerf wants
FREQ1_HZ = int(FREQ1_MHZ * 1e6)
FREQ2_HZ = int(FREQ2_MHZ * 1e6)
BANDWIDTH_HZ = int(BANDWIDTH_MHZ * 1e6)
SAMPLE_RATE_HZ = int(SAMPLE_RATE_MSPS * 1e6)

# for clean exit
running = True

def signal_handler(sig, frame):
    global running
    print("\n[*] Stopping dual-band transmission...")
    running = False

def generate_white_noise(num_samples):
    """Generate white noise at max amplitude"""
    # full scale IQ samples
    i_samples = np.random.randint(-2047, 2048, num_samples, dtype=np.int16)
    q_samples = np.random.randint(-2047, 2048, num_samples, dtype=np.int16)
    
    # scale slightly to avoid clipping
    i_samples = (i_samples * 0.95).astype(np.int16)
    q_samples = (q_samples * 0.95).astype(np.int16)
    
    # interleave for bladerf
    samples = np.empty(2 * num_samples, dtype=np.int16)
    samples[0::2] = i_samples
    samples[1::2] = q_samples
    
    return samples

def configure_channel(dev, channel_idx, freq_hz, gain_db, name):
    """Setup a single tx channel"""
    channel = _bladerf.CHANNEL_TX(channel_idx)
    
    # tune to frequency
    dev.set_frequency(channel, freq_hz)
    actual_freq = dev.get_frequency(channel)
    print(f"[*] {name}: Set frequency to {actual_freq/1e6:.2f} MHz")
    
    # sample rate
    dev.set_sample_rate(channel, SAMPLE_RATE_HZ)
    actual_rate = dev.get_sample_rate(channel)
    print(f"[*] {name}: Set sample rate to {actual_rate/1e6:.2f} MSPS")
    
    # bandwidth
    dev.set_bandwidth(channel, BANDWIDTH_HZ)
    actual_bw = dev.get_bandwidth(channel)
    print(f"[*] {name}: Set bandwidth to {actual_bw/1e6:.2f} MHz")
    
    # set channel-specific gain
    dev.set_gain(channel, gain_db)
    actual_gain = dev.get_gain(channel)
    print(f"[*] {name}: Set TX gain to {actual_gain} dB")
    
    # get gain stages and max them out
    gain_stages = dev.get_gain_stages(channel)
    for stage in gain_stages:
        try:
            if 'dsa' in stage.lower():
                # DSA is attenuator, 0 = max power
                dev.set_gain_stage(channel, stage, 0)
                print(f"[*] {name}: Set {stage} to 0 (max power)")
            else:
                dev.set_gain_stage(channel, stage, 60)
        except:
            pass
    
    # try bias tee for external amp
    try:
        dev.set_bias_tee(channel, True)
        print(f"[*] {name}: Bias tee enabled")
    except:
        pass
    
    return channel

def main():
    print(f"[*] BladeRF Dual-Band GPS Jammer")
    print(f"[*] Band 1: L2 @ {FREQ1_MHZ} MHz")
    print(f"[*] Band 2: L5 @ {FREQ2_MHZ} MHz")
    print(f"[*] Bandwidth: {BANDWIDTH_MHZ} MHz per channel")
    print(f"[*] TX Gain: L2={TX_GAIN_L2_DB}dB, L5={TX_GAIN_L5_DB}dB")
    print(f"[*] Press Ctrl+C to stop\n")
    
    signal.signal(signal.SIGINT, signal_handler)
    
    dev = None
    try:
        # open device
        dev = _bladerf.BladeRF()
        print(f"[*] Opened BladeRF: {dev.board_name}")
        
        # setup both channels
        print("\n[*] Configuring Channel 0 (L2)...")
        ch0 = configure_channel(dev, 0, FREQ1_HZ, TX_GAIN_L2_DB, "CH0/L2")
        
        print("\n[*] Configuring Channel 1 (L5)...")
        ch1 = configure_channel(dev, 1, FREQ2_HZ, TX_GAIN_L5_DB, "CH1/L5")
        
        # configure sync interface for dual channel
        num_buffers = 16
        buffer_size = 8192
        num_transfers = 8
        timeout_ms = 3500
        
        # TX_X2 for dual channel operation
        dev.sync_config(layout=_bladerf.ChannelLayout.TX_X2,
                       fmt=_bladerf.Format.SC16_Q11,
                       num_buffers=num_buffers,
                       buffer_size=buffer_size,
                       num_transfers=num_transfers,
                       stream_timeout=timeout_ms)
        
        print("\n[*] Sync interface configured for dual TX")
        
        # enable both tx channels
        dev.enable_module(ch0, True)
        dev.enable_module(ch1, True)
        print("[*] Both TX channels enabled")
        
        # pre-generate noise buffers
        print("[*] Generating noise buffers...")
        # for dual channel, we need interleaved samples: ch0_i, ch0_q, ch1_i, ch1_q
        # so double the buffer size to accommodate both channels
        dual_buffer_size = buffer_size * 2
        
        print("\n[*] Starting dual-band transmission...")
        print("[*] Transmitting on L2 and L5 simultaneously... (Press Ctrl+C to stop)")
        
        # main tx loop
        while running:
            # generate fresh noise for both channels
            noise_ch0 = generate_white_noise(buffer_size)
            noise_ch1 = generate_white_noise(buffer_size)
            
            # interleave both channels for TX_X2 format
            # format: [ch0_i, ch0_q, ch1_i, ch1_q, ...]
            dual_samples = np.empty(dual_buffer_size * 2, dtype=np.int16)
            dual_samples[0::4] = noise_ch0[0::2]  # ch0 I
            dual_samples[1::4] = noise_ch0[1::2]  # ch0 Q
            dual_samples[2::4] = noise_ch1[0::2]  # ch1 I
            dual_samples[3::4] = noise_ch1[1::2]  # ch1 Q
            
            # transmit on both channels
            dev.sync_tx(dual_samples, timeout_ms)
            
            # tiny sleep
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
                # disable both channels
                dev.enable_module(_bladerf.CHANNEL_TX(0), False)
                dev.enable_module(_bladerf.CHANNEL_TX(1), False)
                print("[*] Both TX channels disabled")
                
                dev.close()
                print("[*] BladeRF closed")
            except:
                pass
    
    print("[*] Shutdown complete")
    return 0

if __name__ == "__main__":
    sys.exit(main())