"""Recording analysis, before any cut is decided.

Measures what can be measured from the transcript and the audio: sentences, pauses (and which ones may be
pauses for emphasis), retakes (a sentence that stops and is said again), repetitions (the same sentence said
twice), hesitations, negations, low-confidence words and loudness. Nothing here changes media.
"""
from __future__ import annotations

import difflib
import subprocess
from pathlib import Path

import numpy as np

from .common import END_PUNCT, NEGATIONS, hesitation_re, norm, write_json

SENTENCE_PAUSE = 0.30     # a pause this long also ends a sentence (s)
UNCERTAIN = 0.6           # word probability below this is "uncertain"
LONG, EXCESSIVE = 0.7, 1.5
ENV_STEP = 0.01           # loudness envelope resolution (s)


def load_words(transcript: dict) -> list[dict]:
    hes = hesitation_re(transcript.get('language'))
    out = []
    for x in transcript['words']:
        t = x['text'].strip()
        if not t:
            continue
        n = norm(t)
        out.append({'i': len(out), 'w': t, 'n': n, 's': float(x['start']), 'e': float(x['end']),
                    'p': float(x.get('prob', 1.0)), 'neg': n in NEGATIONS, 'hes': bool(n) and bool(hes.match(n))})
    return out


def sentences(ws: list[dict]) -> list[dict]:
    """A sentence ends at end punctuation, at a pause of SENTENCE_PAUSE, or at a comma followed by 0.2 s."""
    out, cur = [], []
    for k, w in enumerate(ws):
        cur.append(w)
        nxt = ws[k + 1] if k + 1 < len(ws) else None
        gap = nxt['s'] - w['e'] if nxt else 99
        if w['w'][-1] in END_PUNCT or gap >= SENTENCE_PAUSE or (w['w'][-1] == ',' and gap >= 0.2):
            out.append(cur)
            cur = []
    if cur:
        out.append(cur)
    return [{'id': f's{k + 1:02d}', 'first': f[0]['i'], 'last': f[-1]['i'], 'start': f[0]['s'], 'end': f[-1]['e'],
             'text': ' '.join(w['w'] for w in f)} for k, f in enumerate(out)]


