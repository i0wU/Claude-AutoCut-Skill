# Examples

Everything here is synthetic. No real recording is included in this repository.

## A demo video

```bash
python examples/make_demo_video.py demo.mp4              # 1280x720, English
python examples/make_demo_video.py demo_v.mp4 --vertical # 1080x1920
python examples/make_demo_video.py demo_pt.mp4 --lang pt # Portuguese
```

The speech comes from your system's text-to-speech (Windows SAPI, macOS `say`, Linux `espeak-ng`) over
FFmpeg's test pattern. The script includes a redone take ("Today I will show you" twice), long pauses, a
filler ("Um") and a negation ("this is not magic"), so the editor has something to do. Text-to-speech voices
are harder to transcribe than people; use `--model small` or larger if the transcript looks wrong.

## Auto Edit

```bash
python .claude/skills/claude-autocut/scripts/autocut.py edit demo.mp4 -o edits/demo --model tiny
```

Expected: the lead-in silence and the incomplete take are removed, pauses are shortened, "not" stays,
`REPORT.md` says the verification passed.

## Cartoon

```bash
python .claude/skills/claude-autocut/scripts/autocut.py cartoon init demo_v.mp4 -o cartoons/demo --model small
```

`storyboard_example.json` shows the shape of a storyboard for a 32-second video with five scenes. Times and
words depend on your transcript: use it as a template, write the scenes from `cartoons/demo/speech.md`, and
run `cartoon check` until it reports no errors.
