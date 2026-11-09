"""Auto Edit mode: transcribe → analyze → plan (with the gate) → render → verify → captions → report.

Project folder layout (nothing outside it is written; the source video is only read):
  source.json            path, SHA-256 and properties of the source
  transcript.json        word-level transcript of the source
  analysis.json/.md      sentences, pauses, retakes, repetitions, fillers, negations
  overrides.json         optional manual decisions (cuts, keep, pauses, approvals)
  edl.json, decisions.md the plan: kept ranges and the reason for every removed span
  renders/cut_vN.mp4     the edit (never overwritten; every render gets a new version)
  renders/final_vN.mp4   the edit with burned-in captions
  captions_vN.srt        captions on the edited timeline
  verify_vN.json         re-transcription of the edit compared with the expected words
  REPORT.md              human-readable summary of the last run
"""
from __future__ import annotations

import difflib
from pathlib import Path

from . import analyze as A
from . import captions as CAP
from . import plan as P
from . import render as R
from .common import AutoCutError, fmt_time, norm, probe, read_json, sha256, strip_accents, write_json
from .transcribe import DEFAULT_MODEL, transcribe


def next_version(folder: Path, stem: str) -> int:
    n = 1
    while (folder / f'{stem}_v{n}.mp4').exists():
        n += 1
    return n


def prepare(video, project, model=DEFAULT_MODEL, language=None, transcript=None, device='cpu') -> tuple[dict, dict]:
    video, project = Path(video).resolve(), Path(project).resolve()
    info = probe(video)
    if not info['video']:
        raise AutoCutError(f'{video.name} has no video track')
    project.mkdir(parents=True, exist_ok=True)
    src = project / 'source.json'
    digest = sha256(video)
    if src.exists():
        old = read_json(src)
        if old.get('sha256') != digest:
            raise AutoCutError(f'{project} already belongs to another source video; use a new project folder')
    write_json(src, {'path': str(video), 'name': video.name, 'sha256': digest, **info})
    if transcript:   # a transcript made elsewhere (same JSON shape): used as is
        tr = read_json(transcript)
        write_json(project / 'transcript.json', tr)
    else:
        tr = transcribe(video, project / 'transcript.json', model=model, language=language, device=device)
    return info, tr


def kept_words_out(analysis, timeline):
    """Words that stay in the edit, with times on the edited timeline."""
    out = []
    for w in analysis['words']:
        m = (w['s'] + w['e']) / 2
        mo = R.src_to_out(timeline, m)
        if mo is None:
            continue
        s, e = R.src_to_out(timeline, w['s']), R.src_to_out(timeline, w['e'])
        s = mo - 0.05 if s is None else s
        e = mo + 0.05 if e is None else e
        out.append({'w': w['w'], 's': round(s, 3), 'e': round(e, 3), 'neg': w['neg'], 'hes': w['hes'], 'p': w['p']})
    return out


def verify(cut_mp4, expected, project, version, model, language, device='cpu') -> dict:
    """Transcribe the edit again and compare: no expected word may disappear, negations must match."""
    tr = transcribe(cut_mp4, Path(project) / f'transcript_cut_v{version}.json', model=model, language=language, device=device)
    key = lambda w: strip_accents(norm(w))  # noqa: E731
    a = [key(w['w']) for w in expected]
    b = [key(w['text']) for w in tr['words']]
    sm = difflib.SequenceMatcher(None, a, b, autojunk=False)
    missing, extra = [], []
    for op, i1, i2, j1, j2 in sm.get_opcodes():
        if op in ('delete', 'replace'):
            for w in expected[i1:i2]:
                if not w['hes'] and w['p'] >= 0.6:   # fillers and uncertain readings are not proof of a lost word
                    missing.append({'word': w['w'], 'at_edit': w['s']})
        if op in ('insert', 'replace'):
            extra += [x['text'] for x in tr['words'][j1:j2]]
    from .common import NEGATIONS
    neg_a = sum(1 for x in a if x in {strip_accents(n) for n in NEGATIONS})
    neg_b = sum(1 for x in b if x in {strip_accents(n) for n in NEGATIONS})
    res = {'expected_words': len(a), 'transcribed_words': len(b), 'similarity': round(sm.ratio(), 3),
           'missing_words': missing, 'unexpected_words': extra[:50], 'negations_expected': neg_a, 'negations_found': neg_b,
           'ok': not missing and neg_a == neg_b}
    write_json(Path(project) / f'verify_v{version}.json', res)
    return res


