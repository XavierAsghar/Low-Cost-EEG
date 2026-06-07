import pyxdf
import numpy as np
import matplotlib.pyplot as plt
from scipy import signal

# Load the recorded file
file_path = r"C:..."
data, header = pyxdf.load_xdf(file_path)

for stream in data:
    if stream['info']['name'][0] == 'Custom_ESP32_EEG':
        
        # Convert to NumPy arrays
        time_stamps = np.array(stream['time_stamps'])
        time_series = np.array(stream['time_series'])
        
        # Make the recording start exactly at 0.0 seconds
        time_stamps = time_stamps - time_stamps[0]
        print(f"Total recording length: {time_stamps[-1]:.2f} seconds")
        print(len(time_stamps)/56.52, "samples loaded.")
        
        # Extract Channel 1
        ch1_raw = time_series[:, 0]

        fs = 500.0  # Your sampling rate
        
        # 50 Hz Notch Filter (Q=30 determines how "narrow" the cut is)
        b_notch, a_notch = signal.iirnotch(w0=50.0, Q=30.0, fs=fs)
        ch1_notched = signal.filtfilt(b_notch, a_notch, ch1_raw)
        
        # Bandpass Filter (4th-order Butterworth)
        b_band, a_band = signal.butter(N=4, Wn=[0.5, 30], btype='bandpass', fs=fs)
        ch1_filtered = signal.filtfilt(b_band, a_band, ch1_notched)

        # Define window to plot
        start_time = 18.5
        end_time = 21.5
        
        # Create a boolean mask for time window
        mask = (time_stamps >= start_time) & (time_stamps <= end_time)
        
        # Apply the mask to slice the data
        time_sliced = time_stamps[mask]
        data_sliced = ch1_filtered[mask]


        
        # Plot Data ------------------------------------------------------------------------------------------------------------
        plt.rcParams['font.family'] = 'serif'
        plt.rcParams['font.serif'] = ['Georgia']

        fig, ax = plt.subplots(figsize=(14, 5), dpi=100)
    
        ax.plot(time_sliced, data_sliced, color='#3157F7', linewidth=1.5)
        ax.set_title("Filtered ECG without DRL", fontsize=18, fontweight='bold', pad=20)
        ax.set_xlabel("Time (Seconds)", fontsize=18, labelpad=15)
        ax.set_ylabel("Amplitude (µV)", fontsize=18)
        #ax.set_ylim(-1000,1500)
        
        # Remove the top and right borders
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)
        # Add grid lines to the y-axis
        ax.yaxis.grid(True, linestyle='--', alpha=0.7)
        ax.xaxis.grid(False)
        # Set tick font size
        ax.tick_params(labelsize=18)
        # Set background colour
        fig.set_facecolor('#FFFFFF')
        
        plt.tight_layout()
        # plt.savefig(r"C:...")
        plt.show()