'''
Concealed Information Test Results Plotting Script

This script averages the P300 responses to each colour, and plots the results.
'''

import pyxdf
import numpy as np
import matplotlib.pyplot as plt
from scipy import signal

# CHANGE THIS TO YOUR FILE PATH
file_path = r"C:\..."

EEG_STREAM_NAME    = 'Custom_ESP32_EEG'
MARKER_STREAM_NAME = 'CIT_Visual_Markers'

# Channels to plot
CHANNELS = [
     (0, 'Cz'),
    # (1, 'Fz'),
    # (2, 'Pz'),
]

FS = 500.0   # sampling rate (Hz)

T_PRE  = -0.2
T_POST =  0.8
LOW_FREQ  = 0.5
HIGH_FREQ = 30.0
NOTCH_FREQ = 50.0
ARTIFACT_THRESHOLD_UV = 100.0
P300_WINDOW = (0.30, 0.60)

# Color categories
PROBE_COLOR  = "Green"
TARGET_COLOR = "Yellow"
IRRELEVANT_COLORS = ["Red", "Blue", "Cyan", "Purple"]

# Plotting colors (tweaked slightly so they show up nicely on a white background)
PLOT_COLORS = {
    "Red":    '#D62728', 
    "Yellow": '#D4AF37',  
    "Green":  '#2CA02C',
    "Blue":   '#1F77B4',
    "Purple": '#9467BD',
    "Cyan":   '#17BECF'
}

# Load the recorded file
print("Loading XDF file...")
data, header = pyxdf.load_xdf(file_path)

eeg_stream = None
marker_stream = None
for stream in data:
    if stream['info']['name'][0] == EEG_STREAM_NAME:
        eeg_stream = stream
    elif stream['info']['name'][0] == MARKER_STREAM_NAME:
        marker_stream = stream

if eeg_stream is None or marker_stream is None:
    print("Error: Could not find both EEG and Marker streams. Check stream names.")
    exit()

# Process EEG Data
print("Filtering EEG data...")
eeg_times = np.array(eeg_stream['time_stamps'])
eeg_data  = np.array(eeg_stream['time_series'])

b_notch, a_notch = signal.iirnotch(w0=NOTCH_FREQ, Q=30.0, fs=FS)
b_band,  a_band  = signal.butter(N=4, Wn=[LOW_FREQ, HIGH_FREQ], btype='bandpass', fs=FS)

filtered = np.zeros_like(eeg_data, dtype=float)
for ch in range(eeg_data.shape[1]):
    x = signal.filtfilt(b_notch, a_notch, eeg_data[:, ch])
    x = signal.filtfilt(b_band,  a_band,  x)
    filtered[:, ch] = x

# Sort markers by color
marker_times  = np.array(marker_stream['time_stamps'])
marker_labels = np.array([m[0] for m in marker_stream['time_series']])

# Group times by color
color_times = {color: [] for color in PLOT_COLORS.keys()}
for t, label in zip(marker_times, marker_labels):
    if label in color_times:
        color_times[label].append(t)

# Epoching
samples_pre  = int(abs(T_PRE)  * FS)
samples_post = int(T_POST * FS)
epoch_time_vector = np.linspace(T_PRE, T_POST, samples_pre + samples_post)

def extract_epochs(stim_times, channel_signal):
    accepted = []
    for t in stim_times:
        idx = np.argmin(np.abs(eeg_times - t))
        start = idx - samples_pre
        end   = idx + samples_post
        if start < 0 or end >= len(channel_signal):
            continue
        ep = channel_signal[start:end].copy()
        ep -= np.mean(ep[:samples_pre]) # Baseline correct
        if np.max(np.abs(ep)) <= ARTIFACT_THRESHOLD_UV: # Artifact rejection
            accepted.append(ep)
    return np.array(accepted)

# Plot Data ------------------------------------------------------------------------------------------------------------
plt.rcParams['font.family'] = 'serif'
plt.rcParams['font.serif']  = ['Georgia']
inc = 4

n_chan = len(CHANNELS)
fig1, axes1 = plt.subplots(n_chan, 1, figsize=(15, 6 * n_chan), dpi=100, squeeze=False)
fig2, axes2 = plt.subplots(n_chan, 1, figsize=(15, 6 * n_chan), dpi=100, squeeze=False)
fig1.set_facecolor('#FFFFFF')
fig2.set_facecolor('#FFFFFF')

