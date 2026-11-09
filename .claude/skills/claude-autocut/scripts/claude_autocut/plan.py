"""Editorial plan: which parts of the recording stay (the EDL) and why, with a gate for risky cuts.

Automatic decisions are conservative:
- silence before the first and after the last word is trimmed;
- long pauses are shortened, never removed: a natural breath stays at every join, and a pause after the end of
  a sentence (a possible pause for emphasis) keeps more;
- filler sounds ("um", "uh", "hmm", "ééé"...) are removed;
- an incomplete take that is immediately redone in full is removed (the complete take stays);
- of two complete takes of the same sentence, the cleaner one stays by evidence (complete sentence, fewer
  fillers, higher word confidence). If the evidence does not separate them, both stay and the case is listed
  for review. The plan never picks "the last one" or "the shortest one" by default.

Every removed span is classified:
- technical: silence, shortened pause, filler, incomplete take that was redone;
- editorial: words that leave because the same words stay in a nearby take;
- high_impact: words that leave and are not said anywhere else (negations included). These only come from
  manual cuts (overrides.json) and block the render until an approval covering them is recorded.

overrides.json (optional, written by the user or by Claude after asking the user):
  {"cuts":      [{"start": 12.0, "end": 18.5, "reason": "off-topic tangent"}],
   "keep":      [{"start": 3.0, "end": 4.2, "reason": "the filler is part of the joke"}],
   "pauses":    {"p04": {"action": "keep"}},
   "approvals": [{"start": 12.0, "end": 18.5, "approved_by": "user", "reason": "asked to drop the tangent"}]}
"""
from __future__ import annotations

from pathlib import Path

from .analyze import envelope_db
from .common import END_PUNCT, AutoCutError, read_json, write_json

PAUSE_KEEP_MAX = 0.7      # pauses up to this length are left untouched
PAUSE_TARGET = 0.30       # silence kept at a shortened pause
EMPHASIS_TARGET = 0.45    # silence kept at a shortened pause after the end of a sentence
JOIN_TARGET = 0.15        # silence kept where removed words were
LEAD_IN, TAIL = 0.15, 0.35
EDGE_MAX = 0.30           # how far a word edge may be extended into audible sound (Whisper edges drift)


def _within(t, spans):
    return any(s['start'] - 0.02 <= t <= s['end'] + 0.02 for s in spans)


def _seq_in(target, seq):
    n = len(seq)
    return bool(n) and any(target[k:k + n] == seq for k in range(len(target) - n + 1))


class Edges:
    """Find where speech really starts/ends around Whisper word edges, using the loudness envelope."""

    def __init__(self, env, floor, voice):
        self.env = env
        if env is None:
            self.thr = None
        else:
            f = floor if floor is not None else -60.0
            v = voice if voice is not None else f + 30
            self.thr = max(f + 6.0, v - 28.0)

    def _db(self, t):
        i = int(t / 0.01)
        return float(self.env[min(max(i, 0), len(self.env) - 1)])

    def forward(self, t, limit):
        if self.env is None:
            return t
        stop = min(limit, t + EDGE_MAX)
        x = t
        while x < stop and self._db(x) > self.thr:
            x += 0.01
        return min(x, stop)

    def backward(self, t, limit):
        if self.env is None:
            return t
        stop = max(limit, t - EDGE_MAX)
        x = t
        while x > stop and self._db(x - 0.01) > self.thr:
            x -= 0.01
        return max(x, stop)


def _evidence(ws, s):
    sw = ws[s['first']:s['last'] + 1]
    complete = 1.0 if sw[-1]['w'][-1] in END_PUNCT else 0.0
    fillers = sum(w['hes'] for w in sw)
    conf = sum(w['p'] for w in sw) / len(sw)
    return complete * 1.0 - 0.3 * fillers + conf


