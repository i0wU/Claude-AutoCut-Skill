"""Cartoon project creation, storyboard checks and the generated composition (no HyperFrames render here;
set AUTOCUT_RENDER_TESTS=1 with Node.js installed to also render a short range)."""
import json
import os
import shutil

import pytest
from conftest import SPEC, make_media, needs_ffmpeg, transcript

from claude_autocut import cartoon as C
from claude_autocut.common import AutoCutError


@pytest.fixture
def proj(tmp_path):
    media = make_media(tmp_path / 'rec.mp4', SPEC, 11.0, size='360x640')
    tr = tmp_path / 't.json'
    tr.write_text(json.dumps(transcript(SPEC, 11.0)), encoding='utf-8')
    return C.init(media, tmp_path / 'cartoon', transcript=tr, install_gsap=False, log=lambda *a: None)


def scene(i, t0, t1, **kw):
    return {'id': f's{i}', 't0': t0, 't1': t1, 'cenario': {'nome': 'quarto'},
            'atores': [{'nome': 'criador', 'x': 520, 'y': 905, 'partes': True, 'fala': True,
                        'chaves': [{'t': t0, 'pose': 'explica', 'rosto': 'feliz'}]}], **kw}


def write_sb(proj, scenes):
    sb = json.loads((proj / 'storyboard.json').read_text(encoding='utf-8'))
    sb['cenas'] = scenes
    (proj / 'storyboard.json').write_text(json.dumps(sb), encoding='utf-8')


@needs_ffmpeg
def test_init_creates_project(proj):
    for p in ('assets/source.mp4', 'source.json', 'config.json', 'transcript.json', 'speech.md', 'storyboard.json',
              'data/words.js', 'data/envelope.js', 'engine/core.js', 'library/palco.js', 'fonts/Anton-Regular.ttf',
              'engine/LICENSE-drawn-by-code.txt', 'fonts/OFL-Anton.txt', 'package.json'):
        assert (proj / p).exists(), p
    pkg = json.loads((proj / 'package.json').read_text(encoding='utf-8'))
    assert pkg['dependencies'] == {'gsap': '3.14.2'}
    assert 'hyperframes@0.8.79' in pkg['scripts']['render']
    assert 'Hello' in (proj / 'speech.md').read_text(encoding='utf-8')
    with pytest.raises(AutoCutError, match='not empty'):
        C.init(proj / 'assets' / 'source.mp4', proj, install_gsap=False)


@needs_ffmpeg
def test_storyboard_check(proj):
    assert not C.check_storyboard(proj)['ok']                       # empty storyboard
    write_sb(proj, [scene(1, 0.0, 5.0), scene(2, 5.0, 11.0, textos=[{'t': 9.4, 'ate': 10.2, 'txt': 'NOT|MAGIC', 'x': 600, 'y': 350, 'tam': 80}])])
    r = C.check_storyboard(proj)
    assert r['ok'], r['errors']
    write_sb(proj, [scene(1, 0.0, 4.0), scene(2, 5.0, 11.0)])        # gap
    assert any('previous scene ends' in e for e in C.check_storyboard(proj)['errors'])
    write_sb(proj, [scene(1, 0.0, 11.0, objetos=[{'tipo': 'dragon', 'x': 1, 'y': 1}])])
    assert any('unknown object' in e for e in C.check_storyboard(proj)['errors'])
    write_sb(proj, [scene(1, 0.0, 11.0, textos=[{'t': 1.0, 'ate': 2.0, 'txt': 'FREE MONEY', 'x': 600, 'y': 350, 'tam': 80}])])
    assert any('not spoken' in e for e in C.check_storyboard(proj)['errors'])


@needs_ffmpeg
def test_composition_html(proj):
    write_sb(proj, [scene(1, 0.0, 11.0)])
    with pytest.raises(AutoCutError, match='GSAP'):
        C.build_html(proj)
    g = proj / 'node_modules' / 'gsap' / 'dist'
    g.mkdir(parents=True)
    (g / 'gsap.min.js').write_text('/* placeholder for the test */', encoding='utf-8')
    html = C.build_html(proj).read_text(encoding='utf-8')
    assert 'data-composition-id="autocut-cartoon"' in html and 'window.__timelines["autocut-cartoon"]' in html
    for s in C.scripts(proj):
        assert (proj / s).exists(), s


@needs_ffmpeg
@pytest.mark.skipif(os.environ.get('AUTOCUT_RENDER_TESTS') != '1' or not shutil.which('npx'), reason='render test is opt-in')
def test_render_short_range(tmp_path):
    media = make_media(tmp_path / 'rec.mp4', SPEC, 11.0, size='360x640')
    tr = tmp_path / 't.json'
    tr.write_text(json.dumps(transcript(SPEC, 11.0)), encoding='utf-8')
    p = C.init(media, tmp_path / 'cartoon', transcript=tr, log=lambda *a: None)
    write_sb(p, [scene(1, 0.0, 11.0)])
    qc = C.render(p, span=(0.0, 2.0), workers=1, log=lambda *a: None)
    assert qc['duration_ok']