for ax_row, (ch_idx, ch_name) in enumerate(CHANNELS):
    ax1 = axes1[ax_row, 0]
    ax2 = axes2[ax_row, 0]
    ch_signal = filtered[:, ch_idx]

    # Extract epochs for all 6 colors
    epochs_dict = {}
    print(f"\n{ch_name} Epochs Accepted:")
    for color, times in color_times.items():
        epochs = extract_epochs(times, ch_signal)
        epochs_dict[color] = epochs
        print(f"  {color}: {len(epochs)} / {len(times)}")

    # Figure 1: All 6 colours
    for color, epochs in epochs_dict.items():
        if len(epochs) > 0:
            mean_wave = epochs.mean(axis=0)
            
            # Make Probe and Target thicker lines
            linewidth = 3.5 if color in [PROBE_COLOR, TARGET_COLOR] else 2
            alpha = 1.0 if color in [PROBE_COLOR, TARGET_COLOR] else 0.7
            label_suffix = " (Probe)" if color == PROBE_COLOR else " (Target)" if color == TARGET_COLOR else ""
            
            ax1.plot(epoch_time_vector, mean_wave, color=PLOT_COLORS[color], 
                     linewidth=linewidth, alpha=alpha, label=f"{color}{label_suffix} (n={len(epochs)})")

    ax1.axvline(x=0, color='black', linestyle='--', linewidth=1.5, alpha=0.7)
    ax1.axvspan(P300_WINDOW[0], P300_WINDOW[1], color='gray', alpha=0.1, label='P300 Window')
    ax1.set_title(f"Grand Average ERP Response for each Colour ({ch_name})", fontsize=16+inc, fontweight='bold')
    ax1.set_xlabel("Time (s)", fontsize=13+inc)
    ax1.set_ylabel("Amplitude (µV)", fontsize=13+inc)
    ax1.legend(loc='upper right')
    ax1.grid(True, linestyle='--', alpha=0.5)
    ax1.tick_params(labelsize=11+inc)

    # Figure 2: Aggregate irrelvants together
    irrelevant_epochs_list = [epochs_dict[c] for c in IRRELEVANT_COLORS if len(epochs_dict[c]) > 0]
    
    if len(irrelevant_epochs_list) > 0 and len(epochs_dict[PROBE_COLOR]) > 0 and len(epochs_dict[TARGET_COLOR]) > 0:
        all_irrelevant = np.vstack(irrelevant_epochs_list)
        
        groups = {
            "Irrelevant Average": (all_irrelevant, 'gray', 0.2),
            f"Target ({TARGET_COLOR})": (epochs_dict[TARGET_COLOR], PLOT_COLORS[TARGET_COLOR], 0.2),
            f"Probe/Lie ({PROBE_COLOR})": (epochs_dict[PROBE_COLOR], PLOT_COLORS[PROBE_COLOR], 0.2)
        }

        for name, (eps, color, fill_alpha) in groups.items():
            n = len(eps)
            mean_w = eps.mean(axis=0)
            sem_w  = eps.std(axis=0) / np.sqrt(n)
            
            ax2.fill_between(epoch_time_vector, mean_w - sem_w, mean_w + sem_w, color=color, alpha=fill_alpha)
            ax2.plot(epoch_time_vector, mean_w, color=color, linewidth=2.5, label=f"{name} (n={n})")

    ax2.axvline(x=0, color='black', linestyle='--', linewidth=1.5, alpha=0.7)
    ax2.axvspan(P300_WINDOW[0], P300_WINDOW[1], color='gray', alpha=0.1, label='P300 Window')
    ax2.set_title(f"Grand Average ERP Response for Target, Probe and Irrelevant Stimuli ({ch_name})", fontsize=16, fontweight='bold')
    ax2.set_xlabel("Time (s)", fontsize=13)
    ax2.set_ylabel("Amplitude (µV)", fontsize=13)
    ax2.legend(loc='upper right')
    ax2.grid(True, linestyle='--', alpha=0.5)

fig1.tight_layout()
fig2.tight_layout()
plt.show()