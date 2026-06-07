'''
Three stimulus protocol concealed information test (CIT) script.
The test has been designed to mirror the methods used by Farwell and Donchin:
(The truth will out: interrogative polygraphy ("lie detection") with event-related brain potentials, 1991)

In this script, the subject is asked to choose a "secret" color from a list of 5 options. This becomes the "probe" stimulus.
The "target" stimulus is a fixed color (yellow) that the subject is instructed to pay attention to and count silently.
The remaining 4 colors are "irrelevant" stimuli that the subject has no reason to attend to.

The colours will be flashed in a random order on the screen, and the subjects P300 response to each stimulus is recorded. 
The probe stimulus should elicit a larger P300 than the irrelevant stimuli. The target stimulus should elicit the largest P300.

The test yields better results if the subject has interacted with the probe colour before the test, for instance by 
writing it down, or picking up a physical object of that colour.

The channel 1 electrode should be placed at Cz. The test could also be carried out at Fz or Pz.
Ensure the subject is sitting still and trying not to blink during the test. 
Ensure LabRecorder is recording the EEG stream and the marker stream, before pressing enter in the terminal to start the test.
'''

import os
import sys
import time
import random
# Hide pygame welcome message
os.environ['PYGAME_HIDE_SUPPORT_PROMPT'] = '1'
import pygame
from pylsl import StreamInfo, StreamOutlet, local_clock

# EXPERIMENT PARAMETERS -----------------------------------------------------------------------------------
TOTAL_TRIALS   = 150     # Total number of color flashes
FLASH_DURATION = 0.100   # How long the color stays on screen (seconds)
ISI_MIN        = 0.8     # Minimum Inter-Stimulus Interval (seconds)
ISI_MAX        = 1.6     # Maximum Inter-Stimulus Interval (seconds)
PRE_TEST_DELAY = 3.0     # Time to wait before first flash

# Spacing constraints
MIN_GAP_BETWEEN_SALIENT = 1  # Minimum irrelevant colors between ANY probe or target
NO_SALIENT_AT_START     = 2  # First N flashes must be irrelevant

# Color Palette (RGB Tuples)
COLORS = {
    "Red":    (255, 0, 0),
    "Yellow": (255, 255, 0),   # Hardcoded as the Target
    "Green":  (0, 255, 0),
    "Blue":   (0, 100, 255),
    "Purple": (150, 0, 255),
    "Cyan":   (0, 255, 255)
}
BG_COLOR = (40, 40, 40)
TARGET_COLOR = "Yellow"

# Generate colour sequence --------------------------------------------------------------------------------
def build_sequence(total_trials, target_color, probe_color, min_gap, start_gap):
    irrelevant_colors = [c for c in COLORS.keys() if c not in (target_color, probe_color)]
    
    # Calculate roughly 1/6th distribution
    base_count = int(total_trials / 6)
    
    # Randomise target count slightly
    n_targets = random.randint(max(1, base_count - 5), base_count + 5)
    n_probes  = base_count  # Keep probe fixed at 1/6th for stable averaging
    
    n_salient = n_targets + n_probes
    n_irrelevants = total_trials - n_salient

    # Check spacing constraints
    mandatory = start_gap + min_gap * (n_salient - 1)
    if mandatory > n_irrelevants:
        raise ValueError(f"Need at least {mandatory} irrelevants for spacing, but only have {n_irrelevants}.")

    # Distribute free irrelevants into 'buckets'
    free = n_irrelevants - mandatory
    n_slots = n_salient + 1
    extras = [0] * n_slots
    for _ in range(free):
        extras[random.randrange(n_slots)] += 1

    # Create a shuffled list of the salient items
    salient_items = [probe_color] * n_probes + [target_color] * n_targets
    random.shuffle(salient_items)

    # Build the sequence using an 'irrelevant' placeholder
    seq = []
    seq.extend(['irrelevant'] * (start_gap + extras[0]))
    for i in range(n_salient):
        seq.append(salient_items[i])
        gap = min_gap if i < n_salient - 1 else 0
        seq.extend(['irrelevant'] * (gap + extras[i + 1]))

    # Create a balanced pool of the actual irrelevant colors
    irrelevant_pool = []
    for color in irrelevant_colors:
        irrelevant_pool.extend([color] * int(n_irrelevants / len(irrelevant_colors)))
    # Top up any remainder caused by rounding
    while len(irrelevant_pool) < n_irrelevants:
        irrelevant_pool.append(random.choice(irrelevant_colors))
    random.shuffle(irrelevant_pool)

    # Replace placeholders with actual irrelevant colors
    final_seq = []
    for item in seq:
        if item == 'irrelevant':
            final_seq.append(irrelevant_pool.pop())
        else:
            final_seq.append(item)

    return final_seq, n_targets

