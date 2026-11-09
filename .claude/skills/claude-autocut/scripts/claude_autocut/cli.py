"""Command line of Claude AutoCut. Run `python scripts/autocut.py --help` from the skill folder."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from . import __version__
from .common import AutoCutError, read_json


def _span(s):
    if not s:
        return None
    a, b = (float(x) for x in s.split('-'))
    if b <= a:
        raise AutoCutError('--range must be START-END with END > START (seconds)')
    return a, b


def cmd_doctor(a):
    from .doctor import doctor
    d = doctor()
    for k, c in d['checks'].items():
        print(f"{'ok  ' if c['ok'] else 'MISS'} {k:15} {c['value'] or '-'}" + ('' if c['ok'] else f"   → {c['need']}"))
    print('\nmodes: ' + ', '.join(f"{k} {'ready' if v else 'NOT ready'}" for k, v in d['modes'].items()))
    for n in d['notes']:
        print('note: ' + n)
    return 0 if d['modes']['auto_edit'] else 1


def cmd_transcribe(a):
    from .transcribe import transcribe
    d = transcribe(a.video, a.out, model=a.model, language=a.language, device=a.device)
    print(f"{len(d['words'])} words ({d['language']}) → {a.out}")
    return 0


def cmd_edit(a):
    from .edit import run_edit
    r = run_edit(a.video, a.out, model=a.model, language=a.language, transcript=a.transcript, captions=not a.no_captions,
                 verify_cut=not a.no_verify, device=a.device, caption_size=a.caption_size, caption_y=a.caption_y)
    print(f"\nedit: {r['cut']}" + (f"\nwith captions: {r['final']}" if r['final'] else '') + f"\nreport: {Path(r['project']) / 'REPORT.md'}")
    return 0 if not r['verify'] or r['verify']['ok'] else 4


def cmd_plan(a):
    from . import analyze as A
    from . import plan as P
    proj = Path(a.project)
    src = read_json(proj / 'source.json')
    an = A.analyze(read_json(proj / 'transcript.json'), src['path'], proj)
    p = P.build_plan(an, src['path'], proj, P.load_overrides(proj))
    print(f"{p['duration']:.2f} s → {p['kept_duration']:.2f} s · status {p['status']} · see {proj / 'decisions.md'}")
    for x in p['pending']:
        print('PENDING: ' + x)
    return 0 if p['status'] == 'ok' else 3


def cmd_approve(a):
    from .plan import add_approval
    add_approval(a.project, a.start, a.end, a.by, a.reason)
    print(f'approval recorded in {Path(a.project) / "overrides.json"}; run `edit` again to render')
    return 0


def cmd_captions(a):
    from . import analyze as A
    from .captions import make_captions
    from .transcribe import transcribe
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    tr = read_json(a.transcript) if a.transcript else transcribe(a.video, out / 'transcript.json', model=a.model,
                                                                language=a.language, device=a.device)
    words = [{'w': w['w'], 's': w['s'], 'e': w['e']} for w in A.load_words(tr)]
    r = make_captions(words, a.video, out, burn_in=not a.no_burn, size=a.caption_size, y=a.caption_y)
    print(json.dumps({k: v for k, v in r.items()}, ensure_ascii=False, indent=1))
    return 0


def cmd_cartoon(a):
    from . import cartoon as C
    if a.action == 'init':
        p = C.init(a.target, a.out, model=a.model, language=a.language, transcript=a.transcript,
                   install_gsap=not a.no_npm, device=a.device)
        print(f'cartoon project: {p}\nnext: read speech.md, write storyboard.json, then `cartoon check` and `cartoon render`')
    elif a.action == 'check':
        r = C.check_storyboard(a.target)
        for e in r['errors']:
            print('ERROR: ' + e)
        for w in r['warnings']:
            print('warning: ' + w)
        print(f"{r['scenes']} scene(s): {'ok' if r['ok'] else 'fix the errors above'}")
        return 0 if r['ok'] else 3
    elif a.action == 'lint':
        r = C.lint(a.target)
        for k, v in r.items():
            print(f"{k}: exit {v['exit']}\n{v['stdout'][-1500:]}")
        return 0 if all(v['exit'] == 0 for v in r.values()) else 3
    elif a.action == 'snapshot':
        print(C.snapshot(a.target, a.at, a.name))
    elif a.action == 'render':
        r = C.render(a.target, _span(a.range), a.workers, a.quality)
        print(json.dumps(r, indent=1))
        return 0 if r['duration_ok'] and r.get('audio_identical_to_source', True) else 4
    return 0


def cmd_complete(a):
    from . import cartoon as C
    from .edit import run_edit
    out = Path(a.out)
    r = run_edit(a.video, out / 'edit', model=a.model, language=a.language, captions=True, verify_cut=not a.no_verify,
                 device=a.device)
    C.init(r['cut'], out / 'cartoon', model=a.model, language=a.language, install_gsap=not a.no_npm, device=a.device)
    print(f"\nedit: {r['cut']}\ncaptioned edit: {r['final']}\ncartoon project (on the edited timeline): {out / 'cartoon'}"
          f"\nnext: write {out / 'cartoon' / 'storyboard.json'}, then `cartoon check` and `cartoon render`")
    return 0


def parser():
    p = argparse.ArgumentParser(prog='autocut', description='Claude AutoCut: automatic editing, captions and cartoon videos.')
    p.add_argument('--version', action='version', version=__version__)
    sub = p.add_subparsers(dest='cmd', required=True)

    def media_opts(x):
        x.add_argument('--model', default='small', help='Whisper model: tiny, base, small (default), medium, large-v3')
        x.add_argument('--language', help='language code (e.g. en, pt, es); detected when omitted')
        x.add_argument('--device', default='cpu', help='cpu (default) or cuda')

    x = sub.add_parser('doctor', help='check dependencies and which modes are ready')
    x.set_defaults(f=cmd_doctor)
    x = sub.add_parser('transcribe', help='word-level transcript (JSON)')
    x.add_argument('video')
    x.add_argument('-o', '--out', required=True)
    media_opts(x)
    x.set_defaults(f=cmd_transcribe)
    x = sub.add_parser('edit', help='Auto Edit: cut pauses, fillers and redone takes, render, verify, caption')
    x.add_argument('video')
    x.add_argument('-o', '--out', required=True, help='project folder')
    x.add_argument('--transcript', help='use an existing transcript JSON instead of transcribing')
    x.add_argument('--no-captions', action='store_true')
    x.add_argument('--no-verify', action='store_true', help='skip re-transcribing the edit')
    x.add_argument('--caption-size', type=float)
    x.add_argument('--caption-y', type=float, help='caption center as a fraction of the height (0-1)')
    media_opts(x)
    x.set_defaults(f=cmd_edit)
    x = sub.add_parser('plan', help='re-run analysis and plan of a project (after editing overrides.json)')
    x.add_argument('project')
    x.set_defaults(f=cmd_plan)
    x = sub.add_parser('approve', help='record an approval for a high-impact cut (only with the user\'s explicit yes)')
    x.add_argument('project')
    x.add_argument('--start', type=float, required=True)
    x.add_argument('--end', type=float, required=True)
    x.add_argument('--by', required=True, help='who approved (e.g. "user")')
    x.add_argument('--reason', required=True)
    x.set_defaults(f=cmd_approve)
    x = sub.add_parser('captions', help='captions for a video without cutting it (SRT and burned-in)')
    x.add_argument('video')
    x.add_argument('-o', '--out', required=True)
    x.add_argument('--transcript')
    x.add_argument('--no-burn', action='store_true')
    x.add_argument('--caption-size', type=float)
    x.add_argument('--caption-y', type=float)
    media_opts(x)
    x.set_defaults(f=cmd_captions)
    x = sub.add_parser('cartoon', help='cartoon mode: init, check, lint, snapshot, render')
    x.add_argument('action', choices=['init', 'check', 'lint', 'snapshot', 'render'])
    x.add_argument('target', help='video (init) or cartoon project folder')
    x.add_argument('-o', '--out', help='project folder (init)')
    x.add_argument('--transcript')
    x.add_argument('--no-npm', action='store_true', help='do not run npm install (init)')
    x.add_argument('--at', help='snapshot times, e.g. 1.5,4,9')
    x.add_argument('--name')
    x.add_argument('--range', help='render only START-END seconds')
    x.add_argument('--workers', type=int, default=2)
    x.add_argument('--quality', default='standard', help='HyperFrames quality: draft, standard, looks, delivery (default standard)')
    media_opts(x)
    x.set_defaults(f=cmd_cartoon)
    x = sub.add_parser('complete', help='Auto Edit, then a cartoon project on the edited timeline')
    x.add_argument('video')
    x.add_argument('-o', '--out', required=True)
    x.add_argument('--no-verify', action='store_true')
    x.add_argument('--no-npm', action='store_true')
    media_opts(x)
    x.set_defaults(f=cmd_complete)
    return p


def main(argv=None):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass
    a = parser().parse_args(argv)
    if a.cmd == 'cartoon' and a.action == 'init' and not a.out:
        print('ERROR: cartoon init needs -o/--out', file=sys.stderr)
        return 2
    try:
        return a.f(a) or 0
    except AutoCutError as e:
        print(f'ERROR: {e}', file=sys.stderr)
        return 2
    except KeyboardInterrupt:
        return 130
