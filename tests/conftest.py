"""Synthetic media and transcripts for the tests: tones stand for words, so no speech model is needed."""
import shutil
import subprocess
import sys
import wave
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parent.parent
SKILL = ROOT / '.claude' / 'skills' / 'claude-autocut'
sys.path.insert(0, str(SKILL / 'scripts'))

needs_ffmpeg = pytest.mark.skipif(not shutil.which('ffmpeg') or not shutil.which('ffprobe'), reason='FFmpeg not installed')


def words(spec):
    """spec: list of (text, start, end[, prob]) → transcript words."""
    return [{'text': t, 'start': s, 'end': e, 'prob': (p[0] if p else 0.95)} for t, s, e, *p in spec]


def transcript(spec, duration, language='en'):
    return {'engine': 'fixture', 'model': 'fixture', 'language': language, 'duration': duration, 'words': words(spec)}


def make_media(path, spec, duration, size='320x240', fps=30, extra_sound=()):
    """A test pattern video whose audio has a tone under every word of `spec` (and under `extra_sound` spans)."""
    sr = 48000
    t = np.arange(int(duration * sr)) / sr
    audio = np.random.default_rng(1).normal(0, 0.0005, len(t))   # a quiet noise floor, like a real room
    for k, (_, s, e, *_) in enumerate(list(spec) + [(None, a, b) for a, b in extra_sound]):
        m = (t >= s) & (t < e)
        audio[m] += 0.3 * np.sin(2 * np.pi * (220 + 40 * (k % 5)) * t[m])
    wav = Path(path).with_suffix('.wav')
    with wave.open(str(wav), 'wb') as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(sr)
        w.writeframes((np.clip(audio, -1, 1) * 32767).astype(np.int16).tobytes())
    subprocess.run(['ffmpeg', '-v', 'error', '-y', '-f', 'lavfi', '-i', f'testsrc2=size={size}:rate={fps}:duration={duration}',
                    '-i', str(wav), '-map', '0:v', '-map', '1:a', '-c:v', 'libx264', '-pix_fmt', 'yuv420p', '-preset', 'ultrafast',
                    '-c:a', 'aac', '-shortest', str(path)], check=True)
    wav.unlink()
    return Path(path)


# A recording with: lead-in silence, a sentence, an incomplete take redone in full, a long pause after a
# sentence, a filler, a negation, and text that Whisper "heard" over silence at the end.
SPEC = [
    ('Hello', 1.00, 1.40), ('everyone.', 1.45, 2.00),
    ('Today', 2.50, 2.80), ('I', 2.85, 2.95), ('will', 3.00, 3.20), ('show', 3.25, 3.55),
    ('Today', 4.40, 4.70), ('I', 4.75, 4.85), ('will', 4.90, 5.10), ('show', 5.15, 5.45), ('you', 5.50, 5.70), ('this.', 5.75, 6.20),
    ('Um,', 8.20, 8.60),
    ('it', 9.00, 9.15), ('is', 9.20, 9.35), ('not', 9.40, 9.70), ('magic.', 9.75, 10.30),
]
GHOST = [('Thanks', 12.40, 12.70), ('for', 12.75, 12.90), ('watching.', 12.95, 13.30)]   # over silence
DURATION = 14.0