# Drawing functions ---------------------------------------------------------------------------------------
def draw_fixation_cross(screen, color=(200, 200, 200), size=20):
    cx, cy = screen.get_rect().center
    pygame.draw.line(screen, color, (cx - size, cy), (cx + size, cy), 3)
    pygame.draw.line(screen, color, (cx, cy - size), (cx, cy + size), 3)

def draw_color_block(screen, color_rgb, size=400):
    cx, cy = screen.get_rect().center
    rect = pygame.Rect(0, 0, size, size)
    rect.center = (cx, cy)
    pygame.draw.rect(screen, color_rgb, rect)

# Main experiment loop ------------------------------------------------------------------------------------
def main():
    print("="*50)
    print(" CIT: CONCEALED INFORMATION TEST ")
    print("="*50)
    print(f"\nExperimenter: Please step away or look away.")
    print("Subject: Follow the instructions below.\n")
    
    valid_probes = [c for c in COLORS.keys() if c != TARGET_COLOR]
    print(f"Available secret colors: {', '.join(valid_probes)}")
    
    # User Input Loop
    probe_color = ""
    while probe_color not in valid_probes:
        probe_color = input(f"Type your chosen secret color (Case Sensitive) >>> ").strip().capitalize()
        if probe_color not in valid_probes:
            print(f"Invalid choice. Must be one of: {', '.join(valid_probes)}")
            
    # Hide the answer from the experimenter by printing blank lines
    print("\n" * 50)
    print("Secret color locked in! (Hidden from experimenter).")
    input("Experimenter: You may return. Press ENTER to connect to LSL >>> ")

    # Initialize LSL
    info = StreamInfo(name='CIT_Visual_Markers', type='Markers', 
                      channel_count=1, nominal_srate=0, 
                      channel_format='string', source_id='cit_visual_v2')
    outlet = StreamOutlet(info)
    print("LSL Marker stream 'CIT_Visual_Markers' created.")

    # Build sequence
    sequence, actual_targets = build_sequence(TOTAL_TRIALS, TARGET_COLOR, probe_color, 
                                              MIN_GAP_BETWEEN_SALIENT, NO_SALIENT_AT_START)
    print(f"\nSequence built: {len(sequence)} total flashes.")
    print(f"Wait for the prompt, then start LabRecorder.")
    
    input("\nStart LabRecorder, then press ENTER to launch the visual test >>> ")

    # Initialise Pygame
    pygame.init()
    screen = pygame.display.set_mode((800, 600), pygame.SCALED | pygame.FULLSCREEN, vsync=1)
    pygame.mouse.set_visible(False)

    screen.fill(BG_COLOR)
    draw_fixation_cross(screen)
    pygame.display.flip()
    
    print(f"\nStarting in {PRE_TEST_DELAY} seconds...")
    print(f"Subject task: Silently count the number of {TARGET_COLOR} flashes.")
    time.sleep(PRE_TEST_DELAY)
    
    outlet.push_sample(['test_start'], local_clock())

    try:
        for i, color_name in enumerate(sequence):
            for event in pygame.event.get():
                if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                    raise KeyboardInterrupt

            screen.fill(BG_COLOR)
            draw_color_block(screen, COLORS[color_name])
            pygame.display.flip()
            
            stamp = local_clock()
            outlet.push_sample([color_name], stamp)
            
            t_end = time.perf_counter() + FLASH_DURATION
            while time.perf_counter() < t_end:
                pass 
                
            screen.fill(BG_COLOR)
            draw_fixation_cross(screen)
            pygame.display.flip()
            
            isi = random.uniform(ISI_MIN, ISI_MAX)
            time.sleep(isi)
            
            if (i + 1) % 20 == 0:
                print(f"  Progress: {i+1}/{len(sequence)} flashes complete.")

    except KeyboardInterrupt:
        print("\nTest aborted by user.")
        outlet.push_sample(['test_aborted'], local_clock())

    outlet.push_sample(['test_end'], local_clock())
    pygame.quit()
    print("\nTest complete! You can stop LabRecorder.")
    
    reported = input(f"\nSubject, how many times did you see {TARGET_COLOR}? >>> ")
    print(f"Subject reported: {reported}")
    print(f"Actual Target count was: {actual_targets}")
    #print(f"(The secret probe color was: {probe_color})")

if __name__ == '__main__':
    main()