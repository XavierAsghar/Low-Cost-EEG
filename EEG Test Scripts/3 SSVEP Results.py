'''
SSVEP Results Plotting Script

This script loads XDF file recorded during the SSVEP test script, and plots an FFT of the EEG data during the flickering phase.
'''

import pyxdf
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
from scipy import signal

# Load the recorded file (REPLACE WITH YOUR FILE PATH)
file_path = r"C:..."
data, header = pyxdf.load_xdf(file_path)

hzline = 15
freq_str = str(float(hzline))

eeg_stream = None
marker_stream = None

# Separate the streams
for stream in data:
    if stream['info']['name'][0] == 'Custom_ESP32_EEG':
        eeg_stream = stream
    elif stream['info']['name'][0] == 'StimulusMarkers':
        marker_stream = stream

if eeg_stream is None or marker_stream is None:
    print("Error: Could not find both EEG and Marker streams in the XDF file.")
    exit()

# Process EEG Data
eeg_times = np.array(eeg_stream['time_stamps'])
eeg_data = np.array(eeg_stream['time_series'])

dt = np.median(np.diff(eeg_stream['time_stamps']))
print(f"Effective sample rate from timestamps: {1/dt:.4f} Hz")
print(f"Number of samples: {len(eeg_data)}, duration: {eeg_times[-1]-eeg_times[0]:.2f} s")
print(f"Samples / duration: {len(eeg_data)/(eeg_times[-1]-eeg_times[0]):.4f} Hz")

# Extract Channel 1 
ch1_raw = eeg_data[:, 0]
fs = 500.0

# Filters (Notch 50Hz, Bandpass 1-50Hz)
b_notch, a_notch = signal.iirnotch(w0=50.0, Q=30.0, fs=fs)
ch1_notched = signal.filtfilt(b_notch, a_notch, ch1_raw)

b_band, a_band = signal.butter(N=4, Wn=[1.0, 50.0], btype='bandpass', fs=fs)
ch1_filtered = signal.filtfilt(b_band, a_band, ch1_notched)

# Process Markers
marker_times = np.array(marker_stream['time_stamps'])
marker_labels = [m[0] for m in marker_stream['time_series']]

# Find timestamps for stage boundaries
t_start = marker_times[marker_labels.index('Test_Start')] if 'Test_Start' in marker_labels else eeg_times[0]
t_flicker_start = marker_times[marker_labels.index('Flicker_Start')]
t_flicker_end = marker_times[marker_labels.index('Flicker_End')]
t_end = marker_times[marker_labels.index('Test_End')] if 'Test_End' in marker_labels else eeg_times[-1]

# Normalize times so the recording starts at 0
time_offset = eeg_times[0]
eeg_times -= time_offset
t_start -= time_offset
t_flicker_start -= time_offset
t_flicker_end -= time_offset
t_end -= time_offset

# Function to slice and calculate Frequency (PSD)
def get_stage_data(start_t, end_t):
    mask = (eeg_times >= start_t) & (eeg_times <= end_t)
    t_sliced = eeg_times[mask]
    data_sliced = ch1_filtered[mask]
    
    # Calculate Power Spectral Density using Welch's method
    freqs, psd = signal.welch(data_sliced, fs=fs, nperseg=int(fs*2))
    freqs, psd = signal.welch(data_sliced, fs=fs, nperseg=len(data_sliced))
    return t_sliced, data_sliced, freqs, psd

# Get data for the 3 stages
t_rest1, d_rest1, f_rest1, p_rest1 = get_stage_data(t_start, t_flicker_start)
t_flick, d_flick, f_flick, p_flick = get_stage_data(t_flicker_start, t_flicker_end)
t_rest2, d_rest2, f_rest2, p_rest2 = get_stage_data(t_flicker_end, t_end)



# Plot Data ------------------------------------------------------------------------------------------------------------
plt.rcParams['font.family'] = 'serif'
plt.rcParams['font.serif'] = ['Georgia']

fig, ax = plt.subplots(figsize=(12, 6), dpi=100)
        
ax.plot(f_flick, p_flick, color='#3157F7', linewidth=1.5)
ax.set_title(f"SSVEP Response with {freq_str} Hz Stimulus", fontsize=18, fontweight='bold', pad=20)
ax.set_xlabel("Frequency (Hz)", fontsize=18, labelpad=15)
ax.set_ylabel("Power (µV²/Hz)", fontsize=18)
ax.set_xlim(0,40)

# Highlight target frequency with a vertical dashed line
ax.axvline(x=hzline, color='black', linestyle='--', alpha=0.5, label=f'{freq_str} Hz Stimulus')
ax.legend(fontsize=10)
# Remove the top and right borders
ax.spines['top'].set_visible(False)
ax.spines['right'].set_visible(False)
# Add y axis grid
ax.yaxis.grid(True, linestyle='--', alpha=0.7)
# Set tick font size
ax.tick_params(labelsize=18)
# Set background colour
fig.set_facecolor('#FFFFFF')

plt.tight_layout()
plt.show()