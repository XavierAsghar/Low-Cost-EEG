'''
Alpha Wave Test Script

Channel 1 electrode should be placed at Oz, channel 2 at O1, and channel 3 at O2. Ensure the patient is 
sitting still and trying not to blink.

The test consists of 3 phases: 20 seconds of eyes open, 20 seconds of eyes closed, and 20 seconds of eyes open.
A tone is played at the start of each phase.

Ensure that LabRecorder is recording both the EEG stream and the marker stream before pressing enter in the 
terminal to start the test.
'''


import time
import winsound
from pylsl import StreamInfo, StreamOutlet

# Setup LSL marker stream
info = StreamInfo('AlphaMarkers', 'Markers', 1, 0, 'string', 'alpha_test_markers')
outlet = StreamOutlet(info)

# Duration of each phase in seconds
phase_duration = 20 

def beep_cue(frequency=1000, duration=500):
    winsound.Beep(frequency, duration)

input("Press Enter to begin the 1-minute Alpha Test...")

# PHASE 1: Eyes Open
print("\n[ PHASE 1: EYES OPEN ] - Stare at a point on the wall.")
outlet.push_sample(['Eyes_Open_1_Start'])
beep_cue(1000, 500) # Single beep
time.sleep(phase_duration)
outlet.push_sample(['Eyes_Open_1_End'])

# PHASE 2: Eyes Closed
print("\n[ PHASE 2: EYES CLOSED ] - Close your eyes.")
outlet.push_sample(['Eyes_Closed_Start'])
beep_cue(1500, 500) 
time.sleep(0.5)
beep_cue(1500, 500) # Double high beep for eyes closed
time.sleep(phase_duration)
outlet.push_sample(['Eyes_Closed_End'])

# PHASE 3: Eyes Open
print("\n[ PHASE 3: EYES OPEN ] - Open your eyes.")
outlet.push_sample(['Eyes_Open_2_Start'])
beep_cue(1000, 500) # Single beep
time.sleep(phase_duration)
outlet.push_sample(['Eyes_Open_2_End'])

print("\nTest complete! You can stop LabRecorder.")
beep_cue(500, 1000) # Long low beep