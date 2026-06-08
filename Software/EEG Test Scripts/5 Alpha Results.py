'''
Alpha Wave Results Plotting Script

This script loads XDF file recorded during the Alpha Wave test script, and plots the time and 
frequency domain results with eyes closed vs eyes open.

Frequency domain results are plotted using Welch's method to remove noise.
'''

import pyxdf
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
from scipy import signal

#  Load the recorded file (REPLACE WITH YOUR FILE PATH)
file_path = r"C:\..."
data, header = pyxdf.load_xdf(file_path)

eeg_stream = None
marker_stream = None

# Separate the streams 
for stream in data:
    if stream['info']['name'][0] == 'Custom_ESP32_EEG':
        eeg_stream = stream
    elif stream['info']['name'][0] == 'AlphaMarkers':
        marker_stream = stream

if eeg_stream is None or marker_stream is None:
    print("Error: Could not find both EEG and Marker streams in the XDF file.")
    exit()

eeg_times = np.array(eeg_stream['time_stamps'])
eeg_data = np.array(eeg_stream['time_series'])

# Extract Channels 1, 2, and 3 
ch_raw_all = eeg_data[:, 0:3] 

fs = 500.0  

# Filters
b_notch, a_notch = signal.iirnotch(w0=50.0, Q=30.0, fs=fs)
ch_notched = signal.filtfilt(b_notch, a_notch, ch_raw_all, axis=0)

b_band, a_band = signal.butter(N=4, Wn=[1.0, 50.0], btype='bandpass', fs=fs)
ch_filtered = signal.filtfilt(b_band, a_band, ch_notched, axis=0)

ch_names = ['Ch1 (Oz)', 'Ch2 (O1)', 'Ch3 (O2)']
ch_colors = ['#E74C3C', '#2ECC71', '#3157F7'] 
ch_colors = ['#3157F7', '#2ECC71', '#E74C3C'] 

# Process Markers 
marker_times = np.array(marker_stream['time_stamps'])
marker_labels = [m[0] for m in marker_stream['time_series']]

t_eo1_start = marker_times[marker_labels.index('Eyes_Open_1_Start')]
t_eo1_end = marker_times[marker_labels.index('Eyes_Open_1_End')]
t_ec_start = marker_times[marker_labels.index('Eyes_Closed_Start')]
t_ec_end = marker_times[marker_labels.index('Eyes_Closed_End')]
t_eo2_start = marker_times[marker_labels.index('Eyes_Open_2_Start')]
t_eo2_end = marker_times[marker_labels.index('Eyes_Open_2_End')]

# Normalize times
time_offset = eeg_times[0]
eeg_times -= time_offset
t_eo1_start -= time_offset
t_eo1_end -= time_offset
t_ec_start -= time_offset
t_ec_end -= time_offset
t_eo2_start -= time_offset
t_eo2_end -= time_offset

# PSD Function
def get_stage_data(start_t, end_t):
    mask = (eeg_times >= start_t) & (eeg_times <= end_t)
    t_sliced = eeg_times[mask]
    data_sliced = ch_filtered[mask, :] 
    freqs, psd = signal.welch(data_sliced, fs=fs, nperseg=int(fs*2), axis=0)
    return t_sliced, data_sliced, freqs, psd

t_eo1, d_eo1, f_eo1, p_eo1 = get_stage_data(t_eo1_start, t_eo1_end)
t_ec, d_ec, f_ec, p_ec = get_stage_data(t_ec_start, t_ec_end)
t_eo2, d_eo2, f_eo2, p_eo2 = get_stage_data(t_eo2_start, t_eo2_end)

# Change to True to use Phase 1. Change to False to use Phase 3.
use_phase_1 = False

if use_phase_1:
    baseline_title = "Eyes Open"
    t_base, d_base, f_base, p_base = t_eo1, d_eo1, f_eo1, p_eo1
else:
    baseline_title = "Eyes Open"
    t_base, d_base, f_base, p_base = t_eo2, d_eo2, f_eo2, p_eo2



# Plot Data ------------------------------------------------------------------------------------------------------------
plt.rcParams['font.family'] = 'serif'
plt.rcParams['font.serif'] = ['Georgia']

fig1, axs = plt.subplots(2, 2, figsize=(18, 10), dpi=100)
fig1.set_facecolor('#F2F2F2')
fig1.set_facecolor('#FFFFFF')

# Top Left: Time Domain, Baseline (Oz Only)
axs[0, 0].plot(t_base, d_base[:, 0], color=ch_colors[0], linewidth=1.2)
axs[0, 0].set_title(f"Time Series (Oz) with Eyes Open", fontsize=16, fontweight='bold', pad=15)
axs[0, 0].set_ylabel("Amplitude (µV)", fontsize=14)
axs[0, 0].set_xlabel("Time (Seconds)", fontsize=14)