def build_plan(analysis: dict, media, out_dir, overrides: dict | None = None) -> dict:
    out_dir = Path(out_dir)
    ov = overrides or {}
    ws = analysis['words']
    if not ws:
        raise AutoCutError('the transcript has no words: nothing to edit (is there speech in the video?)')
    ss = {s['id']: s for s in analysis['sentences']}
    duration = float(analysis['source'].get('duration') or ws[-1]['e'])
    mid = lambda w: (w['s'] + w['e']) / 2  # noqa: E731
    keep_spans = ov.get('keep', [])
    cut_spans = ov.get('cuts', [])
    protected = {w['i'] for w in ws if _within(mid(w), keep_spans)}
    removed: dict[int, tuple[str, str]] = {}
    review = []

    for w in ws:
        if w.get('silent') and w['i'] not in protected:
            removed[w['i']] = ('technical', 'text over silence (transcription artifact)')
        elif w['hes'] and w['i'] not in protected:
            removed[w['i']] = ('technical', 'filler sound')
    incomplete_ids = set()
    for r in analysis['retakes']:
        a, b = ss[r['incomplete']], ss[r['redone']]
        if r['confidence'] != 'high':
            review.append(f"possible retake {r['incomplete']} → {r['redone']} ({r['evidence']}): nothing was cut")
            continue
        idx = [i for i in range(a['first'], a['last'] + 1) if i not in protected]
        if len(idx) == a['last'] - a['first'] + 1:
            incomplete_ids.add(a['id'])
            for i in idx:
                removed[i] = ('technical', f"incomplete take {a['id']}, redone in full in {b['id']}")
    for r in analysis['repetitions']:
        a, b = ss[r['first']], ss[r['second']]
        if a['id'] in incomplete_ids or b['id'] in incomplete_ids:
            continue
        ea, eb = _evidence(ws, a), _evidence(ws, b)
        if abs(ea - eb) < 0.05:
            review.append(f"{a['id']} and {b['id']} are two complete takes of the same sentence and the evidence does "
                          f"not separate them: both kept, choose one")
            continue
        loser, keeper = (a, b) if ea < eb else (b, a)
        idx = [i for i in range(loser['first'], loser['last'] + 1) if i not in protected]
        if len(idx) == loser['last'] - loser['first'] + 1:
            for i in idx:
                removed[i] = ('editorial', f"repeated take {loser['id']}; the cleaner take {keeper['id']} stays")
    for c in cut_spans:
        for w in ws:
            if c['start'] - 0.02 <= mid(w) <= c['end'] + 0.02:
                removed[w['i']] = ('manual', c.get('reason', 'manual cut'))

    # audible sound the transcript missed is kept as if it were words: the plan never cuts it on its own
    sound = [{'i': None, 'w': '[sound]', 's': u['start'], 'e': u['end'], 'p': 1.0, 'hes': False, 'neg': False}
             for u in analysis.get('unworded_sound', [])]
    for u in sound:
        review.append(f"audible sound without transcript at {u['s']:.2f}-{u['e']:.2f} s was kept: listen to it")
    seq = sorted(ws + sound, key=lambda x: x['s'])
    gone = lambda x: x['i'] is not None and x['i'] in removed  # noqa: E731
    kept = [k for k, x in enumerate(seq) if not gone(x)]
    if not any(seq[k]['i'] is not None for k in kept):
        raise AutoCutError('every word would be removed; check overrides.json')
    env = envelope_db(media)
    edges = Edges(env, analysis['source'].get('noise_floor_db'), analysis['source'].get('voice_db'))
    pauses_by_word = {p['after_index']: p for p in analysis['pauses']}
    pause_ov = ov.get('pauses', {})

    first = seq[kept[0]]
    segs, start = [], max(0.0, edges.backward(first['s'], 0.0) - LEAD_IN)
    for ka, kb in zip(kept, kept[1:]):
        a, b = seq[ka], seq[kb]
        gap = b['s'] - a['e']
        between = kb - ka > 1
        p = pauses_by_word.get(a['i']) if (not between and a['i'] is not None and b['i'] == a['i'] + 1) else None
        if p and pause_ov.get(p['id'], {}).get('action') == 'keep':
            continue
        if not between and gap <= PAUSE_KEEP_MAX:
            continue
        if between:
            target = EMPHASIS_TARGET if a['w'][-1] in END_PUNCT else JOIN_TARGET   # a sentence ended: keep its breath
        elif p:
            target = float(pause_ov.get(p['id'], {}).get('keep_s', EMPHASIS_TARGET if p['emphasis_candidate'] else PAUSE_TARGET))
        else:
            target = PAUSE_TARGET
        nxt_any = seq[ka + 1]['s']
        prv_any = seq[kb - 1]['e']
        tail_end = edges.forward(a['e'], nxt_any)
        head = edges.backward(b['s'], prv_any)
        if head <= tail_end:
            if not between:
                continue
            head = tail_end
        middle = (tail_end + head) / 2
        end = min(tail_end + target / 2, middle)
        nstart = max(head - target / 2, middle)
        if nstart - end < 0.06 and not between:
            continue
        segs.append([start, end])
        start = nstart
    last = seq[kept[-1]]
    segs.append([start, min(duration, edges.forward(last['e'], duration) + TAIL)])
    segs = [[round(a, 3), round(b, 3)] for a, b in segs if b - a > 0.04]

    # --- gate: classify every removed span -------------------------------------------------------
    holes, t = [], 0.0
    for a, b in segs:
        if a - t > 0.02:
            holes.append((t, a))
        t = max(t, b)
    if duration - t > 0.02:
        holes.append((t, duration))
    approvals = ov.get('approvals', [])
    stays = lambda w: _within(mid(w), [{'start': a, 'end': b} for a, b in segs])  # noqa: E731
    kept_norm = [(w['n'], mid(w)) for w in ws if stays(w)]
    decisions, pending = [], []
    for a, b in holes:
        gone = [w for w in ws if a <= mid(w) <= b and not stays(w)]
        d = {'start': round(a, 3), 'end': round(b, 3), 'words': ' '.join(w['w'] for w in gone)}
        reasons = {removed.get(w['i'], ('?', '?')) for w in gone}
        if not gone:
            what = 'silence before the first word' if a < 0.05 else 'silence after the last word' if b >= duration - 0.05 else 'pause shortened'
            d.update(type='technical', reason=what, impact='none')
        elif all(r[0] == 'technical' for r in reasons):
            d.update(type='technical', reason='; '.join(sorted(r[1] for r in reasons)), impact='low')
        else:
            seq = [w['n'] for w in gone if not w['hes']]
            near = [n for n, m in kept_norm if abs(m - a) < 20]
            negs = [w['w'] for w in gone if w['neg']]
            manual = [r[1] for r in reasons if r[0] == 'manual']
            if all(r[0] in ('technical', 'editorial') for r in reasons) or (_seq_in(near, seq) and not manual):
                d.update(type='editorial', reason='; '.join(sorted(r[1] for r in reasons if r[0] != '?')) or
                         'the same words stay in a nearby take', impact='medium')
            elif _seq_in(near, seq) and not negs:
                d.update(type='editorial', reason=f"{'; '.join(manual)} (the same words stay nearby)", impact='medium')
            else:
                d.update(type='high_impact', impact='high',
                         reason=('; '.join(manual) or 'speech that is not repeated anywhere') +
                         (f" (negation removed: {', '.join(negs)})" if negs else ''))
        if d['type'] == 'high_impact':
            # the approval has to cover the risky words (not fillers or silence around them)
            risky = [w for w in gone if removed.get(w['i'], ('?',))[0] != 'technical'] or gone
            r0, r1 = min(w['s'] for w in risky), max(w['e'] for w in risky)
            d['risky_span'] = [round(r0, 2), round(r1, 2)]
            ok = [x for x in approvals if x.get('approved_by') and all(x['start'] - 0.05 <= mid(w) <= x['end'] + 0.05 for w in risky)]
            if ok:
                d['approved'] = f"{ok[0]['approved_by']}: {ok[0].get('reason', '')}"
            else:
                pending.append(f"high-impact cut without approval: {r0:.2f}-{r1:.2f} \"{' '.join(w['w'] for w in risky)}\"")
        decisions.append(d)

    kept_dur = sum(b - a for a, b in segs)
    plan = {
        'source': analysis['source'], 'duration': duration, 'kept_duration': round(kept_dur, 3),
        'ranges': [{'start': a, 'end': b} for a, b in segs],
        'decisions': decisions, 'review': review, 'pending': pending, 'status': 'blocked' if pending else 'ok',
        'settings': {'pause_keep_max': PAUSE_KEEP_MAX, 'pause_target': PAUSE_TARGET, 'emphasis_target': EMPHASIS_TARGET},
    }
    write_json(out_dir / 'edl.json', plan)
    counts = {}
    for d in decisions:
        counts[d['type']] = counts.get(d['type'], 0) + 1
    L = ['# Editorial plan', '', f"{duration:.2f} s → {kept_dur:.2f} s · {len(segs)} kept ranges · "
         f"removed spans: {counts or 'none'} · status: **{plan['status']}**", '',
         '| Removed span | Type | Reason | Words removed |', '|---|---|---|---|']
    L += [f"| {d['start']:.2f}-{d['end']:.2f} | {d['type']} | {d['reason']}{' · approved by ' + d['approved'] if d.get('approved') else ''} "
          f"| {d['words'] or '-'} |" for d in decisions]
    L += ['', '## For review', ''] + ([f'- {r}' for r in review] or ['- nothing'])
    L += ['', '## Pending (blocks the render)', ''] + ([f'- {p}' for p in pending] or ['- nothing'])
    (out_dir / 'decisions.md').write_text('\n'.join(L) + '\n', encoding='utf-8')
    return plan


def load_overrides(project) -> dict:
    p = Path(project) / 'overrides.json'
    return read_json(p) if p.exists() else {}


def add_approval(project, start: float, end: float, approved_by: str, reason: str) -> dict:
    if not approved_by.strip() or not reason.strip():
        raise AutoCutError('an approval needs who approved it (--by) and why (--reason)')
    ov = load_overrides(project)
    ov.setdefault('approvals', []).append({'start': float(start), 'end': float(end), 'approved_by': approved_by.strip(),
                                           'reason': reason.strip()})
    write_json(Path(project) / 'overrides.json', ov)
    return ov
