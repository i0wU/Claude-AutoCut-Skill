"""Analysis and plan on a synthetic recording: what is cut, what is kept, and the gate."""
import json

import pytest
from conftest import DURATION, GHOST, SPEC, make_media, needs_ffmpeg, transcript

from claude_autocut import analyze as A
from claude_autocut import plan as P
from claude_autocut.common import hesitation_re, norm


def test_norm_and_fillers():
    assert norm('Éééééé') == 'ééé'
    assert norm('"Não,"') == 'não'
    assert hesitation_re('en').match('um')
    assert not hesitation_re('pt').match('um')      # "um" is a word in Portuguese
    assert hesitation_re('pt').match('hum')


@pytest.fixture
def project(tmp_path):
    media = make_media(tmp_path / 'rec.mp4', SPEC, DURATION)
    tr = transcript(SPEC + GHOST, DURATION)
    an = A.analyze(tr, media, tmp_path)
    return tmp_path, media, an


def kept_text(an, plan):
    rs = plan['ranges']
    return [w['w'] for w in an['words'] if any(r['start'] <= (w['s'] + w['e']) / 2 <= r['end'] for r in rs)]


@needs_ffmpeg
def test_analysis_finds_structure(project):
    _, _, an = project
    assert [r['confidence'] for r in an['retakes']] == ['high']
    assert [h['word'] for h in an['hesitations']] == ['Um,']
    assert [n['word'] for n in an['negations']] == ['not']
    assert [w['word'] for w in an['silent_words']] == ['Thanks', 'for', 'watching.']
    assert any(p['emphasis_candidate'] and p['dur'] > 1.5 for p in an['pauses'])


@needs_ffmpeg
def test_plan_cuts_conservatively(project):
    proj, media, an = project
    plan = P.build_plan(an, media, proj)
    assert plan['status'] == 'ok'
    kept = kept_text(an, plan)
    assert kept == ['Hello', 'everyone.', 'Today', 'I', 'will', 'show', 'you', 'this.', 'it', 'is', 'not', 'magic.']
    assert 'not' in kept                                   # negation never removed
    types = {d['type'] for d in plan['decisions']}
    assert types == {'technical'}
    # the long pause after "this." is shortened, never removed: some silence stays between the sentences
    this_end, it_start = 6.20, 9.00
    gap = [r for r in plan['ranges'] if r['start'] > this_end - 0.1]
    assert gap and gap[0]['start'] < it_start
    joined = sum(r['end'] - r['start'] for r in plan['ranges'])
    assert 5.0 < joined < 6.5                          # 4.1 s of speech + lead-in, two 0.45 s breaths, tail


@needs_ffmpeg
def test_unworded_sound_is_kept(tmp_path):
    media = make_media(tmp_path / 'rec.mp4', SPEC, DURATION, extra_sound=[(11.0, 11.6)])
    an = A.analyze(transcript(SPEC, DURATION), media, tmp_path)
    assert an['unworded_sound'] and abs(an['unworded_sound'][0]['start'] - 11.0) < 0.05
    plan = P.build_plan(an, media, tmp_path)
    assert any(r['start'] <= 11.3 <= r['end'] for r in plan['ranges'])
    assert any('without transcript' in r for r in plan['review'])


@needs_ffmpeg
def test_gate_blocks_high_impact_until_approved(project):
    proj, media, an = project
    ov = {'cuts': [{'start': 9.0, 'end': 10.3, 'reason': 'manual test cut'}]}
    plan = P.build_plan(an, media, proj, ov)
    assert plan['status'] == 'blocked'
    assert any('negation removed: not' in d['reason'] for d in plan['decisions'] if d['type'] == 'high_impact')
    (proj / 'overrides.json').write_text(json.dumps(ov), encoding='utf-8')
    with pytest.raises(Exception):
        P.add_approval(proj, 8.9, 10.4, '', 'no approver')
    P.add_approval(proj, 8.9, 10.4, 'user', 'asked to drop it')
    plan2 = P.build_plan(an, media, proj, P.load_overrides(proj))
    assert plan2['status'] == 'ok'
    assert 'not' not in kept_text(an, plan2)


@needs_ffmpeg
def test_keep_override_protects_filler(project):
    proj, media, an = project
    plan = P.build_plan(an, media, proj, {'keep': [{'start': 8.1, 'end': 8.7, 'reason': 'part of the joke'}]})
    assert 'Um,' in kept_text(an, plan)


@needs_ffmpeg
def test_repetition_tie_keeps_both(tmp_path):
    spec = [('This', 1.0, 1.3), ('is', 1.35, 1.5), ('the', 1.55, 1.7), ('point.', 1.75, 2.2),
            ('This', 3.0, 3.3), ('is', 3.35, 3.5), ('the', 3.55, 3.7), ('point.', 3.75, 4.2)]
    media = make_media(tmp_path / 'rec.mp4', spec, 5.0)
    an = A.analyze(transcript(spec, 5.0), media, tmp_path)
    plan = P.build_plan(an, media, tmp_path)
    assert len(kept_text(an, plan)) == 8                    # never "the last one" by default
    assert any('both kept' in r for r in plan['review'])


@needs_ffmpeg
def test_drifted_word_is_not_called_silent(tmp_path):
    # the audio has a tone (speech) at 1.0-1.6, but Whisper placed the second word at 1.75-1.95, in silence
    audio_spec = [('Hello', 1.0, 1.6)]
    media = make_media(tmp_path / 'rec.mp4', audio_spec, 4.0)
    tr = transcript([('Hello', 1.0, 1.3), ('everyone.', 1.75, 1.95)], 4.0)
    an = A.analyze(tr, media, tmp_path)
    assert an['silent_words'] == []
    plan = P.build_plan(an, media, tmp_path)
    assert kept_text(an, plan) == ['Hello', 'everyone.']
