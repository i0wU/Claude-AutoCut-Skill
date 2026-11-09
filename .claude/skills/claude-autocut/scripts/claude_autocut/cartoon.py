"""Cartoon mode: an animated paper-cutout scene on top, a torn-paper divider and the speaker's video below
(1080x1920). The scene follows the speech through a storyboard; HyperFrames renders it; the source audio is
copied into the final file unchanged.

Project folder:
  assets/source.mp4        copy of the video (SHA-256 checked); never modified
  source.json, config.json properties of the video and the layout
  transcript.json          word-level transcript; data/words.js and data/envelope.js feed the stage
  speech.md                the speech in blocks with times (read this to write the storyboard)
  storyboard.json          scenes, characters, objects and texts on the source timeline (written by Claude)
  scenes/*.js              optional project-specific drawings (same API as library/*.js)
  engine/, library/, fonts/ copied from the template; package.json pins GSAP for the timeline
  renders/cartoon_vN.mp4   renders, never overwritten
"""
from __future__ import annotations

import json
import re
import shutil
import subprocess
import time
from pathlib import Path

import numpy as np

from .common import AutoCutError, need_tool, norm, probe, read_json, run, sha256, strip_accents, write_json
from .transcribe import DEFAULT_MODEL, transcribe

TEMPLATE = Path(__file__).resolve().parent / 'cartoon_template'
HYPERFRAMES = 'hyperframes@0.8.79'   # pinned: never updated automatically
GSAP_VERSION = '3.14.2'
FIRST = ['texto.js', 'divisoria.js', 'palco.js']
BLOCK_PAUSE, BLOCK_WORDS = 0.45, 14


def npx() -> str:
    for n in ('npx.cmd', 'npx') if shutil.which('npx.cmd') else ('npx',):
        c = shutil.which(n)
        if c:
            return c
    raise AutoCutError('npx (Node.js) was not found. The cartoon mode needs Node.js 18 or newer.')


def npm() -> str:
    for n in ('npm.cmd', 'npm') if shutil.which('npm.cmd') else ('npm',):
        c = shutil.which(n)
        if c:
            return c
    raise AutoCutError('npm (Node.js) was not found. The cartoon mode needs Node.js 18 or newer.')


def hf(proj, args, timeout=3600):
    return subprocess.run([npx(), '--yes', HYPERFRAMES, *args], cwd=proj, capture_output=True, text=True,
                          encoding='utf-8', errors='replace', timeout=timeout)


def default_config(info) -> dict:
    v = info['video']
    vertical = v['height'] >= v['width']
    return {
        'frame': {'width': 1080, 'height': 1920, 'fps': 30},
        'top': {'height': 950, 'logical_width': 1200},
        'divider': {'y': 950, 'thickness': 30, 'seed': 'divider-1'},
        # vertical source: a 1080-wide window at face height; horizontal source: cover the lower box
        'video': {'y': 950, 'scale': 1080 / v['width'], 'crop_y': 0.20, 'fit': 'window' if vertical else 'cover'},
        'grain': 0.32, 'background': '#2a1826',
    }


def blocks_of(words):
    """Speech blocks (units of meaning for the storyboard): break at pauses or sentence ends; long blocks split."""
    blocks, cur = [], []
    for i, w in enumerate(words):
        cur.append(w)
        nxt = words[i + 1] if i + 1 < len(words) else None
        gap = (nxt['s'] - w['e']) if nxt else 99
        if nxt is None or gap >= BLOCK_PAUSE or (w['w'][-1:] in '.?!' and len(cur) >= 4):
            blocks.append(cur)
            cur = []

    def split(b):
        if len(b) <= BLOCK_WORDS:
            return [b]
        k = max(range(4, len(b) - 3), key=lambda j: (round(b[j]['s'] - b[j - 1]['e'], 2), b[j - 1]['w'][-1:] in ',;:'))
        return split(b[:k]) + split(b[k:])

    out = [p for b in blocks for p in split(b)]
    return [{'id': f'b{n + 1:02d}', 't0': b[0]['s'], 't1': b[-1]['e'], 'speech': ' '.join(w['w'] for w in b),
             'uncertain': [w['w'] for w in b if w['p'] < 0.5]} for n, b in enumerate(out)]