def envelope_db(media) -> np.ndarray | None:
    """RMS loudness in dBFS over 10 ms windows (mono, 16 kHz)."""
    if not media or not Path(media).exists():
        return None
    sr = 16000
    r = subprocess.run(['ffmpeg', '-v', 'error', '-i', str(media), '-vn', '-ac', '1', '-ar', str(sr), '-f', 's16le', '-'],
                       capture_output=True)
    if r.returncode != 0 or not r.stdout:
        return None
    x = np.frombuffer(r.stdout[: len(r.stdout) // 2 * 2], np.int16).astype(np.float32) / 32768
    n = int(sr * ENV_STEP)
    if len(x) < n:
        return None
    blocks = x[: len(x) // n * n].reshape(-1, n)
    return 20 * np.log10(np.sqrt((blocks ** 2).mean(1)) + 1e-7)


def level(env, t0: float, t1: float):
    """(mean speech level dB, peak dB) between t0 and t1; speech = windows within 25 dB of the peak."""
    if env is None:
        return None, None
    j = env[int(t0 / ENV_STEP): max(int(t0 / ENV_STEP) + 1, int(t1 / ENV_STEP))]
    if not len(j):
        return None, None
    peak = float(j.max())
    sp = j[j > peak - 25]
    return round(float(10 * np.log10(np.mean(10 ** (sp / 10)))), 1), round(peak, 1)


def mark_sound(ws, env, floor):
    """Flag words transcribed over silence (a known Whisper artifact) and find audible sound without words.

    A word is "silent" when the loudest 10 ms window from 0.3 s before it to 0.3 s after it is less than 10 dB
    above the noise floor: there is no voice under it or next to it (Whisper edges drift, so a word right after
    speech is never called silent). A run of 0.3 s or more clearly above the floor with no word on it is "unworded" sound (speech the
    transcript missed, laughter, music...): the plan never cuts it on its own.
    """
    if env is None or floor is None:
        return []
    for w in ws:
        j = env[int(w['s'] / ENV_STEP): max(int(w['s'] / ENV_STEP) + 1, int(w['e'] / ENV_STEP))]
        w['peak_db'] = round(float(j.max()), 1) if len(j) else None
        k = env[max(0, int((w['s'] - 0.3) / ENV_STEP)): int((w['e'] + 0.3) / ENV_STEP) + 1]
        w['silent'] = len(k) > 0 and float(k.max()) < floor + 10
    voiced = [w['peak_db'] for w in ws if not w.get('silent') and w.get('peak_db') is not None]
    ref = float(np.median(voiced)) if voiced else floor + 30
    thr = max(floor + 15, ref - 25)
    covered = np.zeros(len(env), bool)
    for w in ws:
        if not w.get('silent'):
            covered[max(0, int((w['s'] - 0.15) / ENV_STEP)): int((w['e'] + 0.15) / ENV_STEP) + 1] = True
    loud = (env > thr) & ~covered
    out, k = [], 0
    while k < len(loud):
        if loud[k]:
            j = k
            while j < len(loud) and loud[j]:
                j += 1
            if (j - k) * ENV_STEP >= 0.3:
                out.append({'start': round(k * ENV_STEP, 2), 'end': round(j * ENV_STEP, 2), 'peak_db': round(float(env[k:j].max()), 1)})
            k = j
        else:
            k += 1
    return out


def pause_class(d: float) -> str:
    return 'excessive' if d > EXCESSIVE else 'long' if d > LONG else 'incidental'


def retakes(ws, ss):
    """A sentence that starts with the same 2+ words as the next one and is not longer: a take that was redone."""
    out = []
    for a, b in zip(ss, ss[1:]):
        na = [w['n'] for w in ws[a['first']:a['last'] + 1] if not w['hes']]
        nb = [w['n'] for w in ws[b['first']:b['last'] + 1] if not w['hes']]
        same = 0
        while same < min(len(na), len(nb)) and na[same] == nb[same]:
            same += 1
        if same == len(na) == len(nb):
            continue   # two complete, identical takes: a repetition, decided by evidence, not a retake
        if same >= 2 and len(na) <= len(nb) and b['start'] - a['end'] < 3.0:
            full_prefix = same == len(na)
            out.append({'incomplete': a['id'], 'redone': b['id'], 'same_words': same,
                        'confidence': 'high' if full_prefix else 'medium',
                        'evidence': ('the first take stops midway; the second repeats its start and goes on' if full_prefix
                                     else 'both start the same way and the first is shorter')})
    return out


def repetitions(ws, ss, window: float = 20.0):
    """The same sentence (80%+ of the words) said twice within `window` seconds: two complete takes."""
    out = []
    for i, a in enumerate(ss):
        ta = [w['n'] for w in ws[a['first']:a['last'] + 1]]
        for b in ss[i + 1:]:
            if b['start'] - a['end'] > window:
                break
            tb = [w['n'] for w in ws[b['first']:b['last'] + 1]]
            r = difflib.SequenceMatcher(None, ta, tb).ratio()
            if len(ta) >= 3 and r >= 0.8:
                out.append({'first': a['id'], 'second': b['id'], 'similarity': round(r, 2)})
    return out


def analyze(transcript: dict, media, out_dir) -> dict:
    out_dir = Path(out_dir)
    ws = load_words(transcript)
    ss = sentences(ws)
    env = envelope_db(media)
    floor = round(float(np.percentile(env, 10)), 1) if env is not None else None
    unworded = mark_sound(ws, env, floor)
    for k, s in enumerate(ss):
        s['level_db'], s['peak_db'] = level(env, s['start'], s['end'])
        s['words_per_s'] = round((s['last'] - s['first'] + 1) / max(0.01, s['end'] - s['start']), 2)
        s['pause_before'] = round(s['start'] - ss[k - 1]['end'], 2) if k else round(s['start'], 2)
        s['pause_after'] = round(ss[k + 1]['start'] - s['end'], 2) if k + 1 < len(ss) else None
    pauses = []
    for a, b in zip(ws, ws[1:]):
        d = round(b['s'] - a['e'], 2)
        if d < 0.25:
            continue
        emph = a['w'][-1] in END_PUNCT + ':' and d >= 0.3
        pauses.append({'id': f'p{len(pauses) + 1:02d}', 'start': a['e'], 'end': b['s'], 'dur': d, 'class': pause_class(d),
                       'after': a['w'], 'before': b['w'], 'after_index': a['i'], 'emphasis_candidate': emph})
    levels = [s['level_db'] for s in ss if s['level_db'] is not None]
    result = {
        'source': {'media': str(Path(media).name) if media else None, 'language': transcript.get('language'),
                   'duration': transcript.get('duration'), 'speech_end': round(ws[-1]['e'], 2) if ws else 0,
                   'noise_floor_db': floor, 'voice_db': round(sum(levels) / len(levels), 1) if levels else None},
        'words': ws,
        'sentences': ss,
        'pauses': pauses,
        'retakes': retakes(ws, ss),
        'repetitions': repetitions(ws, ss),
        'hesitations': [{'word': w['w'], 'at': w['s'], 'i': w['i']} for w in ws if w['hes']],
        'negations': [{'word': w['w'], 'at': w['s'], 'i': w['i']} for w in ws if w['neg']],
        'uncertain': [{'word': w['w'], 'at': w['s'], 'prob': w['p']} for w in ws if w['p'] < UNCERTAIN],
        'silent_words': [{'word': w['w'], 'at': w['s']} for w in ws if w.get('silent')],
        'unworded_sound': unworded,
    }
    write_json(out_dir / 'analysis.json', result)
    L = [f'# Recording analysis', '',
         f"Speech until {result['source']['speech_end']} s · language {result['source']['language']} · "
         f"{len(ss)} sentences · {len(pauses)} pauses of 0.25 s or more", '',
         '| Sentence | Time | Text | Level | Pause after |', '|---|---|---|---|---|']
    L += [f"| {s['id']} | {s['start']:.2f}-{s['end']:.2f} | {s['text']} | {s['level_db']} dB | {s['pause_after']} |" for s in ss]
    L += ['', '## Pauses', ''] + [f"- {p['id']} {p['start']:.2f}-{p['end']:.2f} ({p['dur']} s, {p['class']})"
                                 f"{' · emphasis candidate' if p['emphasis_candidate'] else ''}: after \"{p['after']}\"" for p in pauses]
    L += ['', '## Retakes and repetitions', '']
    L += [f"- retake: {r['incomplete']} → {r['redone']} ({r['confidence']}: {r['evidence']})" for r in result['retakes']]
    L += [f"- repetition: {r['first']} and {r['second']} ({r['similarity']})" for r in result['repetitions']] or ['- no repetition']
    L += ['', '## Hesitations, negations, uncertain words', '',
          '- hesitations: ' + (', '.join(f"\"{h['word']}\" {h['at']:.2f}" for h in result['hesitations']) or 'none'),
          '- negations: ' + (', '.join(f"\"{h['word']}\" {h['at']:.2f}" for h in result['negations']) or 'none'),
          '- uncertain: ' + (', '.join(f"\"{h['word']}\" {h['at']:.2f} ({h['prob']})" for h in result['uncertain']) or 'none'),
          '- text over silence (transcription artifact): ' + (', '.join(f"\"{h['word']}\" {h['at']:.2f}" for h in result['silent_words']) or 'none'),
          '- audible sound without words (kept): ' + (', '.join(f"{u['start']:.2f}-{u['end']:.2f}" for u in unworded) or 'none')]
    (out_dir / 'analysis.md').write_text('\n'.join(L) + '\n', encoding='utf-8')
    return result
