"""Shared helpers: JSON files, hashing, ffprobe, word normalization, negations and hesitations."""
from __future__ import annotations

import hashlib
import json
import re
import shutil
import subprocess
import unicodedata
from pathlib import Path

# Words whose loss changes the meaning of a sentence. A cut that removes one of them without the same
# word surviving nearby is always "high impact" and needs explicit approval.
NEGATIONS = {
    # Portuguese
    'não', 'nao', 'nunca', 'nem', 'jamais', 'nada', 'ninguém', 'ninguem', 'nenhum', 'nenhuma',
    # English
    'no', 'not', "don't", 'dont', "doesn't", 'doesnt', "didn't", 'didnt', "isn't", 'isnt', "aren't", 'arent',
    "wasn't", 'wasnt', "weren't", 'werent', "won't", 'wont', "can't", 'cant', 'cannot', "couldn't", 'couldnt',
    "shouldn't", 'shouldnt', "wouldn't", 'wouldnt', 'never', 'nothing', 'nobody', 'none', 'nor', 'neither',
    # Spanish
    'nadie', 'ninguno', 'ninguna', 'tampoco',
}

# Filler sounds. "um" is a filler in English but the word "one/a" in Portuguese, so it is language dependent.
_HES_COMMON = r'e{2,}|é{2,}|ê{2,}|a{2,}|ã{2,}|hã+|ah+n*|ahm+|hum+|hm+|uh+m*|eh+|éh+|er+m*|mm+'
_HES_BY_LANG = {'en': r'|um+|uhm+', 'es': r'|este+|em+'}
END_PUNCT = '.?!…'


def hesitation_re(language: str | None) -> re.Pattern:
    extra = _HES_BY_LANG.get((language or '')[:2], '')
    return re.compile(rf'^({_HES_COMMON}{extra})$')


def norm(word: str) -> str:
    """Lowercase, keep letters/digits/apostrophes/hyphens, squash 3+ repeated letters ("ééééé" == "ééé")."""
    w = word.lower().replace('’', "'")
    w = re.sub(r"[^\w'-]", '', w)
    w = w.strip("'-")
    return re.sub(r'(.)\1{2,}', r'\1\1\1', w)


def strip_accents(w: str) -> str:
    return ''.join(ch for ch in unicodedata.normalize('NFKD', w) if not unicodedata.combining(ch))


def read_json(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def write_json(path, data):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(json.dumps(data, ensure_ascii=False, indent=1) + '\n', encoding='utf-8')


def sha256(path) -> str:
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for block in iter(lambda: f.read(1 << 20), b''):
            h.update(block)
    return h.hexdigest()


class AutoCutError(Exception):
    """A user-facing error: printed without a traceback."""


def need_tool(name: str) -> str:
    path = shutil.which(name)
    if not path:
        raise AutoCutError(f'{name} was not found on PATH. Install FFmpeg (ffmpeg and ffprobe) and try again.')
    return path


def run(cmd, **kw):
    return subprocess.run([str(c) for c in cmd], capture_output=True, text=True, encoding='utf-8', errors='replace', **kw)


def probe(media) -> dict:
    """Duration, size, frame rate and audio of a media file (ffprobe)."""
    media = Path(media)
    if not media.is_file():
        raise AutoCutError(f'file not found: {media}')
    r = run([need_tool('ffprobe'), '-v', 'error', '-print_format', 'json', '-show_format', '-show_streams', media])
    if r.returncode != 0:
        raise AutoCutError(f'ffprobe could not read {media.name}: {r.stderr.strip()[:300]}')
    d = json.loads(r.stdout)
    v = next((s for s in d['streams'] if s['codec_type'] == 'video'), None)
    a = next((s for s in d['streams'] if s['codec_type'] == 'audio'), None)
    info = {'duration': float(d['format'].get('duration', 0) or 0), 'video': None, 'audio': None}
    if v:
        num, den = (int(x) for x in (v.get('avg_frame_rate') or v.get('r_frame_rate') or '30/1').split('/'))
        if not num or not den:
            num, den = (int(x) for x in v.get('r_frame_rate', '30/1').split('/'))
        w, h = int(v['width']), int(v['height'])
        rot = 0
        for sd in v.get('side_data_list', []) or []:
            if 'rotation' in sd:
                rot = int(sd['rotation'])
        if abs(rot) in (90, 270):
            w, h = h, w
        info['video'] = {'codec': v.get('codec_name'), 'width': w, 'height': h, 'fps': num / den if den else 30.0,
                         'fps_fraction': f'{num}/{den}'}
    if a:
        info['audio'] = {'codec': a.get('codec_name'), 'sample_rate': int(a.get('sample_rate', 0) or 0),
                         'channels': a.get('channels')}
    return info


def fmt_time(t: float) -> str:
    m, s = divmod(max(0.0, t), 60)
    return f'{int(m)}:{s:05.2f}'
