"""Render the EDL with FFmpeg: kept ranges, snapped to the video frame grid, joined with tiny audio fades."""
from __future__ import annotations

from pathlib import Path

from .common import AutoCutError, need_tool, probe, run, write_json

FADE = 0.008   # seconds of audio fade at every join (removes clicks, inaudible otherwise)


def snap(ranges, fps: float, duration: float):
    """Snap range edges to whole frames so audio and video keep the same length on every segment (no drift)."""
    out = []
    for r in ranges:
        a = round(r['start'] * fps) / fps
        b = min(round(r['end'] * fps) / fps, int(duration * fps) / fps)
        if b - a >= 2 / fps:
            out.append((a, b))
    return out


def timeline(ranges_snapped):
    """[{src_start, src_end, out_start, out_end}] for mapping source times to the edited video."""
    out, t = [], 0.0
    for a, b in ranges_snapped:
        out.append({'src_start': round(a, 4), 'src_end': round(b, 4), 'out_start': round(t, 4), 'out_end': round(t + b - a, 4)})
        t += b - a
    return out


def src_to_out(tl, t: float):
    """Edited-video time of source time `t`, or None if `t` was cut."""
    for s in tl:
        if s['src_start'] - 1e-3 <= t <= s['src_end'] + 1e-3:
            return s['out_start'] + min(max(t - s['src_start'], 0.0), s['src_end'] - s['src_start'])
    return None


def render_cut(media, plan: dict, out_mp4, crf: int = 18, preset: str = 'medium') -> dict:
    media, out_mp4 = Path(media), Path(out_mp4)
    if plan.get('status') != 'ok':
        raise AutoCutError('the plan is blocked by high-impact cuts without approval; see decisions.md '
                           '(record an approval with `approve`, or remove the cut from overrides.json)')
    info = probe(media)
    if not info['video']:
        raise AutoCutError(f'{media.name} has no video track')
    fps = info['video']['fps']
    rs = snap(plan['ranges'], fps, info['duration'])
    if not rs:
        raise AutoCutError('the plan keeps nothing')
    has_audio = info['audio'] is not None
    parts, labels = [], []
    for k, (a, b) in enumerate(rs):
        parts.append(f'[0:v]trim=start={a:.6f}:end={b:.6f},setpts=PTS-STARTPTS[v{k}]')
        lab = f'[v{k}]'
        if has_audio:
            d = b - a
            f = min(FADE, d / 4)
            parts.append(f'[0:a]atrim=start={a:.6f}:end={b:.6f},asetpts=PTS-STARTPTS,'
                         f'afade=t=in:d={f:.4f},afade=t=out:st={d - f:.6f}:d={f:.4f}[a{k}]')
            lab += f'[a{k}]'
        labels.append(lab)
    parts.append(''.join(labels) + f"concat=n={len(rs)}:v=1:a={1 if has_audio else 0}[v]" + ('[a]' if has_audio else ''))
    out_mp4.parent.mkdir(parents=True, exist_ok=True)
    tmp = out_mp4.with_suffix('.partial.mp4')
    cmd = [need_tool('ffmpeg'), '-y', '-v', 'error', '-i', media, '-filter_complex', ';'.join(parts), '-map', '[v]']
    if has_audio:
        cmd += ['-map', '[a]', '-c:a', 'aac', '-b:a', '192k', '-ar', str(info['audio']['sample_rate'] or 48000)]
    cmd += ['-c:v', 'libx264', '-preset', preset, '-crf', str(crf), '-pix_fmt', 'yuv420p',
            '-r', info['video']['fps_fraction'], '-movflags', '+faststart', tmp]
    r = run(cmd)
    if r.returncode != 0 or not tmp.exists():
        tmp.unlink(missing_ok=True)
        raise AutoCutError(f'ffmpeg failed while rendering the cut: {r.stderr.strip()[-600:]}')
    tmp.replace(out_mp4)
    tl = timeline(rs)
    meta = {'source': media.name, 'output': out_mp4.name, 'fps': fps, 'segments': tl,
            'duration': round(tl[-1]['out_end'], 4)}
    write_json(out_mp4.with_suffix('.timeline.json'), meta)
    return meta
