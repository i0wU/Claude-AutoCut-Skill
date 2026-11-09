# Auto Edit: how decisions are made

## Pipeline

1. **Transcript** (`transcript.json`): faster-whisper with word timestamps. Reused when the same file (SHA-256)
   was already transcribed with the same model.
2. **Analysis** (`analysis.json`, `analysis.md`):
   - sentences (end punctuation, or a pause of 0.30 s, or a comma followed by 0.2 s);
   - pauses of 0.25 s or more, classed `incidental` (up to 0.7 s), `long` (up to 1.5 s) or `excessive`;
     a pause after the end of a sentence is an *emphasis candidate*;
   - retakes: a sentence that starts with the same two or more words as the next one and is not longer
     (`high` confidence when it is a full prefix of the next one);
   - repetitions: the same sentence (80% of the words) said twice within 20 s;
   - fillers (language aware: "um" is a filler in English, the word "one/a" in Portuguese), negations,
     words with probability below 0.6;
   - text over silence: a word whose loudest 10 ms is less than 10 dB above the noise floor (a Whisper
     artifact, often subtitles credits invented over silence);
   - audible sound without words: 0.3 s or more clearly above the floor with no word on it.
3. **Plan** (`edl.json`, `decisions.md`): kept ranges and the classification of every removed span.
4. **Render** (`renders/cut_vN.mp4`): FFmpeg trims each kept range, snapped to whole video frames (audio and
   video stay the same length on every segment, so there is no drift), and joins them with 8 ms audio fades.
5. **Verification** (`verify_vN.json`): the edit is transcribed again and compared word by word with the
   words that should have stayed. Fillers and uncertain words are not counted as losses. Negations are
   counted on both sides.
6. **Captions** (`captions_vN.srt`, `renders/final_vN.mp4`).

## What the plan cuts automatically

| Situation | Decision | Type |
|---|---|---|
| silence before the first / after the last word | trimmed to 0.15 s / 0.35 s | technical |
| pause up to 0.7 s | untouched | - |
| longer pause | shortened to 0.30 s; 0.45 s after the end of a sentence | technical |
| filler sound | removed | technical |
| text over silence | removed | technical |
| incomplete take followed by the full take (high confidence) | the incomplete one removed | technical |
| possible retake (medium confidence) | nothing cut, listed for review | - |
| two complete takes of the same sentence | the one with better evidence stays (complete sentence, fewer fillers, higher confidence); tie: both stay, listed for review | editorial |
| audible sound without words | always kept, listed for review | - |

Word edges from Whisper drift by up to a few hundred milliseconds. Before cutting inside a pause, the
plan follows the loudness envelope from each word edge until the sound really stops (up to 0.3 s), and the
kept breath is split around the join.

## The gate

Every removed span is classified:
- **technical**: silence, shortened pause, filler, text over silence, incomplete take that was redone;
- **editorial**: the same words stay in a nearby take;
- **high_impact**: words leave that are not said anywhere else, including any negation. Only manual cuts
  (`overrides.json` → `cuts`) can produce this. The render refuses to run until an approval covering the
  span is recorded with `approve` (who approved and why). Ask the user first; never approve on their behalf.

## Tuning

- `overrides.json` → `keep`: protect a span (a filler that is part of a joke, a pause that is a punchline).
- `overrides.json` → `pauses`: `{"p04": {"action": "keep"}}` keeps a pause whole;
  `{"p07": {"keep_s": 0.8}}` keeps 0.8 s of it.
- `--caption-size` (pixels) and `--caption-y` (0-1) change the captions.
- Thresholds are constants at the top of `scripts/claude_autocut/plan.py` and `analyze.py`.

## Limits

- The quality of every decision depends on the transcript. Whisper may skip fillers, merge a retake into one
  sentence, or mishear words (verification and "For review" catch part of this, not all).
- The editor does not judge content: it does not remove off-topic parts on its own, and it does not pick a
  take by delivery or tone, only by measurable evidence.
- No reframing, zooms or b-roll in this version.
