---
name: claude-autocut
description: AI video editing for talking-head recordings, run locally. Automatic smart cuts that remove long pauses, filler words and redone takes, interview and podcast editing, vertical videos for Reels, TikTok and Shorts, automatic captions/subtitles (SRT and burned-in), and an animated podcast / cartoon mode where a paper-cutout scene follows the narration above the speaker. Use when the user asks to edit a video automatically, cut pauses or silences, remove "um"/"uh", clean up retakes, edit an interview, add captions or subtitles, make a vertical video, or turn a recording into a cartoon or animated podcast.
---

# Claude AutoCut

Local video editing driven by a word-level transcript. Everything runs on the user's machine: Whisper
(faster-whisper) for speech, FFmpeg for media, Pillow for captions and, in the cartoon mode only, HyperFrames
(Node.js) to render the animation. No API key, no paid service, nothing is uploaded.

The command line is `scripts/autocut.py` inside this skill folder. Run it with the Python that has the
requirements installed (see "Setup"):

```bash
python "<skill-dir>/scripts/autocut.py" <command> ...
```

`<skill-dir>` is the base directory of this skill (shown when the skill loads).

## Pick the mode

| The user wants | Mode | Command |
|---|---|---|
| "edit this video", "cut the pauses", "remove the ums", "clean up my retakes" | Auto Edit | `edit VIDEO -o PROJECT` |
| captions/subtitles on a video without cutting it | Captions | `captions VIDEO -o FOLDER` |
| an animated scene above the speaker, whole recording kept | Full Animated | `cartoon init VIDEO -o PROJECT`, storyboard, `cartoon render` |
| edit first, then animate the edited video | Complete | `complete VIDEO -o FOLDER`, storyboard, `cartoon render` |
| "cartoon", "animated podcast" without saying whether to cut | ask once: keep everything (Full Animated) or cut first (Complete)? |

If the request is ambiguous, ask which mode in one short question and recommend one. Before anything else,
run `doctor` once in the session: it says which modes are ready on this machine.

## Setup (once per machine)

1. `python -m venv .venv` and activate it, then `pip install -r "<skill-dir>/requirements.txt"`.
2. FFmpeg (`ffmpeg` and `ffprobe`) on PATH.
3. Cartoon modes only: Node.js 18+ (npx and npm). HyperFrames 0.8.79 is fetched by npx on first use and is
   never updated automatically; each cartoon project installs GSAP with npm.
4. `python "<skill-dir>/scripts/autocut.py" doctor`

The first transcription downloads the Whisper model (`--model tiny` ~75 MB, `small` ~480 MB, the default).
Use `--language` when the language is known; `--model medium` or `large-v3` for hard audio.

## Auto Edit

```bash
python "<skill-dir>/scripts/autocut.py" edit input.mp4 -o edits/my-video [--language en] [--model small]
```

Steps: transcript → analysis → plan → render → verification (the edit is transcribed again and compared) →
captions → `REPORT.md`. Outputs in the project folder: `renders/cut_vN.mp4` (clean edit),
`renders/final_vN.mp4` (with burned captions), `captions_vN.srt`, `decisions.md` (every removed span with
its type and reason), `analysis.md`, `verify_vN.json`. Nothing is ever overwritten: every render is a new version.
The source video is only read.

What the plan does on its own (conservative on purpose):
- trims silence before the first and after the last word;
- shortens pauses longer than 0.7 s but never removes them; a pause after the end of a sentence keeps more
  (a possible pause for emphasis);
- removes filler sounds and an incomplete take that is redone right after;
- of two complete takes of the same sentence, keeps the cleaner one by evidence, never "the last" or "the
  shortest"; if the evidence is even, both stay and the case is listed under "For review";
- keeps audible sound that the transcript missed and drops text Whisper invented over silence.

### The gate (high-impact cuts)

A cut that removes words not said anywhere else (negations included) is **high impact**. The automatic plan
never makes one; they come only from `overrides.json` (cuts you add on the user's request). The render stops
until each high-impact cut has an approval. To approve, show the user the exact span and words from
`decisions.md`, get an explicit yes, then:

```bash
python "<skill-dir>/scripts/autocut.py" approve PROJECT --start 12.0 --end 18.5 --by "user" --reason "asked to drop the tangent"
python "<skill-dir>/scripts/autocut.py" edit input.mp4 -o PROJECT     # transcript is reused, new version rendered
```

Never record an approval the user did not give. `plan PROJECT` re-runs analysis and plan without rendering.

### overrides.json (in the project folder)

```json
{"cuts":  [{"start": 12.0, "end": 18.5, "reason": "off-topic tangent"}],
 "keep":  [{"start": 3.0, "end": 4.2, "reason": "the filler is part of the joke"}],
 "pauses": {"p04": {"action": "keep"}, "p07": {"keep_s": 0.8}}}
```

Pause ids (`p04`) come from `analysis.md`. Read `references/editing.md` for how decisions are classified.

### Reporting back to the user

Read `REPORT.md` and `decisions.md` and tell the user, briefly: duration before and after, what was removed
and why, anything under "For review", whether verification passed (missing words, negations kept). Say that
you cannot hear or watch the video: rhythm and taste are for the user to judge with sound.

## Captions only

```bash
python "<skill-dir>/scripts/autocut.py" captions input.mp4 -o captions/my-video [--no-burn] [--caption-y 0.75]
```

Writes `captions.srt`, `captions.json` and `captioned.mp4`. Vertical videos get large uppercase captions at
70% of the height; horizontal ones sit near the bottom. Every spoken word appears once, in order.

## Cartoon (Full Animated and Complete)

1. `cartoon init VIDEO -o PROJECT` (Complete does `edit` first and creates the cartoon project on the edit).
2. Read `PROJECT/speech.md` (speech blocks with times) and write `PROJECT/storyboard.json`: scenes that cover
   the whole video without gaps, each with a scenario, the host's poses and faces, objects and on-screen
   words. The schema, the catalog (scenarios, poses, faces, objects, transitions) and layout rules are in
   `references/cartoon.md`. Read it before writing the first storyboard.
3. `cartoon check PROJECT` until it reports no errors. On-screen text may only use words that are spoken.
4. `cartoon snapshot PROJECT --at 1.5,8,20` and look at the frames in `reviews/`.
5. `cartoon render PROJECT` (or `--range 0-6` for a quick test). Output: `renders/cartoon_vN.mp4` with the
   source audio copied unchanged; `renders/cartoon_vN.qc.json` checks duration and audio.

The animation reads the meaning of the speech only through the storyboard you write: the code does not
understand the speech by itself.

## Rules

- Never modify or delete the source video or earlier renders.
- Never add a cut that changes the meaning of the speech; never approve a high-impact cut for the user.
- On-screen text and captions use only words that are spoken.
- Run renders one at a time; cartoon rendering is heavy (see `references/troubleshooting.md`).
- Do not claim the result "sounds good": you cannot hear it. Report what was measured.

## When something fails

See `references/troubleshooting.md` (missing FFmpeg, model download, Node/npx, HyperFrames, memory, wrong
language, bad transcription).
