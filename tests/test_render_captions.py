"""End-to-end Auto Edit on synthetic media with a fixture transcript (no speech model): render, captions,
versioning and the integrity of the outputs."""
import json
import subprocess

import pytest
from conftest import DURATION, GHOST, SPEC, make_media, needs_ffmpeg, transcript

from claude_autocut import captions as CAP
from claude_autocut.common import AutoCutError, probe
from claude_autocut.edit import run_edit


def stream_duration(path, kind):
    out = subprocess.run(['ffprobe', '-v', 'error', '-select_streams', kind, '-show_entries', 'stream=duration',
                          '-of', 'csv=p=0', str(path)], capture_output=True, text=True).stdout.strip()
    return float(out)


@needs_ffmpeg
def test_edit_end_to_end(tmp_path):
    media = make_media(tmp_path / 'rec.mp4', SPEC, DURATION, size='360x640')
    src_bytes = media.read_bytes()
    tr = tmp_path / 'transcript.json'
    tr.write_text(json.dumps(transcript(SPEC + GHOST, DURATION)), encoding='utf-8')
    proj = tmp_path / 'proj'
    r = run_edit(media, proj, transcript=tr, log=lambda *a: None)
    cut, final = proj / 'renders' / 'cut_v1.mp4', proj / 'renders' / 'final_v1.mp4'
    assert cut.exists() and final.exists() and (proj / 'captions_v1.srt').exists() and (proj / 'REPORT.md').exists()
    assert media.read_bytes() == src_bytes                        # the source is never modified
    tl = json.loads((proj / 'renders' / 'cut_v1.timeline.json').read_text(encoding='utf-8'))
    v, a = stream_duration(cut, 'v'), stream_duration(cut, 'a')
    assert abs(v - tl['duration']) < 0.04 and abs(a - v) < 0.03   # no drift between audio and video
    assert probe(final)['video']['width'] == 360
    caps = json.loads((proj / 'captions_v1.json').read_text(encoding='utf-8'))
    assert caps['check']['same_sequence'] is True                 # every kept word once, in order
    text = ' '.join(c['text'] for c in caps['captions'])
    assert 'not' in text and 'Thanks' not in text and 'Um' not in text
    # a second run never overwrites: it renders version 2
    r2 = run_edit(media, proj, transcript=tr, captions=False, log=lambda *a: None)
    assert r2['version'] == 2 and (proj / 'renders' / 'cut_v2.mp4').exists() and cut.exists()


@needs_ffmpeg
def test_edit_stops_at_gate(tmp_path):
    media = make_media(tmp_path / 'rec.mp4', SPEC, DURATION)
    tr = tmp_path / 't.json'
    tr.write_text(json.dumps(transcript(SPEC, DURATION)), encoding='utf-8')
    proj = tmp_path / 'proj'
    proj.mkdir()
    (proj / 'overrides.json').write_text(json.dumps({'cuts': [{'start': 9.0, 'end': 10.3, 'reason': 'test'}]}), encoding='utf-8')
    with pytest.raises(AutoCutError, match='gate'):
        run_edit(media, proj, transcript=tr, log=lambda *a: None)
    assert not (proj / 'renders' / 'cut_v1.mp4').exists()


def test_caption_grouping_rules():
    ws = [{'w': x, 's': i * 0.3, 'e': i * 0.3 + 0.25} for i, x in enumerate('we do not cut words from captions ever.'.split())]
    caps = CAP.group_words(ws, max_chars=14)
    assert CAP.check_complete(ws, caps)['same_sequence']
    assert all(len(c['text']) <= 14 or len(c['words']) == 1 for c in caps)
    assert all(c['end'] - c['start'] >= 0.25 for c in caps)
    srt = CAP.srt(caps)
    assert srt.startswith('1\n00:00:00,000 --> ') and 'not' in srt


def test_missing_file_is_a_clear_error(tmp_path):
    with pytest.raises(AutoCutError, match='not found'):
        probe(tmp_path / 'nope.mp4')