def voice_envelope(media, fps) -> list:
    """Voice energy per frame, 0..1 (95th percentile = 1): the speaking character's mouth follows it."""
    r = subprocess.run(['ffmpeg', '-v', 'error', '-i', str(media), '-map', '0:a:0', '-ac', '1', '-ar', '16000',
                        '-f', 's16le', '-'], capture_output=True)
    if r.returncode != 0:
        raise AutoCutError('ffmpeg could not read the audio of the source')
    x = np.frombuffer(r.stdout[: len(r.stdout) // 2 * 2], np.int16).astype(np.float32) / 32768
    n = int(16000 / fps)
    if len(x) < n:
        return []
    rms = np.sqrt((x[: len(x) // n * n].reshape(-1, n) ** 2).mean(1))
    ref = float(np.percentile(rms, 95)) or 1.0
    return [round(float(v), 3) for v in np.clip(rms / ref, 0, 1)]


def init(video, proj, model=DEFAULT_MODEL, language=None, transcript=None, install_gsap=True, device='cpu', log=print):
    video, proj = Path(video).resolve(), Path(proj).resolve()
    info = probe(video)
    if not info['video'] or not info['audio']:
        raise AutoCutError('the cartoon mode needs a video with an audio track')
    if proj.exists() and any(proj.iterdir()):
        raise AutoCutError(f'{proj} exists and is not empty; use a new folder')
    for d in ('assets', 'data', 'scenes', 'renders', 'reviews'):
        (proj / d).mkdir(parents=True, exist_ok=True)
    for d in ('engine', 'library', 'fonts'):
        shutil.copytree(TEMPLATE / d, proj / d)
    digest = sha256(video)
    shutil.copy2(video, proj / 'assets' / 'source.mp4')
    if sha256(proj / 'assets' / 'source.mp4') != digest:
        raise AutoCutError('the copy of the source differs from the original; check the disk')
    write_json(proj / 'source.json', {'name': video.name, 'sha256': digest, **info})
    write_json(proj / 'config.json', default_config(info))
    (proj / 'package.json').write_text(json.dumps({
        'name': 'autocut-cartoon-project', 'private': True, 'type': 'module',
        'dependencies': {'gsap': GSAP_VERSION},
        'scripts': {'preview': f'npx --yes {HYPERFRAMES} preview', 'render': f'npx --yes {HYPERFRAMES} render'}}, indent=2) + '\n',
        encoding='utf-8')
    write_json(proj / 'hyperframes.json', {'paths': {'assets': 'assets'}, 'media': {'autoProxy': True}})
    log('transcript...')
    if transcript:
        tr = read_json(transcript)
        write_json(proj / 'transcript.json', tr)
    else:
        tr = transcribe(proj / 'assets' / 'source.mp4', proj / 'transcript.json', model=model, language=language, device=device)
    from . import analyze as A
    ws = A.load_words(tr)
    env_db = A.envelope_db(proj / 'assets' / 'source.mp4')
    floor = float(np.percentile(env_db, 10)) if env_db is not None else None
    unworded = A.mark_sound(ws, env_db, floor)
    # words transcribed over silence (a Whisper artifact) never reach the stage or the storyboard
    words = [{'w': w['w'], 's': round(w['s'], 3), 'e': round(w['e'], 3), 'p': round(w['p'], 3)} for w in ws if not w.get('silent')]
    (proj / 'data' / 'words.js').write_text('window.PALAVRAS = ' + json.dumps(words, ensure_ascii=False) + ';\n', encoding='utf-8')
    fps = default_config(info)['frame']['fps']
    env = voice_envelope(proj / 'assets' / 'source.mp4', fps)
    (proj / 'data' / 'envelope.js').write_text('window.ENVELOPE = ' + json.dumps({'fps': fps, 'v': env}) + ';\n', encoding='utf-8')
    blocks = blocks_of(words)
    L = ['# Speech', '', f'{len(words)} words, {info["duration"]:.2f} s. Times are on the source timeline.', '']
    L += [f"- **{b['id']}** {b['t0']:.2f}-{b['t1']:.2f}: {b['speech']}" + (f" _(uncertain: {', '.join(b['uncertain'])})_" if b['uncertain'] else '')
          for b in blocks]
    dropped = [w['w'] for w in ws if w.get('silent')]
    if dropped:
        L += ['', f"Dropped as text over silence (transcription artifact): {' '.join(dropped)}"]
    if unworded:
        L += ['', 'Audible sound without words: ' + ', '.join(f"{u['start']:.2f}-{u['end']:.2f}" for u in unworded)]
    (proj / 'speech.md').write_text('\n'.join(L) + '\n', encoding='utf-8')
    write_json(proj / 'storyboard.json', {'version': 1, 'subject': '', 'characters': {}, 'blocks': blocks, 'cenas': []})
    if install_gsap:
        log(f'installing gsap@{GSAP_VERSION} into the project (npm)...')
        r = run([npm(), 'install', '--no-audit', '--no-fund', '--loglevel=error'], cwd=proj, timeout=600)
        if r.returncode != 0:
            log(f'WARNING: npm install failed ({r.stderr.strip()[-300:]}); run `npm install` in {proj} before rendering')
    return proj


# --- storyboard check --------------------------------------------------------------------------------
def registered(proj) -> dict:
    names = {'scenarios': set(), 'actors': set(), 'objects': set()}
    files = list((proj / 'library').glob('*.js')) + list((proj / 'scenes').glob('*.js'))
    for f in files:
        s = f.read_text(encoding='utf-8')
        names['scenarios'] |= set(re.findall(r"Palco\.cenario\('(\w+)'", s))
        names['actors'] |= set(re.findall(r"Palco\.ator\('(\w+)'", s))
        names['objects'] |= set(re.findall(r"(?:Palco\.objeto|\bob)\('(\w+)'", s))
    return names


def check_storyboard(proj) -> dict:
    proj = Path(proj)
    sb = read_json(proj / 'storyboard.json')
    dur = read_json(proj / 'source.json')['duration']
    words = [w for w in read_json(proj / 'transcript.json')['words'] if w['text'].strip()]
    reg = registered(proj)
    errors, warnings = [], []
    scenes = sb.get('cenas') or []
    if not scenes:
        errors.append('storyboard.json has no scenes ("cenas"): write them from speech.md')
    prev_end = 0.0
    for k, c in enumerate(sorted(scenes, key=lambda c: c.get('t0', 0))):
        cid = c.get('id', f'#{k + 1}')
        t0, t1 = c.get('t0'), c.get('t1')
        if not isinstance(t0, (int, float)) or not isinstance(t1, (int, float)) or t1 <= t0:
            errors.append(f'{cid}: needs numbers t0 < t1')
            continue
        if abs(t0 - prev_end) > 0.05:
            errors.append(f'{cid}: starts at {t0:.2f} but the previous scene ends at {prev_end:.2f} (no gaps or overlaps)')
        prev_end = t1
        cen = c.get('cenario')
        cname = cen.get('nome') if isinstance(cen, dict) else cen
        if cname not in reg['scenarios']:
            errors.append(f'{cid}: unknown scenario {cname!r} (known: {sorted(reg["scenarios"])})')
        for a in c.get('atores', []):
            if a.get('nome') not in reg['actors']:
                errors.append(f"{cid}: unknown actor {a.get('nome')!r} (known: {sorted(reg['actors'])})")
            for key in a.get('chaves', []):
                if not (t0 - 0.05 <= key.get('t', -1) <= t1 + 0.05):
                    warnings.append(f"{cid}: key of {a.get('nome')} at {key.get('t')} is outside the scene")
        for o in c.get('objetos', []):
            if o.get('tipo') not in reg['objects']:
                errors.append(f"{cid}: unknown object {o.get('tipo')!r} (known: {sorted(reg['objects'])})")
        for tx in c.get('textos', []):
            spoken = {strip_accents(norm(w['text'])) for w in words if tx.get('t', 0) - 1.5 <= w['start'] <= tx.get('ate', tx.get('t', 0)) + 1.5}
            for piece in re.split(r'[\s|]+', tx.get('txt', '')):
                n = strip_accents(norm(piece))
                if n and n not in spoken:
                    errors.append(f"{cid}: on-screen text word {piece!r} is not spoken around {tx.get('t')} s "
                                  f"(on-screen text only uses words that are said)")
    if scenes and abs(prev_end - dur) > 0.15:
        errors.append(f'the last scene ends at {prev_end:.2f} s but the video lasts {dur:.2f} s')
    return {'errors': errors, 'warnings': warnings, 'scenes': len(scenes), 'ok': not errors}


# --- composition -----------------------------------------------------------------------------------
def scripts(proj):
    lst = [f'node_modules/gsap/dist/gsap.min.js'] + [f'engine/{n}' for n in ('core.js', 'paper.js', 'kit.js', 'detail.js')]
    lst += [f'library/{n}' for n in FIRST]
    lst += sorted(f'library/{p.name}' for p in (proj / 'library').glob('*.js') if p.name not in FIRST)
    lst += ['data/words.js', 'data/envelope.js', 'data/storyboard.js']
    lst += sorted(f'scenes/{p.name}' for p in (proj / 'scenes').glob('*.js'))
    return lst


def build_html(proj, span=None) -> Path:
    proj = Path(proj)
    cfg, src = read_json(proj / 'config.json'), read_json(proj / 'source.json')
    sb = read_json(proj / 'storyboard.json')
    if not sb.get('cenas'):
        raise AutoCutError('the storyboard has no scenes yet: write storyboard.json first')
    if not (proj / 'node_modules' / 'gsap' / 'dist' / 'gsap.min.js').exists():
        raise AutoCutError(f'GSAP is not installed in the project: run `npm install` in {proj}')
    (proj / 'data' / 'storyboard.js').write_text('window.STORYBOARD = ' + json.dumps(sb, ensure_ascii=False) + ';\n', encoding='utf-8')
    F, top, div, vid = cfg['frame'], cfg['top'], cfg['divider'], cfg['video']
    W, H = F['width'], F['height']
    total = round(src['duration'], 3)
    a, b = span if span else (0.0, total)
    dur = round(b - a, 3)
    sw, sh = src['video']['width'], src['video']['height']
    box_h = H - vid['y']
    if vid.get('fit') == 'cover':
        sc = max(W / sw, box_h / sh)
        vw, vh = sw * sc, sh * sc
        vx, vy = -(vw - W) / 2, -(vh - box_h) / 2
    else:
        sc = vid.get('scale', W / sw)
        vw, vh = sw * sc, sh * sc
        vx, vy = -(vw - W) / 2, -(vid.get('crop_y', 0.2) * vh)
    top_h = top['height']
    logical = [top['logical_width'], round(top['logical_width'] * top_h / W, 1)]
    div_h = 96
    start = {'canvas': 'topo', 'logico': logical, 'fps': F['fps'], 'duracao': dur, 'deslocamento': a,
             'fontes': [{'family': 'Anton', 'src': 'fonts/Anton-Regular.ttf'}, {'family': 'Hand', 'src': 'fonts/PatrickHand-Regular.ttf'}],
             'divisoria': {'canvas': 'divisoria', 'semente': div.get('seed', 'divider-1'), 'espessura': div.get('thickness', 30)},
             'grao': cfg.get('grain', 0.32), 'fundo': cfg.get('background', '#2a1826')}
    tags = '\n'.join(f'<script src="{s}"></script>' for s in scripts(proj))
    media = f'data-start="0" data-duration="{dur}"' + (f' data-media-start="{a}"' if a else '')
    page = f'''<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<!-- generated by Claude AutoCut (cartoon mode): edit storyboard.json, config.json or scenes/, not this file -->
<style>
@font-face {{ font-family: "Anton"; src: url("fonts/Anton-Regular.ttf"); }}
@font-face {{ font-family: "Hand"; src: url("fonts/PatrickHand-Regular.ttf"); }}
html, body {{ margin: 0; padding: 0; background: #1d1220; }}
#root {{ position: relative; width: 100%; height: 100%; overflow: hidden; background: #1d1220; }}
#topo {{ position: absolute; left: 0; top: 0; width: {W}px; height: {top_h}px; }}
#video-box {{ position: absolute; left: 0; top: {vid['y']}px; width: {W}px; height: {box_h}px; overflow: hidden; background: #1d1220; }}
#source-video {{ position: absolute; left: {vx:.1f}px; top: {vy:.1f}px; width: {vw:.1f}px; height: {vh:.1f}px; }}
#divisoria {{ position: absolute; left: 0; top: {div['y'] - div_h // 2}px; width: {W}px; height: {div_h}px; }}
</style>
</head>
<body>
<div id="root" data-composition-id="autocut-cartoon" data-width="{W}" data-height="{H}" data-duration="{dur}">
  <canvas id="topo" width="{W}" height="{top_h}"></canvas>
  <div id="video-box">
    <video id="source-video" src="assets/source.mp4" {media} muted playsinline></video>
  </div>
  <audio id="source-audio" src="assets/source.mp4" {media} data-volume="1"></audio>
  <canvas id="divisoria" width="{W}" height="{div_h}"></canvas>
</div>
{tags}
<script>
Palco.iniciar(Object.assign({json.dumps(start, ensure_ascii=False)}, {{ storyboard: window.STORYBOARD }}));
// the GSAP timeline only carries time to the stage; the stage paints every frame (also on hf-seek)
const clock = {{ t: 0 }};
const tl = gsap.timeline({{ paused: true }});
tl.to(clock, {{ t: {dur}, duration: {dur}, ease: 'none', onUpdate: () => Palco.desenhar(clock.t + {a}) }});
window.__timelines = window.__timelines || {{}};
window.__timelines["autocut-cartoon"] = tl;
</script>
</body>
</html>
'''
    out = proj / 'index.html'
    out.write_text(page, encoding='utf-8')
    return out


def next_name(folder: Path, stem: str) -> Path:
    n = 1
    while (folder / f'{stem}_v{n}.mp4').exists():
        n += 1
    return folder / f'{stem}_v{n}.mp4'


def lint(proj) -> dict:
    proj = Path(proj)
    build_html(proj)
    out = {}
    for cmd in ('lint', 'check'):
        r = hf(proj, [cmd, '--json'], timeout=900)
        out[cmd] = {'exit': r.returncode, 'stdout': (r.stdout or '')[-4000:], 'stderr': (r.stderr or '')[-1500:]}
    write_json(proj / 'reviews' / 'lint.json', out)
    return out


def snapshot(proj, at: str, name=None) -> Path:
    proj = Path(proj)
    build_html(proj)
    started = time.time() - 1
    r = hf(proj, ['snapshot', '--at', at], timeout=1800)
    if r.returncode != 0:
        raise AutoCutError(f'HyperFrames snapshot failed: {(r.stderr or r.stdout).strip()[-600:]}')
    dest = proj / 'reviews' / (name or time.strftime('frames-%Y%m%d-%H%M%S'))
    dest.mkdir(parents=True, exist_ok=True)
    snaps = sorted(p for p in (proj / 'snapshots').glob('*.png') if p.stat().st_mtime >= started) if (proj / 'snapshots').exists() else []
    for p in snaps:
        shutil.copy2(p, dest / p.name)
    return dest


def audio_md5(media) -> str | None:
    r = run([need_tool('ffmpeg'), '-v', 'error', '-i', media, '-map', '0:a:0', '-c', 'copy', '-f', 'md5', '-'])
    return r.stdout.strip() if r.returncode == 0 else None


def render(proj, span=None, workers=2, quality='standard', log=print) -> dict:
    proj = Path(proj).resolve()
    chk = check_storyboard(proj)
    if not chk['ok']:
        raise AutoCutError('the storyboard has errors; run `autocut cartoon check` and fix them:\n  ' + '\n  '.join(chk['errors']))
    build_html(proj, span)
    work = proj / 'renders' / 'work'
    work.mkdir(parents=True, exist_ok=True)
    raw = work / f'hf_{time.strftime("%Y%m%d-%H%M%S")}.mp4'
    log(f'rendering with {HYPERFRAMES} ({workers} workers)...')
    t0 = time.time()
    r = hf(proj, ['render', '--quality', quality, '--workers', str(workers), '--output', str(raw)], timeout=4 * 3600)
    if r.returncode != 0 or not raw.exists():
        raise AutoCutError(f'HyperFrames render failed (exit {r.returncode}): {(r.stderr or r.stdout).strip()[-800:]}')
    final = next_name(proj / 'renders', 'cartoon' + ('_range' if span else ''))
    source = proj / 'assets' / 'source.mp4'
    if span:
        a, b = span
        cmd = [need_tool('ffmpeg'), '-v', 'error', '-i', raw, '-ss', str(a), '-t', str(b - a), '-i', source,
               '-map', '0:v:0', '-map', '1:a:0', '-c:v', 'copy', '-c:a', 'aac', '-b:a', '192k', '-movflags', '+faststart', final]
    else:   # the source audio is copied without re-encoding: same sound, same start
        cmd = [need_tool('ffmpeg'), '-v', 'error', '-i', raw, '-i', source, '-map', '0:v:0', '-map', '1:a:0', '-c', 'copy',
               '-movflags', '+faststart', final]
    m = run(cmd)
    if m.returncode != 0:
        raise AutoCutError(f'joining the source audio failed: {m.stderr.strip()[-500:]}')
    info, src = probe(final), read_json(proj / 'source.json')
    expected = (span[1] - span[0]) if span else src['duration']
    qc = {'output': final.name, 'seconds': round(time.time() - t0, 1), 'duration': info['duration'],
          'expected_duration': round(expected, 3), 'duration_ok': abs(info['duration'] - expected) < 0.1,
          'size': [info['video']['width'], info['video']['height']], 'fps': info['video']['fps']}
    if not span:
        qc['audio_identical_to_source'] = audio_md5(final) == audio_md5(source)
    write_json(final.with_suffix('.qc.json'), qc)
    return qc
