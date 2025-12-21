PyTap: Linguistic Encoder & Acoustic Synthesis Pipeline
PyTap is a modular Python-based toolkit designed to handle the end-to-end transformation of natural language into procedurally generated acoustic signals. Originally developed for an archival reconstruction project, the system provides a robust framework for linguistic encryption and high-fidelity audio synthesis.

# System Architecture
The pipeline consists of two distinct, decoupled scripts that can be used independently or as a sequence.

Phase 1: Linguistic Encryption (converter.py)
This module handles the transition from human language to a structured cipher.

Linguistic Normalization: Automates the expansion of Turkish numerals into textual form to ensure cipher consistency.

Custom Cipher Mapping: Implements a 5x6 tap-code matrix optimized for specific character sets.

Data Serialization: Outputs the encoded cipher to a .docx format, maintaining structural markers (slashes and spaces) for the audio synthesis phase.

Phase 2: Procedural Audio Synthesis (tapcode_to_wav.py)
This module reconstructs the cipher as a high-fidelity acoustic performance.

Stochastic Sample Selection: To avoid the "machine-gun effect," the engine utilizes a pool of 10+ randomized "click" samples for every onset, simulating human variance and natural resonance.

Digital Signal Processing (DSP): Uses NumPy for sample-accurate buffer mixing and SciPy for resampling logic.

Dynamic Timing: Features user-editable parameters for HIT_INTERVAL, GROUP_SILENCE, and WORD_SILENCE to control the rhythmic "cadence" of the output.

Peak Optimization: Integrated normalization logic (target 0.98) to ensure broadcast-quality signal integrity.

# Technical Stack
Language: Python 3

Libraries: NumPy, SciPy, SoundFile, python-docx

Audio Logic: Stochastic triggering, Procedural Synthesis, Peak Normalization.