def write_report(project, info, plan, meta=None, ver=None, caps=None, version=None):
    L = ['# Claude AutoCut report', '', f"Source: `{read_json(Path(project) / 'source.json')['name']}` · "
         f"{fmt_time(plan['duration'])} → {fmt_time(plan['kept_duration'])} planned", '']
    counts = {}
    for d in plan['decisions']:
        counts[d['type']] = counts.get(d['type'], 0) + 1
    L += [f"- Plan status: **{plan['status']}** · removed spans: {counts or 'none'} (details in `decisions.md`)"]
    if plan['review']:
        L += [f'- For review: {r}' for r in plan['review']]
    if plan['pending']:
        L += [f'- Pending: {p}' for p in plan['pending']]
    if meta:
        L += [f"- Edit: `renders/cut_v{version}.mp4` ({meta['duration']:.2f} s, {len(meta['segments'])} segments)"]
    if ver:
        L += [f"- Verification: {'passed' if ver['ok'] else 'FAILED'} · similarity {ver['similarity']} · "
              f"missing words {len(ver['missing_words'])} · negations {ver['negations_found']}/{ver['negations_expected']}"]
        L += [f"  - missing: \"{m['word']}\" at {m['at_edit']:.2f} s" for m in ver['missing_words']]
    if caps:
        L += [f"- Captions: {caps['captions']} · every kept word once and in order: {caps['check']['same_sequence']} · "
              f"shorter than 0.5 s: {caps['under_0_5s']}" + (f" · `renders/final_v{version}.mp4`" if caps.get('video') else '')]
    L += ['', 'What this report does not prove: how the edit sounds and feels. Watch it with sound before publishing.']
    (Path(project) / 'REPORT.md').write_text('\n'.join(L) + '\n', encoding='utf-8')


def run_edit(video, project, model=DEFAULT_MODEL, language=None, transcript=None, captions=True, verify_cut=True,
             device='cpu', caption_size=None, caption_y=None, log=print) -> dict:
    project = Path(project).resolve()
    log('1/6 transcript')
    info, tr = prepare(video, project, model, language, transcript, device)
    log(f"    {len(tr['words'])} words, language {tr.get('language')}")
    log('2/6 analysis')
    an = A.analyze(tr, video, project)
    log(f"    {len(an['sentences'])} sentences, {len(an['pauses'])} pauses, {len(an['retakes'])} retakes, "
        f"{len(an['repetitions'])} repetitions, {len(an['hesitations'])} fillers, {len(an['negations'])} negations")
    log('3/6 plan')
    plan = P.build_plan(an, video, project, P.load_overrides(project))
    log(f"    {plan['duration']:.2f} s → {plan['kept_duration']:.2f} s, status {plan['status']}")
    if plan['status'] != 'ok':
        write_report(project, info, plan)
        for p in plan['pending']:
            log('    PENDING: ' + p)
        raise AutoCutError('stopped at the gate: high-impact cuts need an approval (see decisions.md)')
    renders = project / 'renders'
    v = next_version(renders, 'cut')
    log(f'4/6 render → renders/cut_v{v}.mp4')
    meta = R.render_cut(video, plan, renders / f'cut_v{v}.mp4')
    ver = None
    if verify_cut and tr.get('engine') == 'faster-whisper':
        log('5/6 verification (re-transcribing the edit)')
        ver = verify(renders / f'cut_v{v}.mp4', kept_words_out(an, meta['segments']), project, v,
                     tr.get('model', model), tr.get('language'), device)
        log(f"    {'passed' if ver['ok'] else 'FAILED'}: {len(ver['missing_words'])} missing word(s), negations "
            f"{ver['negations_found']}/{ver['negations_expected']}")
    else:
        log('5/6 verification skipped')
    caps = None
    if captions:
        log(f'6/6 captions → renders/final_v{v}.mp4')
        words = kept_words_out(an, meta['segments'])
        caps = CAP.make_captions(words, renders / f'cut_v{v}.mp4', project, True, caption_size, caption_y,
                                 name=f'renders/final_v{v}.mp4')
        (project / 'captions.srt').replace(project / f'captions_v{v}.srt')
        (project / 'captions.json').replace(project / f'captions_v{v}.json')
    else:
        log('6/6 captions skipped')
    write_report(project, info, plan, meta, ver, caps, v)
    return {'project': str(project), 'version': v, 'plan': plan['status'], 'cut': str(renders / f'cut_v{v}.mp4'),
            'final': caps.get('video') if caps else None, 'verify': ver, 'captions': caps}
