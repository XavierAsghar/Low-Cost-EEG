"""
P300 Test Script

Channel 1 electrode should be placed at Pz. The test could also be carried out at Cz or Fz.

This test uses an auditory oddball paradigm to elicit P300 responses. 
The subject should silently count the number of high-pitched 'target' tones.

Ensure the subject is sitting still and trying not to blink during the test. 
Ensure LabRecorder is recording the EEG stream and the marker stream, before pressing enter in the terminal to start the test.
"""

import argparse
import os
import random
import time
# Hide the pygame welcome banner before importing
os.environ['PYGAME_HIDE_SUPPORT_PROMPT'] = '1'
import numpy as np
import pygame
from pylsl import StreamInfo, StreamOutlet, local_clock

# Parameters 
SAMPLE_RATE      = 44100    # audio sample rate (Hz)
TONE_DURATION    = 0.100    # 100 ms tone
RAMP_DURATION    = 0.005    # 5 ms cosine ramps to avoid clicks
TONE_AMPLITUDE   = 0.5      # 0.0 - 1.0
STANDARD_FREQ    = 1000     # Hz
TARGET_FREQ      = 2000     # Hz

N_TARGETS        = random.randint(18,28)    # Number of target tones 
N_STANDARDS      = 100 - N_TARGETS          # Number of standard tones
MIN_STD_BETWEEN  = 2        # min standards between targets
NO_TARGET_AT_START = 3      # first N trials must be standards

ISI_MIN          = 1.4      # seconds (jittered)
ISI_MAX          = 1.8

PRE_TEST_DELAY   = 3.0
# --------------------------------


def make_sound(freq_hz, duration_s, fs, amplitude, ramp_s):
    n = int(duration_s * fs)
    t = np.arange(n) / fs
    tone = np.sin(2 * np.pi * freq_hz * t)

    ramp_n = int(ramp_s * fs)
    env = np.ones(n)
    env[:ramp_n] = 0.5 * (1 - np.cos(np.linspace(0, np.pi, ramp_n)))
    env[-ramp_n:] = 0.5 * (1 + np.cos(np.linspace(0, np.pi, ramp_n)))

    samples = (amplitude * tone * env * 32767).astype(np.int16)
    stereo = np.ascontiguousarray(np.column_stack([samples, samples]))
    return pygame.sndarray.make_sound(stereo)


def build_sequence(n_standards, n_targets, min_gap, no_target_start):
    mandatory = no_target_start + min_gap * (n_targets - 1)
    if mandatory > n_standards:
        raise ValueError(
            f"Need at least {mandatory} standards (have {n_standards})."
        )

    free = n_standards - mandatory
    n_slots = n_targets + 1

    extras = [0] * n_slots
    for _ in range(free):
        extras[random.randrange(n_slots)] += 1

    seq = []
    seq.extend(['standard'] * (no_target_start + extras[0]))
    for t in range(n_targets):
        seq.append('target')
        gap = min_gap if t < n_targets - 1 else 0
        seq.extend(['standard'] * (gap + extras[t + 1]))

    assert seq.count('target') == n_targets
    assert seq.count('standard') == n_standards
    return seq


def main(test_run=False):
    # Initialise pygame mixer
    pygame.mixer.pre_init(frequency=SAMPLE_RATE, size=-16, channels=2, buffer=512)
    pygame.mixer.init()

    # Pre-generate Sound objects
    standard_sound = make_sound(STANDARD_FREQ, TONE_DURATION, SAMPLE_RATE, TONE_AMPLITUDE, RAMP_DURATION)
    target_sound   = make_sound(TARGET_FREQ,   TONE_DURATION, SAMPLE_RATE, TONE_AMPLITUDE, RAMP_DURATION)

    # Build trial sequence
    n_std = 10 if test_run else N_STANDARDS
    n_tgt = 3  if test_run else N_TARGETS
    sequence = build_sequence(n_std, n_tgt, MIN_STD_BETWEEN, NO_TARGET_AT_START)
    print(f"Sequence: {len(sequence)} trials  "f"({sequence.count('standard')} std / {sequence.count('target')} tgt)")
    est_min = len(sequence) * (TONE_DURATION + (ISI_MIN + ISI_MAX) / 2) / 60
    print(f"Estimated duration: {est_min:.1f} min")

    # Create LSL marker outlet
    info = StreamInfo(
        name='P300_Markers',
        type='Markers',
        channel_count=1,
        nominal_srate=0,
        channel_format='string',
        source_id='p300_oddball_v1'
    )
    outlet = StreamOutlet(info)
    print("\nLSL outlet 'P300_Markers' is live.")

    # Audio check
    print("\nAudio check: you should hear a LOW tone, then a HIGH tone.")
    standard_sound.play()
    time.sleep(TONE_DURATION + 0.4)
    target_sound.play()
    time.sleep(TONE_DURATION + 0.1)
    answer = input("Did you hear both tones clearly? [y/N] >>> ").strip().lower()
    if answer != 'y':
        print("Aborting. Check Windows volume mixer for python.exe.")
        pygame.mixer.quit()
        return

    # Wait for experimenter
    input("Start Lab Recorder now, then press Enter to begin >>> ")

    print(f"\nStarting in {PRE_TEST_DELAY:.0f}s. ""Subject: silently count the HIGH-pitched tones.\n")
    time.sleep(PRE_TEST_DELAY)

    # Run trials
    outlet.push_sample(['test_start'], local_clock())
    t0 = time.perf_counter()

    try:
        for i, trial in enumerate(sequence):
            isi = random.uniform(ISI_MIN, ISI_MAX)
            time.sleep(isi)

            sound = target_sound if trial == 'target' else standard_sound

            # Marker timestamped at the moment of .play().
            stamp = local_clock()
            outlet.push_sample([trial], stamp)
            sound.play()
            time.sleep(TONE_DURATION + 0.02)   # let the tone finish

            if (i + 1) % 25 == 0:
                elapsed = time.perf_counter() - t0
                print(f"  trial {i+1:3d}/{len(sequence)}  "
                      f"({elapsed/60:.1f} min)")

    except KeyboardInterrupt:
        outlet.push_sample(['test_aborted'], local_clock())
        print("\nAborted by user.")
        pygame.mixer.quit()
        return

    outlet.push_sample(['test_end'], local_clock())
    pygame.mixer.quit()

    print("\nTest complete.")
    actual = sequence.count('target')
    reported = input(f"How many targets did the subject count? "f"(actual = {actual}) >>> ").strip()
    print(f"Reported: {reported}  |  Actual: {actual}")


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--test', action='store_true', help='Short test run (13 trials)')
    args = parser.parse_args()
    main(test_run=args.test)