# Two-Channel-Signal-Generator
![circuit_labelled](https://github.com/user-attachments/assets/8831387f-45be-4044-ba8e-41e0e0922474)
This project presents a low-cost, feature-rich signal generator capable of producing basic waveforms and advanced modulation schemes. Built around the AD9833 waveform generator and ESP32 microcontroller, it supports sine, square, and triangle waves, as well as BFSK, MFSK, BPSK, MPSK, ASK, PWM, and AM signals. A custom Python GUI allows real-time control of frequency, phase, and modulation settings. A phase-lock loop ensures synchronization between channels using a PD controller. The system includes amplifiers, analog multipliers, and a multiplexer for signal routing. Designed for flexibility and expandability, it is well-suited for educational and testing applications in signal processing and communication systems.

We propose a novel signal generator with the following features:

1. **Two-Phase Synchronized channels**
2. **Sine, Square & Triangle** with variable Amplitude
3. **Various Modulated Waveforms such as:**
   1. **BFSK, QFSK, ... M-FSK** (FSK - Frequency Shift Keying)
   2. **BPSK, QPSK, ... M-PSK** (PSK - Phase Shift Keying)
   3. **Different PWM Signals** (PWM - Pulse Width Modulation)
   4. **ASK** (ASK - Amplitude Shift Keying)
   5. **Frequency Sweep**
   6. **Conventional Amplitude Modulation** (Using a 4-Quadrant Multiplier)

## Components Used in the Signal Generator Circuit

- **2× AD9833** – DDS Signal Generator
- **ESP-32** – Microcontroller for control and communication
- **TSH82** – High Speed Operational Amplifier
- **74LS14N** – Schmitt Trigger
- **SN7486** – XOR Gate
- **AD633JN** – 4-Quadrant Analog Multiplier

## Contributors
[M P Samartha](https://github.com/samarthamp)  
[Hrishikesh Gawas](https://github.com/HrishikeshGawasIIITH)


## Contents
- `FUNGENE-Spec-Sheet.xlsx` contains specifications achieved by the prototype signal generator.
- `FUNGENE_V2.ino` contains the main Arduino code for the microcontroller. It defines all the required functions for Digital Modulation
- `Phase_Loop.ino` contains the Arduino code for implementing **phase measurement, correction and setting.**
- `gui.py` contains the `tkinter` library implementation of an interactive GUI automated to take in inputs and perform the required function. The following image shows a preview of the same.
- `Report.pdf` contains the details regarding implementation. For results and further information, please refer to this.
- For a Detailed Explanation and Demo, [Click Here](https://www.youtube.com/watch?v=zzTNfDaagOw)

![gui](https://github.com/user-attachments/assets/6c182558-31a4-4631-b055-af4442986a54)
 