# Top Right: Time Domain, Eyes Closed (Oz Only)
axs[0, 1].plot(t_ec, d_ec[:, 0], color=ch_colors[0], linewidth=1.2)
axs[0, 1].set_title("Time Series (Oz) with Eyes Closed", fontsize=16, fontweight='bold', pad=15)
axs[0, 1].set_ylabel("Amplitude (µV)", fontsize=14)
axs[0, 1].set_xlabel("Time (Seconds)", fontsize=14)

# Bottom Left: Welch PSD, Baseline (All Channels)
for ch_idx in range(3):
    axs[1, 0].plot(f_base, p_base[:, ch_idx], color=ch_colors[ch_idx], linewidth=2.0, alpha=0.85, label=ch_names[ch_idx])
axs[1, 0].set_title(f"Power Spectral Density (Welch) with Eyes Open", fontsize=16, fontweight='bold', pad=15)
axs[1, 0].set_ylabel("Power (µV²/Hz)", fontsize=14)
axs[1, 0].set_xlabel("Frequency (Hz)", fontsize=14)
axs[1, 0].set_xlim(0, 30)
axs[1, 0].axvspan(8, 12, color='#3157F7', alpha=0.1, label='Alpha Band')
axs[1, 0].legend(fontsize=10, loc='upper right')
axs[1, 0].xaxis.set_minor_locator(ticker.MultipleLocator(1))

# Bottom Right: Welch PSD, Eyes Closed (All Channels)
for ch_idx in range(3):
    axs[1, 1].plot(f_ec, p_ec[:, ch_idx], color=ch_colors[ch_idx], linewidth=2.0, alpha=0.85, label=ch_names[ch_idx])
axs[1, 1].set_title("Power Spectral Density (Welch) with Eyes Closed", fontsize=16, fontweight='bold', pad=15)
axs[1, 1].set_ylabel("Power (µV²/Hz)", fontsize=14)
axs[1, 1].set_xlabel("Frequency (Hz)", fontsize=14)
axs[1, 1].set_xlim(0, 30)
axs[1, 1].axvspan(8, 12, color='#3157F7', alpha=0.1, label='Alpha Band')
axs[1, 1].legend(fontsize=10, loc='upper right')
axs[1, 1].xaxis.set_minor_locator(ticker.MultipleLocator(1))

# Apply aesthetics to all subplots
for row in range(2):
    for col in range(2):
        axs[row, col].spines['top'].set_visible(False)
        axs[row, col].spines['right'].set_visible(False)
        axs[row, col].yaxis.grid(True, linestyle='--', alpha=0.7)
        axs[row, col].xaxis.grid(False)
        axs[row, col].tick_params(labelsize=12)

axs[1,1].yaxis.grid(False)
axs[1,1].xaxis.grid(True, linestyle='-', alpha=0.7)
axs[1,1].grid(which='minor', axis='x', linestyle='-', linewidth=0.4, alpha=0.4)
axs[1,0].yaxis.grid(False)
axs[1,0].xaxis.grid(True, linestyle='-', alpha=0.7)
axs[1,0].grid(which='minor', axis='x', linestyle='-', linewidth=0.4, alpha=0.4)

fig1.tight_layout()

# # FIGURE 2: Spectrogram (Phase 1 & 2)
# spec_channel_idx = 0 

# # Extract data from the start of Phase 1 to the end of Phase 2
# full_mask = (eeg_times >= t_eo1_start) & (eeg_times <= t_ec_end)
# t_full = eeg_times[full_mask]
# data_full = ch_filtered[full_mask, spec_channel_idx] 

# f_spec, t_spec, Sxx = signal.spectrogram(data_full, fs=fs, nperseg=int(fs*2), noverlap=int(fs*1.8))
# t_spec += t_full[0]

# Pxx_dB = 10 * np.log10(Sxx)
# vmin = 0 #np.percentile(Pxx_dB, 5)
# vmax = 20 #np.percentile(Pxx_dB, 95)

# fig2, ax_spec = plt.subplots(figsize=(16, 6), dpi=100)
# fig2.set_facecolor('#F2F2F2')

# mesh = ax_spec.pcolormesh(t_spec, f_spec, Pxx_dB, shading='gouraud', cmap='jet', vmin=vmin, vmax=vmax)

# ax_spec.set_title(f"Spectrogram (Eyes Open to Eyes Closed) - {ch_names[spec_channel_idx]}", fontsize=18, fontweight='bold', pad=15)
# ax_spec.set_ylabel("Frequency (Hz)", fontsize=14)
# ax_spec.set_xlabel("Time (Seconds)", fontsize=14)
# ax_spec.set_ylim(0, 30)

# ax_spec.axvline(x=t_ec_start, color='white', linestyle='-', linewidth=2, label='Eyes Closed')

# ax_spec.legend(loc='upper right', fontsize=12)

# cbar = fig2.colorbar(mesh, ax=ax_spec)
# cbar.set_label('Power (dB)', fontsize=12)

# fig2.tight_layout()
plt.show()