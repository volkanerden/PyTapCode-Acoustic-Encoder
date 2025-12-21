"""
Ensure the samples are named 'tap_1.wav', 'tap_2.wav', etc.
Files must be located in the same directory as this script.

From terminal, run:

    python tapcode_to_wav.py input_tap.docx output.wav
"""

import sys
import re
import random
from pathlib import Path
from typing import List, Optional, Tuple, Iterator

import numpy as np
import soundfile as sf
from docx import Document

try:
    from scipy.signal import resample_poly
except Exception:
    resample_poly = None

###############################################################################
# USER-EDITABLE PARAMETERS
###############################################################################

# leave empty to autoload
DOT_SAMPLES: List[str] = []

# time between tap hit onsets
HIT_INTERVAL_SEC = 0.15

# pauses between dot groups and between words
GROUP_SILENCE_SEC = 0.30
WORD_SILENCE_SEC = 0.45

# inherited from first sample if none
TARGET_SAMPLE_RATE: Optional[int] = None
USE_TRUE_RANDOM = True

OUTPUT_SUBTYPE = "PCM_16"
FINAL_PEAK_TARGET = 0.98

###############################################################################
# DOCX
###############################################################################

def read_docx_text(docx_path: Path) -> str:
    doc = Document(str(docx_path))
    parts = [p.text for p in doc.paragraphs if p.text]
    return " ".join(parts)

###############################################################################
# TAP TOKENS
###############################################################################

LETTER_RE = re.compile(r"(\.+)\s+(\.+)")

def iter_tokens(text: str) -> Iterator[Tuple[str, Optional[Tuple[int, int]]]]:
    cleaned = re.sub(r"[^./\s]", "", text)
    i = 0
    n = len(cleaned)
    while i < n:
        ch = cleaned[i]
        if ch.isspace():
            i += 1
            continue
        if ch == "/":
            yield "SLASH", None
            i += 1
            continue
        m = LETTER_RE.match(cleaned, i)
        if not m:
            i += 1
            continue
        row_dots = len(m.group(1))
        col_dots = len(m.group(2))
        yield "LETTER", (row_dots, col_dots)
        i = m.end()

###############################################################################
# AUDIO HELPERS
###############################################################################

def to_mono(x: np.ndarray) -> np.ndarray:
    if x.ndim == 1:
        return x.astype(np.float32, copy=False)
    return np.mean(x, axis=1).astype(np.float32, copy=False)

def resample_if_needed(x: np.ndarray, sr_in: int, sr_out: int) -> np.ndarray:
    if sr_in == sr_out:
        return x
    if resample_poly is None:
        raise RuntimeError
    from math import gcd
    g = gcd(sr_in, sr_out)
    up = sr_out // g
    down = sr_in // g
    return np.asarray(resample_poly(x, up=up, down=down)).astype(np.float32, copy=False)

def load_dot_samples(sample_paths: List[Path], target_sr: Optional[int]) -> Tuple[List[np.ndarray], int]:
    if target_sr is None:
        first, sr0 = sf.read(str(sample_paths[0]), always_2d=False)
        out_sr = int(sr0)
        samples = [to_mono(first)]
        start = 1
    else:
        out_sr = int(target_sr)
        samples = []
        start = 0

    for p in sample_paths[start:]:
        d, sr = sf.read(str(p), always_2d=False)
        m = to_mono(d)
        m = resample_if_needed(m, int(sr), out_sr)
        samples.append(m)

    # normalize each sample
    normed = []
    for s in samples:
        peak = float(np.max(np.abs(s))) if s.size else 0.0
        normed.append((s / peak * 0.95).astype(np.float32, copy=False) if peak > 0 else s)
    return normed, out_sr

###############################################################################
# OVERLAP MIX ENGINE
###############################################################################

def ensure_len(buf: np.ndarray, needed: int) -> np.ndarray:
    if needed <= buf.shape[0]:
        return buf
    new_len = max(needed, int(buf.shape[0] * 1.25) + 1)
    out = np.zeros(new_len, dtype=np.float32)
    out[:buf.shape[0]] = buf
    return out

def mix_in(buf: np.ndarray, sample: np.ndarray, start_idx: int) -> np.ndarray:
    end = start_idx + sample.shape[0]
    buf = ensure_len(buf, end)
    buf[start_idx:end] += sample
    return buf

###############################################################################
# MAIN
###############################################################################

def main() -> int:
    if len(sys.argv) != 3:
        print("Usage: python tapcode_to_wav.py input_tap.docx output.wav")
        return 1

    in_docx = Path(sys.argv[1])
    out_wav = Path(sys.argv[2])

    if not USE_TRUE_RANDOM:
        random.seed(0)

    # If array is empty autoload
    if DOT_SAMPLES:
        sample_paths = [Path(p) for p in DOT_SAMPLES]
    else:
        script_dir = Path(__file__).resolve().parent
        sample_paths = sorted(script_dir.glob("tap_*.wav"))

    if not sample_paths:
        print("No tap samples found. Put files like tap_1.wav ... tap_9.wav next to the script.")
        return 1

    missing = [str(p) for p in sample_paths if not p.exists()]
    if missing:
        print("Missing dot sample files:")
        for m in missing:
            print(" -", m)
        return 1

    dot_samples, sr = load_dot_samples(sample_paths, TARGET_SAMPLE_RATE)
    text = read_docx_text(in_docx)
    tokens = list(iter_tokens(text))

    hit_step = int(round(HIT_INTERVAL_SEC * sr))
    group_sil = int(round(GROUP_SILENCE_SEC * sr))
    word_sil = int(round(WORD_SILENCE_SEC * sr))

    # start with 1 second buffer
    timeline = np.zeros(sr, dtype=np.float32)
    t = 0

    for idx, (tok_type, payload) in enumerate(tokens):
        if tok_type == "SLASH":
            t += word_sil
            continue

        row_dots, col_dots = payload

        # row group
        for _ in range(row_dots):
            s = random.choice(dot_samples)
            timeline = mix_in(timeline, s, t)
            t += hit_step

        t += group_sil

        # col group
        for _ in range(col_dots):
            s = random.choice(dot_samples)
            timeline = mix_in(timeline, s, t)
            t += hit_step

        # if next is slash, word pause, else group pause
        next_type = tokens[idx + 1][0] if idx + 1 < len(tokens) else None
        t += (word_sil if next_type == "SLASH" else group_sil)

    # 1 sec tail safety
    timeline = timeline[:max(1, t + sr)]

    # Final peak normalize
    peak = float(np.max(np.abs(timeline))) if timeline.size else 0.0
    if peak > 1e-9 and peak > FINAL_PEAK_TARGET:
        scale = (FINAL_PEAK_TARGET / peak)
        timeline *= scale

    sf.write(str(out_wav), timeline, sr, subtype=OUTPUT_SUBTYPE)
    print(f"Wrote: {out_wav} | sr={sr}Hz | length={timeline.shape[0]/sr:.2f}s")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
