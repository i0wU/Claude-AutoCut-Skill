"""Captions from word timestamps: grouping, SRT file and burned-in captions (Pillow + FFmpeg overlay).

Every spoken word that stays in the video appears exactly once, in order (negations included). Text is
drawn with Pillow from a bundled OFL font, so it does not depend on fontconfig or libass.
"""
from __future__ import annotations

import tempfile
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from .common import END_PUNCT, AutoCutError, need_tool, norm, probe, run, write_json

FONT = Path(__file__).resolve().parent / 'cartoon_template' / 'fonts' / 'Anton-Regular.ttf'
MIN_DUR = 0.6     # a caption shorter than this is hard to read: it borrows time from the following silence
GAP_BREAK = 0.45  # a pause this long starts a new caption


def group_words(words, max_chars: int, max_words: int = 6):
    """words: [{'w','s','e'}] on the output timeline → captions [{'start','end','text','words'}]."""
    caps, cur = [], []
    for k, w in enumerate(words):
        if cur:
            text = ' '.join(x['w'] for x in cur + [w])
            gap = w['s'] - cur[-1]['e']
            if len(text) > max_chars or len(cur) >= max_words or gap > GAP_BREAK or cur[-1]['w'][-1] in END_PUNCT:
                caps.append(cur)
                cur = []
        cur.append(w)
    if cur:
        caps.append(cur)
    out = [{'start': c[0]['s'], 'end': c[-1]['e'], 'text': ' '.join(x['w'] for x in c), 'words': [x['w'] for x in c]}
           for c in caps]
    for k, c in enumerate(out):
        nxt = out[k + 1]['start'] if k + 1 < len(out) else c['end'] + MIN_DUR
        if c['end'] - c['start'] < MIN_DUR:
            c['end'] = min(c['start'] + MIN_DUR, nxt)
        c['end'] = max(c['end'], c['start'] + 0.05)
    return out


def srt(caps) -> str:
    def ts(t):
        ms = int(round(t * 1000))
        h, ms = divmod(ms, 3600000)
        m, ms = divmod(ms, 60000)
        s, ms = divmod(ms, 1000)
        return f'{h:02d}:{m:02d}:{s:02d},{ms:03d}'
    return '\n'.join(f"{k + 1}\n{ts(c['start'])} --> {ts(c['end'])}\n{c['text']}\n" for k, c in enumerate(caps))


def check_complete(words, caps):
    """Every word appears once and in order; negations are counted separately."""
    a = [norm(w['w']) for w in words]
    b = [norm(x) for c in caps for x in c['words']]
    return {'words_expected': len(a), 'words_in_captions': len(b), 'same_sequence': a == b}


def style_for(width: int, height: int, size: float | None = None, y: float | None = None):
    vertical = height > width
    fs = int(size or round(0.068 * min(width, height) * (1.0 if vertical else 0.95)))
    return {'font_size': fs, 'max_width': int(width * 0.86), 'center_y': y if y is not None else (0.70 if vertical else 0.86),
            'max_chars': 22 if vertical else 36, 'uppercase': vertical}


def _wrap(draw, text, font, max_w):
    lines, cur = [], ''
    for word in text.split():
        t = f'{cur} {word}'.strip()
        if draw.textlength(t, font=font) <= max_w or not cur:
            cur = t
        else:
            lines.append(cur)
            cur = word
    if cur:
        lines.append(cur)
    return lines


def caption_png(text, width, band_h, st, path):
    img = Image.new('RGBA', (width, band_h), (0, 0, 0, 0))
    if text:
        d = ImageDraw.Draw(img)
        font = ImageFont.truetype(str(FONT), st['font_size'])
        t = text.upper() if st['uppercase'] else text
        lines = _wrap(d, t, font, st['max_width'])
        lh = int(st['font_size'] * 1.15)
        y = (band_h - lh * len(lines)) // 2
        stroke = max(2, st['font_size'] // 14)
        for ln in lines:
            x = (width - d.textlength(ln, font=font)) / 2
            d.text((x, y), ln, font=font, fill='white', stroke_width=stroke, stroke_fill='black')
            y += lh
    img.save(path)


def burn(video, caps, out_mp4, st) -> Path:
    """Overlay the captions on `video`; audio is copied unchanged."""
    info = probe(video)
    W, H, fps = info['video']['width'], info['video']['height'], info['video']['fps']
    band_h = int(st['font_size'] * 1.15 * 2 + st['font_size'])
    top = int(H * st['center_y'] - band_h / 2)
    top = max(0, min(H - band_h, top))
    out_mp4 = Path(out_mp4)
    with tempfile.TemporaryDirectory(prefix='autocut-captions-') as tmp:
        tmp = Path(tmp)
        caption_png('', W, band_h, st, tmp / 'blank.png')
        # durations are differences of frame-snapped times, so the overlay never drifts from the speech
        fr = lambda t: round(t * fps) / fps  # noqa: E731
        items, t = [], 0.0
        for k, c in enumerate(caps):
            a, b = fr(c['start']), fr(c['end'])
            if b <= a:
                b = a + 1 / fps
            if a > t:
                items.append(('blank.png', a - t))
            caption_png(c['text'], W, band_h, st, tmp / f'c{k:05d}.png')
            items.append((f'c{k:05d}.png', b - max(a, t)))
            t = b
        end = info['duration']
        if end > t:
            items.append(('blank.png', end - t))
        lines = [f"file '{(tmp / n).as_posix()}'\nduration {d:.6f}" for n, d in items if d > 0]
        lines.append(f"file '{(tmp / items[-1][0]).as_posix()}'")
        (tmp / 'list.txt').write_text('\n'.join(lines) + '\n', encoding='utf-8')
        part = out_mp4.with_suffix('.partial.mp4')
        cmd = [need_tool('ffmpeg'), '-y', '-v', 'error', '-i', video, '-f', 'concat', '-safe', '0', '-i', tmp / 'list.txt',
               '-filter_complex', f'[1:v]fps={info["video"]["fps_fraction"]},format=rgba[c];[0:v][c]overlay=0:{top}:eof_action=pass:format=auto,format=yuv420p[v]',
               '-map', '[v]', '-map', '0:a?', '-c:a', 'copy', '-c:v', 'libx264', '-crf', '18', '-preset', 'medium',
               '-movflags', '+faststart', part]
        r = run(cmd)
        if r.returncode != 0 or not part.exists():
            part.unlink(missing_ok=True)
            raise AutoCutError(f'ffmpeg failed while burning captions: {r.stderr.strip()[-600:]}')
        part.replace(out_mp4)
    return out_mp4


def make_captions(words_out, video, out_dir, burn_in: bool = True, size=None, y=None, name='captioned.mp4') -> dict:
    """words_out: words already on the timeline of `video`. Writes captions.srt (+ captions.json, burned mp4)."""
    out_dir = Path(out_dir)
    info = probe(video)
    if not info['video']:
        raise AutoCutError('captions need a video track')
    st = style_for(info['video']['width'], info['video']['height'], size, y)
    caps = group_words(words_out, st['max_chars'])
    (out_dir / 'captions.srt').write_text(srt(caps), encoding='utf-8')
    check = check_complete(words_out, caps)
    short = sum(1 for c in caps if c['end'] - c['start'] < 0.5)
    write_json(out_dir / 'captions.json', {'style': st, 'check': check, 'under_0_5s': short, 'captions': caps})
    result = {'captions': len(caps), 'srt': str(out_dir / 'captions.srt'), 'check': check, 'under_0_5s': short}
    if burn_in:
        result['video'] = str(burn(video, caps, out_dir / name, st))
    return result
