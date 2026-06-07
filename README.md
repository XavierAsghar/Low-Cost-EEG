# Low-Cost-EEG
As part of my Masters Project at University, I have created my own EEG module, with the goal of reducing the cost of EEG technology, and removing barriers to conducting BCI projects/reserach. 
The module has been verified through the successful detection of Alpha Waves, SSVEPs, and P300s. Additionally the module can also be used to measure other biopotentials, including EMG and ECG. The component cost of the module is £69.07 for 4-Channels, and £99.92 for 8-Channels.

<img width="3072" height="2931" alt="conc 1" src="https://github.com/user-attachments/assets/7645f9a5-55a8-4bad-aab5-7679d47df7f0" />

### The Hardware
* Up to 8-channels of electrodes can be connected to the input pin headers.
* Texas Instruments ADS1299 EEG Analogue Front-End amplifies and digitises the EEG signal at up to 500 SPS
* The ESP32-S3 then reads the EEG data, and transmits it to a a host computer using Bluetooth Low Energy
* A python script on the host computer unpacks the EEG data, and pushes it to the Lab-Streaming-Layer, for visualisation and recording
* The module is battery powered to ensure patient safety via electrical isolation
* The built in driven right leg helps to cancel common-mode noise

All testing so far has been conducted with standard gold-cup electrodes. For full details of the design and verification of the module, see the Final Report PDF located in the documentation folder. Additionally for complete instructions to use the module, see the User Guide PDF in the same folder. I reccomend using Brainvision LSL Viewer application to view the recorded EEG data in real-time, or the LabRecorder application to record the EEG data.

This repository contains all of production files necessary to create your own module, as well as the source code, and Altium and Inventor Projects needed to modify/continue development of the project. There are several improvements I would like to make to the project before considering it complete, which are discussed in my final report. I have also included the python scripts I used to test for alpha waves, SSVEPs, P300s, and to perform a concealed information test (lie detector).

This project is licensed under the GPL V3 license

### Safety Warning
When connected to a subject, the device must be battery powered, and the USB-C must be disconnected. This is to ensure electrical isolation of the subject from mains.

<img width="2774" height="2787" alt="alpha test" src="https://github.com/user-attachments/assets/0c880261-ad66-4385-a3a3-2ec700e2de8b" />
