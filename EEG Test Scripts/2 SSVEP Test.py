''' 
SSVEP Test Script 

The channel 1 electrode should be placed at Oz. The test could also be carried out at O1 or O2. 
Ensure the patient is sitting still, looking at the target, and trying not to blink.

This script vsyncs with a monitor using Pygame, to create flickering visual stimulus of a certain frequency, 
in order to produce SSVEPs. LSL markers are sent at the start and end of each phase.

Ensure that LabRecorder is recording both the EEG stream and the marker stream before pressing enter in the 
terminal to start the test.

Ensure that the target frequency is a divisor of the monitor refresh rate for accurate flickering. 
For example, with a 120 Hz monitor, you can use 6, 7.5, 8, 10, 12, 15, 20, 24, and 30 Hz.

Check with the terminal that the measured refresh rate matches the expected refresh rate of the monitor, 
and that the measured flicker frequency corresponds to the target frequency.
'''

import pygame
import sys
from pylsl import StreamInfo, StreamOutlet
import time
import numpy as np

# Timing Parameters (CHANGE THESE AS NECESSARY)
refresh_rate = 120  # Monitor Hz
target_freq = 15    # Desired SSVEP Hz
frames_per_cycle = int(refresh_rate / target_freq) 
frames_on = frames_per_cycle // 2 

# LSL Setup 
info = StreamInfo('StimulusMarkers', 'Markers', 1, 0, 'string', 'pygame_ssvep_markers')
outlet = StreamOutlet(info)

# Wait for user to start LabRecorder
input("Press Enter in the terminal to start the test...")

# Pygame Setup
pygame.init()
# Set up fullscreen display with VSync enabled
display_info = pygame.display.Info()
size = (display_info.current_w, display_info.current_h)
flags = pygame.FULLSCREEN | pygame.SCALED
screen = pygame.display.set_mode(size, flags, vsync=1, display=0)

# Test durations
pre_rest_sec = 5
flicker_sec = 10
post_rest_sec = 5

# Convert durations to frame counts
pre_rest_frames = pre_rest_sec * refresh_rate
flicker_frames = flicker_sec * refresh_rate
post_rest_frames = post_rest_sec * refresh_rate
total_frames = pre_rest_frames + flicker_frames + post_rest_frames

# Main Loop Setup
clock = pygame.time.Clock()
dropped_frames = 0
expected_ms_per_frame = 1000 / refresh_rate # ~6.06 ms
frame_intervals = []
last_t = time.perf_counter()

def draw_fixation():
    # Draw a simple fixation cross at the center of the screen
    screen.fill((0, 0, 0))
    center_x, center_y = screen.get_rect().center
    pygame.draw.line(screen, (50, 50, 50), (center_x - 20, center_y), (center_x + 20, center_y), 4)
    pygame.draw.line(screen, (50, 50, 50), (center_x, center_y - 20), (center_x, center_y + 20), 4)

print("Starting test sequence...")
outlet.push_sample(['Test_Start'])

# Stimulus Loop
for frame in range(total_frames):
    # Handle closing the window via Escape key
    for event in pygame.event.get():
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            pygame.quit()
            sys.exit()

    # PHASE 1: Pre-Flicker Baseline 
    if frame < pre_rest_frames:
        if frame == 0:
            print("Resting phase (pre-flicker)...")
        draw_fixation()

    # PHASE 2: SSVEP Flickering
    elif frame < (pre_rest_frames + flicker_frames):
        if frame == pre_rest_frames:
            print("Starting flicker...")
            outlet.push_sample(['Flicker_Start'])
        
        # Calculate where we are in the flicker cycle, independent of the pre-rest frames
        flicker_frame = frame - pre_rest_frames
        current_cycle_frame = flicker_frame % frames_per_cycle
        
        if current_cycle_frame < frames_on:
            screen.fill((255, 255, 255)) # White screen
        else:
            screen.fill((0, 0, 0)) # Black screen

    # PHASE 3: Post-Flicker Baseline
    else:
        if frame == (pre_rest_frames + flicker_frames):
            print("Resting phase (post-flicker)...")
            outlet.push_sample(['Flicker_End'])
        draw_fixation()

    # Update the display (waits for VSync)
    pygame.display.flip()

    # Track how long that frame took to detect drops
    now = time.perf_counter()
    if frame > 0:
        frame_intervals.append((now - last_t) * 1000)
    last_t = now

# End of test
outlet.push_sample(['Test_End'])

fi = np.array(frame_intervals[20:])  # discard warm-up frames
mean_dt = np.mean(fi)
measured_refresh = 1000 / mean_dt
actual_flicker = measured_refresh / frames_per_cycle
n_drops = int(np.sum(fi > mean_dt * 1.5))

print(f"\nMeasured refresh rate: {measured_refresh:.4f} Hz")
print(f"Actual flicker frequency: {actual_flicker:.4f} Hz")
print(f"Dropped frames: {n_drops}")

pygame.quit()

