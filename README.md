# PyTapCode-Acoustic-Encoder

`PyTapCode` is a specialized dual-stage Python pipeline designed for linguistic encryption and procedural acoustic reconstruction. It provides a bridge between natural language and the "Tap Code" cipher—a communication method historically used by prisoners.

This system was specifically developed for the archival art exhibition **"Uninterrupted"** (by Doğa Yirik, opening 2026) to sonify 1980s Turkish prison records.

## Features

* **Turkish Linguistic Processing:** Native support for Turkish characters and automated expansion of numerical values into text.
* **Decoupled Pipeline:** Separate modules for text-to-cipher encoding and cipher-to-audio synthesis.
* **Stochastic Audio Engine:** Uses randomized sample selection (10+ variations) to simulate human tapping variance and organic resonance.
* **Sample-Accurate DSP:** Built on NumPy for precise buffer mixing and peak normalization.

## The Cipher: Turkish Tap Code Matrix

The system utilizes a custom **5x6 Tap Code Matrix** specifically mapped for the Turkish alphabet. Each character is represented by two sets of "taps": the first set indicates the **Row**, and the second set indicates the **Column**.

|  | 1 | 2 | 3 | 4 | 5 | 6 |
| --- | --- | --- | --- | --- | --- | --- |
| **1** | A | B | C | Ç | D | E |
| **2** | F | G | Ğ | H | I | İ |
| **3** | J | K | L | M | N | O |
| **4** | Ö | P | R | S | Ş | T |
| **5** | U | Ü | V | Y | Z | - |

*Example:* The letter **"D"** is Row 1, Column 5. It is encoded as `.` (pause) `.....`

## Usage

### 1. Encode Text to Cipher

The first script reads a `.docx` file, expands numbers, removes punctuation, and generates the tap-code text.

```bash
# Run from terminal
python converter.py input.docx encoded_output.docx

```

### 2. Synthesize Cipher to Audio

The second script reads the encoded `.docx` and generates a high-fidelity `.wav` file.

```bash
# Run from terminal
python tapcode_to_wav.py encoded_output.docx output_audio.wav

```

## Technical Insights

### Audio Logic & Signal Consistency

The synthesis engine is designed to maintain the integrity of the source audio samples:

* **Inherited Sample Rate:** The script automatically detects the sample rate of the first loaded "click" sample and sets the global `TARGET_SAMPLE_RATE` to match it. This ensures no unintended resampling occurs during the mixing process.
* **Bit Depth (PCM_16):** The system outputs a high-fidelity 16-bit PCM signal by default (`OUTPUT_SUBTYPE = "PCM_16"`), providing a professional standard for exhibition playback.
* **Stochastic Selection:** For every "dot" in the cipher, the engine picks a random sample from a provided pool of `tap_*.wav` files. This avoids the "machine-gun effect" and mimics the physical reality of human tapping.

### Linguistic Logic (`converter.py`)

* **Turkish Number Expansion:** Converts digits (e.g., "1970") into full Turkish words ("bin dokuz yüz yetmiş") before encoding.
* **Cipher Formatting:** Generates a slash-terminated (`/`) string where each word is clearly separated for the audio parser.

### DSP & Timing (`tapcode_to_wav.py`)

* **Temporal Precision:** Features user-editable parameters for `HIT_INTERVAL_SEC`, `GROUP_SILENCE_SEC`, and `WORD_SILENCE_SEC` to control the rhythmic cadence.
* **Peak Optimization:** The final audio buffer is normalized to **0.98** using NumPy to ensure maximum headroom without digital clipping.

## Dependencies

* `Python 3.x`
* `NumPy` (Signal processing)
* `SciPy` (Resampling logic)
* `SoundFile` (WAV exporting)
* `python-docx` (Word document parsing)
