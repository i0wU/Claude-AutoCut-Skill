# Claude AutoCut Skill

**AI-Powered Video Editing & Cartoon Animation for Claude Code**

Claude AutoCut is a [Claude Code](https://docs.claude.com/en/docs/claude-code/overview) skill that edits
talking-head recordings on your own computer. Tell Claude "edit this video", "add captions" or "turn this
into an animated podcast" and it runs real tools: a local Whisper transcription, an editorial plan you can
read, FFmpeg for the cut, captions drawn with Pillow and, for the cartoon mode, HyperFrames to render a
paper-cutout animation that follows the speech.

No API key, no paid service, no upload. Every decision is written down with its reason, and cuts that could
change the meaning of what you said are blocked until you approve them.

## Contents

- [What it does](#what-it-does)
- [Modes](#modes)
- [Video Example](#video-example)
- [Installation](#installation)
- [Requirements](#requirements)
- [Your first edit](#your-first-edit)
- [Making a cartoon video](#making-a-cartoon-video)
- [Captions](#captions)
- [Where the files go](#where-the-files-go)
- [Editorial review](#editorial-review)
- [Known limitations](#known-limitations)
- [Hardware and speed](#hardware-and-speed)
- [Privacy](#privacy)
- [License](#license)
- [Contributing](#contributing)

## What it does

From a word-level transcript of your recording, automatically:

- trims the silence before the first and after the last word;
- shortens long pauses while keeping a natural breath, and keeps more after the end of a sentence (a
  possible pause for emphasis); pauses up to 0.7 s are left alone;
- removes filler sounds ("um", "uh", "hmm"; language aware);
- removes an incomplete take that you redo right after, keeping the complete one;
- when you say the same sentence twice, keeps the cleaner take by evidence (complete sentence, fewer
  fillers, higher transcription confidence) and lists ties for you to choose;
- keeps any audible sound the transcript missed, and drops text Whisper invents over silence;
- protects negations: a cut that removes "not", "never", "no"... without the same word surviving nearby is
  never automatic;
- renders the edit frame-accurately (audio and video stay in sync on every segment);
- transcribes the edit again and checks that no expected word disappeared;
- writes captions (SRT and burned-in) where every kept word appears once, in order;
- produces a report and a table of every removed span with its type and reason.

## Modes

| Mode | What you get | Command |
|---|---|---|
| **Auto Edit** | the cut video, a captioned version, SRT, report | `edit VIDEO -o PROJECT` |
| **Captions** | captions for a video you do not want to cut | `captions VIDEO -o FOLDER` |
| **Full Animated** | the whole recording, untouched, with an animated paper-cutout scene above it (1080x1920) | `cartoon init VIDEO -o PROJECT`, storyboard, `cartoon render PROJECT` |
| **Complete** | Auto Edit, then the cartoon on the edited timeline | `complete VIDEO -o FOLDER`, storyboard, `cartoon render` |

In Claude Code you do not need to remember the commands: ask in plain words and the skill picks the mode,
or asks you which one when it is not clear. In the cartoon modes Claude writes the storyboard (which scene,
pose, object and on-screen word goes where) by reading the transcript; the code then checks and renders it.

## Video Example

[**Watch the video example on Instagram**](https://www.instagram.com/reel/DffxhJllcuX/)

An external reference that shows the editing style this project aims at: a short vertical video with tight
cuts and captions. It is linked here for illustration only. It is not an automated test of this repository,
and it was not produced by this public version of the skill.

## Installation

The skill is a folder that Claude Code discovers in `.claude/skills/`. Two ways to use it:

**In this repository** (the skill is already in `.claude/skills/claude-autocut`):

```bash
git clone https://github.com/i0wU/Claude-AutoCut-Skill.git
cd Claude-AutoCut-Skill
python -m venv .venv
# Windows: .venv\Scripts\activate    macOS/Linux: source .venv/bin/activate
pip install -r .claude/skills/claude-autocut/requirements.txt
python .claude/skills/claude-autocut/scripts/autocut.py doctor
```

Then open Claude Code in this folder and ask it to edit a video.

**For every project on your machine**: copy (or link) the folder `.claude/skills/claude-autocut` to
`~/.claude/skills/claude-autocut` (user skills), install the requirements in a Python environment of your
choice, and tell Claude which Python to use the first time.

Optionally, `pip install .` from the repository root also installs an `autocut` command.

More details per operating system: [docs/installation.md](docs/installation.md).

## Requirements

| Needed for | Requirement |
|---|---|
| everything | Python 3.10+ with `faster-whisper`, `numpy`, `Pillow` (`requirements.txt`) |
| everything | [FFmpeg](https://ffmpeg.org/download.html) (`ffmpeg` and `ffprobe` on PATH) |
| first transcription | internet once, to download a Whisper model from Hugging Face (`tiny` ~75 MB, `small` ~480 MB default, `medium` ~1.5 GB) |
| cartoon modes | [Node.js](https://nodejs.org) 18+ (npx, npm); internet once for `hyperframes@0.8.79` (fetched by npx, with a headless browser) and `gsap` (installed by npm in each cartoon project) |

`python .claude/skills/claude-autocut/scripts/autocut.py doctor` tells you what is missing and which modes
are ready. Nothing is installed globally by the skill, and HyperFrames is pinned to 0.8.79 (never updated
automatically).

## Your first edit

Try it on a synthetic video first (made by your system's text-to-speech, with a redone take, long pauses, a
filler and a negation):

```bash
python examples/make_demo_video.py demo.mp4
python .claude/skills/claude-autocut/scripts/autocut.py edit demo.mp4 -o edits/demo --model tiny
```

Then on your own recording:

```bash
python .claude/skills/claude-autocut/scripts/autocut.py edit my-video.mp4 -o edits/my-video --language en
```

Use `--model medium` for difficult audio, `--device cuda` with an NVIDIA GPU, `--no-captions` or
`--no-verify` to skip steps. Running `edit` again on the same project reuses the transcript and renders a new
version (nothing is overwritten).

## Making a cartoon video

```bash
python .claude/skills/claude-autocut/scripts/autocut.py cartoon init my-video.mp4 -o cartoons/my-video
# write cartoons/my-video/storyboard.json (Claude does this by reading speech.md)
python .claude/skills/claude-autocut/scripts/autocut.py cartoon check cartoons/my-video
python .claude/skills/claude-autocut/scripts/autocut.py cartoon snapshot cartoons/my-video --at 1.5,8,20
python .claude/skills/claude-autocut/scripts/autocut.py cartoon render cartoons/my-video
```

The layout is a scene on top, a torn-paper divider and your video below. The library has three scenarios
(studio bedroom, living room, craft bench), a host with 11 poses and 6 expressions whose mouth follows your
real voice, a laptop character, a hand with a phone, 14 objects and a torn-page transition. The storyboard
format and the full catalog are in
[`.claude/skills/claude-autocut/references/cartoon.md`](.claude/skills/claude-autocut/references/cartoon.md).
`cartoon render --range 0-6` renders a short test first. The final file keeps the original audio, copied
byte for byte.

For **Complete** (edit, then animate the edit): `complete my-video.mp4 -o work/my-video`.

## Captions

Auto Edit captions the edit by default. For any video without cutting it:

```bash
python .claude/skills/claude-autocut/scripts/autocut.py captions my-video.mp4 -o captions/my-video
```

Vertical videos get large uppercase captions at 70% of the height (clear of the Reels/TikTok interface);
horizontal videos get them near the bottom. Change with `--caption-size PIXELS` and `--caption-y 0.8`.
Use `--no-burn` for the SRT only. Captions are drawn with Pillow from a bundled open font (Anton, OFL), so
they do not depend on fontconfig or libass.

## Where the files go

Everything is written inside the project folder you pass with `-o`; the source video is only read.

| File | Content |
|---|---|
| `renders/cut_vN.mp4`, `renders/final_vN.mp4` | the edit, and the edit with captions (new version on every run) |
| `captions_vN.srt`, `captions_vN.json` | captions on the edited timeline |
| `decisions.md`, `edl.json` | every removed span, its type and reason; the kept ranges |
| `analysis.md` | sentences, pauses, retakes, repetitions, fillers, negations, uncertain words |
| `verify_vN.json` | the edit transcribed again and compared with the expected words |
| `REPORT.md` | summary of the last run |
| `overrides.json` | your manual decisions (optional) |
| cartoon: `renders/cartoon_vN.mp4`, `reviews/` | renders with a QC file; review frames |

## Editorial review

Every removed span is classified:

- **technical**: silence, shortened pause, filler, text over silence, incomplete take that was redone;
- **editorial**: words that leave because the same words stay in a nearby take;
- **high impact**: words that leave and are not said anywhere else, including negations.

The automatic plan never makes high-impact cuts. They only appear when you ask for a manual cut (for
example "drop the part where I talk about X"), written to `overrides.json`. The render then stops until an
approval covering those words is recorded:

```bash
python .claude/skills/claude-autocut/scripts/autocut.py approve edits/my-video --start 12.0 --end 18.5 --by "me" --reason "off-topic"
```

The skill instructs Claude to show you the exact words and to record an approval only after your explicit
yes. See [`references/editing.md`](.claude/skills/claude-autocut/references/editing.md).

## Known limitations

- Decisions are only as good as the transcript. Whisper may skip fillers, merge a retake into one sentence
  or mishear words; verification and the "For review" list catch part of this, not all of it.
- The editor removes errors, not content: it does not judge what is interesting, choose a take by tone, or
  remove off-topic parts on its own.
- No automatic reframing, zoom, b-roll or music in this version.
- The cartoon library is fixed (three scenarios, one host, a laptop, a phone hand, 14 objects). New subjects
  may need new drawings in `scenes/*.js`. The storyboard schema uses Portuguese key names (the engine's
  original language), documented in English.
- Rendering the cartoon is heavy: it runs a headless browser per worker.
- Tested on Windows 11 (all modes, end to end, with speech from a text-to-speech voice) and on Ubuntu
  through GitHub Actions (unit and synthetic end-to-end tests without a speech model and without the cartoon
  render). macOS has not been tested.
- AI cannot listen to or watch the result. The reports say what was measured; rhythm and taste are yours to
  judge with sound.

## Hardware and speed

Measured on a Windows 11 desktop, CPU only:

- Auto Edit of a 25 s clip with the `tiny` model, including verification and captions: about 25 s.
- Transcription with `small` or `medium` is several times slower than `tiny`; long recordings take minutes.
- Cartoon render of a 32 s video at 1080x1920 with 2 workers: about 2 minutes.

8 GB of RAM is enough for Auto Edit with `tiny`/`small`; the cartoon render and larger models want 16 GB.
A CUDA GPU speeds up transcription (`--device cuda`).

## Privacy

Your media never leaves your computer: transcription, analysis, editing and rendering run locally. The only
network access is downloading public dependencies (Python packages, the Whisper model, HyperFrames and
GSAP). This repository contains no media, recordings or personal data; the demo video is generated on your
machine by your own text-to-speech. Details and the audit used before publishing: [docs/privacy.md](docs/privacy.md).

## License

The original code and documentation are released under the [MIT License](LICENSE). Third-party parts keep
their own licenses, listed in [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md): the paper-cutout drawing
engine from drawn-by-code (MIT) and the fonts Anton and Patrick Hand (SIL Open Font License 1.1). FFmpeg,
HyperFrames (Apache-2.0), GSAP (GSAP Standard License), faster-whisper (MIT) and the Whisper models are
dependencies you install; they are not included here.

## Contributing

Issues and pull requests are welcome.

- Run the tests: `pip install -r .claude/skills/claude-autocut/requirements.txt pytest`, then `pytest`.
  The cartoon render test is opt-in: `AUTOCUT_RENDER_TESTS=1 pytest`.
- Run the content audit before a pull request: `python tools/audit_public_tree.py`.
- Never commit media, recordings, transcripts of real people, credentials or local paths.
- Keep the editor conservative: a change that cuts more must keep the gate, the verification and the
  protection of negations, and come with a test.

Architecture overview: [docs/architecture.md](docs/architecture.md).
