'''
P300 Results Plotting Script

This script loads the XDF file recorded during the P300 test script, averages the time series 
response to the target and standard tones, and plots the results with shaded error bars.
'''

import pyxdf
import numpy as np
import matplotlib.pyplot as plt
from scipy import signal

# CHANGE THIS TO YOUR FILE PATH
file_path = r"C:\..."

EEG_STREAM_NAME    = 'Custom_ESP32_EEG'
MARKER_STREAM_NAME = 'P300_Markers'

# Channels to plot
CHANNELS = [
     (0, 'Cz'),
    # (1, 'Fz'),
    # (2, 'Pz'),
]

FS = 500.0   # sampling rate (Hz)

# Epoch window
T_PRE  = -0.2
T_POST =  0.8

# Filter passband
LOW_FREQ  = 0.5
HIGH_FREQ = 20.0
NOTCH_FREQ = 50.0

# Artifact rejection
ARTIFACT_THRESHOLD_UV = 100.0

# Window in which to look for the P300 peak.
P300_WINDOW = (0.3, 0.60)

# Load the recorded file
data, header = pyxdf.load_xdf(file_path)

eeg_stream = None
marker_stream = None
for stream in data:
    if stream['info']['name'][0] == EEG_STREAM_NAME:
        eeg_stream = stream
    elif stream['info']['name'][0] == MARKER_STREAM_NAME:
        marker_stream = stream

if eeg_stream is None or marker_stream is None:
    print("Error: Could not find both EEG and Marker streams in the XDF file.")
    exit()

# Process EEG Data
eeg_times = np.array(eeg_stream['time_stamps'])
eeg_data  = np.array(eeg_stream['time_series'])

b_notch, a_notch = signal.iirnotch(w0=NOTCH_FREQ, Q=30.0, fs=FS)
b_band,  a_band  = signal.butter(N=4, Wn=[LOW_FREQ, HIGH_FREQ], btype='bandpass', fs=FS)

filtered = np.zeros_like(eeg_data, dtype=float)
for ch in range(eeg_data.shape[1]):
    x = signal.filtfilt(b_notch, a_notch, eeg_data[:, ch])
    x = signal.filtfilt(b_band,  a_band,  x)
    filtered[:, ch] = x

# Sort markers into target & standard
marker_times  = np.array(marker_stream['time_stamps'])
marker_labels = np.array([m[0] for m in marker_stream['time_series']])

target_times   = marker_times[marker_labels == 'target']
standard_times = marker_times[marker_labels == 'standard']
print(f"Markers found: {len(target_times)} targets, "f"{len(standard_times)} standards")

# Epoching
samples_pre  = int(abs(T_PRE)  * FS)
samples_post = int(T_POST * FS)
epoch_time_vector = np.linspace(T_PRE, T_POST, samples_pre + samples_post)

def extract_epochs(stim_times, channel_signal):
    accepted = []
    n_rejected = 0
    n_outofbounds = 0
    for t in stim_times:
        idx = np.argmin(np.abs(eeg_times - t))
        start = idx - samples_pre
        end   = idx + samples_post
        if start < 0 or end >= len(channel_signal):
            n_outofbounds += 1
            continue
        ep = channel_signal[start:end].copy()
        ep -= np.mean(ep[:samples_pre])             # baseline correct
        if np.max(np.abs(ep)) > ARTIFACT_THRESHOLD_UV:
            n_rejected += 1
            continue
        accepted.append(ep)
    return np.array(accepted), n_rejected, n_outofbounds



# Plot Data ------------------------------------------------------------------------------------------------------------
plt.rcParams['font.family'] = 'serif'
plt.rcParams['font.serif']  = ['Georgia']

n_chan = len(CHANNELS)
fig, axes = plt.subplots(n_chan, 1, figsize=(15, 6 * n_chan), dpi=100, squeeze=False)
fig.set_facecolor('#FFFFFF')
inc = 4

for ax_row, (ch_idx, ch_name) in enumerate(CHANNELS):
    ax = axes[ax_row, 0]
    ch_signal = filtered[:, ch_idx]

    target_epochs,   n_t_rej, _ = extract_epochs(target_times,   ch_signal)
    standard_epochs, n_s_rej, _ = extract_epochs(standard_times, ch_signal)

    n_t = len(target_epochs)
    n_s = len(standard_epochs)
    print(f"\n{ch_name}:")
    print(f"  Targets:   {n_t} accepted, {n_t_rej} rejected")
    print(f"  Standards: {n_s} accepted, {n_s_rej} rejected")

    if n_t == 0 or n_s == 0:
        ax.text(0.5, 0.5, f"No accepted epochs at {ch_name}",
                transform=ax.transAxes, ha='center', va='center', fontsize=14)
        continue

    target_mean   = target_epochs.mean(axis=0)
    target_sem    = target_epochs.std(axis=0)   / np.sqrt(n_t)
    standard_mean = standard_epochs.mean(axis=0)
    standard_sem  = standard_epochs.std(axis=0) / np.sqrt(n_s)

    # Standard wave
    ax.fill_between(epoch_time_vector,
                    standard_mean - standard_sem,
                    standard_mean + standard_sem,
                    color='#3157F7', alpha=0.15)
    ax.plot(epoch_time_vector, standard_mean,
            color='#3157F7', linewidth=2.5,
            label=f'Standard (n={n_s})')

    # Target wave
    ax.fill_between(epoch_time_vector,
                    target_mean - target_sem,
                    target_mean + target_sem,
                    color='#E74C3C', alpha=0.20)
    ax.plot(epoch_time_vector, target_mean,
            color='#E74C3C', linewidth=3,
            label=f'Target (n={n_t})')

    # Stimulus onset
    ax.axvline(x=0, color='black', linestyle='--', linewidth=1.5, alpha=0.7, label='Tone onset')

    # P300 window
    ax.axvspan(P300_WINDOW[0], P300_WINDOW[1], color='gray', alpha=0.1, label='Expected P300 window')

    # Find target peak
    in_window = ((epoch_time_vector >= P300_WINDOW[0]) &
                 (epoch_time_vector <= P300_WINDOW[1]))
    rel_idx = np.argmax(target_mean[in_window])
    abs_idx = np.where(in_window)[0][rel_idx]
    peak_t  = epoch_time_vector[abs_idx]
    peak_uv = target_mean[abs_idx]

    # ax.plot(peak_t, peak_uv, 'o', color='#D62728',
    #         markersize=10, markerfacecolor='none', markeredgewidth=2)
    # ax.annotate(f'  Peak: {peak_uv:.2f} µV @ {peak_t*1000:.0f} ms',
    #             xy=(peak_t, peak_uv),
    #             xytext=(peak_t + 0.04, peak_uv),
    #             fontsize=11, va='center')

    ax.set_title(f"Auditory Oddball P300 Recorded from {ch_name}", fontsize=16+inc, fontweight='bold', pad=12)
    ax.set_xlabel("Time relative to tone onset (s)", fontsize=13+inc, labelpad=8)
    ax.set_ylabel("Amplitude (µV)", fontsize=13+inc, labelpad=8)
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.yaxis.grid(True, linestyle='--', alpha=0.7)
    ax.xaxis.grid(True, linestyle='--', alpha=0.3)
    ax.tick_params(labelsize=11+inc)
    ax.set_xlim(T_PRE, T_POST)
    ax.legend(fontsize=11+inc, loc='upper right')

plt.tight_layout()
plt.show()