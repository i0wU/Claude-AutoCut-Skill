# Architecture

```
video ──► Transcription (faster-whisper, word timestamps)
             │
             ▼
        Automatic Editing Engine
          analyze.py  sentences, pauses, retakes, repetitions, fillers, negations,
                      text over silence, audible sound without words
          plan.py     kept ranges (EDL) + classification of every removed span + gate
             │
             ▼
        Rendering Pipeline
          render.py   FFmpeg trim/concat on the frame grid, audio micro-fades
          edit.py     verification by re-transcription, versioned outputs, REPORT.md
             │
             ├──► Subtitle Engine
             │      captions.py  grouping, SRT, Pillow-drawn captions overlaid by FFmpeg
             │
             └──► Cartoon Animation Engine
                    cartoon.py   project, storyboard check, HTML composition,
                                 HyperFrames render, original audio copied, QC
                    cartoon_template/
                      engine/    paper-cutout drawing primitives (drawn-by-code, MIT)
                      library/   stage, divider, texts, scenarios, characters, objects
                      fonts/     Anton, Patrick Hand (OFL)
```

## Automatic Editing Engine

The engine works on words, not on waveforms alone. Each word carries its time, its transcription
confidence, whether it is a filler (by language), a negation, and how loud the audio under it is. Sentences
are built from punctuation and pauses. Two signals decide automatic cuts: structure (an incomplete take
followed by its full version; two full takes of the same sentence) and silence (pauses, lead-in, tail). Word
edges are corrected with the loudness envelope, because Whisper places them up to a few hundred
milliseconds early or late.

The gate is a classification of what leaves, not of what the plan intended: after the ranges are built, every
removed span is checked again against the words. Anything that removes unique speech is high impact and needs
a recorded approval.

## Rendering Pipeline

Kept ranges are snapped to whole video frames before trimming, so each segment has the same audio and video
length and the edit does not drift. Joins get 8 ms audio fades. The verification transcribes the result and
aligns it with the words that should be there; fillers and uncertain words are not counted as losses.

## Subtitle Engine

Words are mapped from the source timeline to the edit through the segment table. Captions break at sentence
ends, pauses longer than 0.45 s and a character budget (22 for vertical, 36 for horizontal video). Each
caption becomes a transparent PNG; FFmpeg's concat demuxer turns them into a timed overlay track (durations
are differences of frame-snapped times). Audio is copied.

## Cartoon Animation Engine

`cartoon init` copies the template, the video and the transcript into a project; it writes the words and a
per-frame voice envelope (used for the host's mouth) as JavaScript data. Claude writes `storyboard.json`; the
checker validates continuity, names and on-screen words. `build_html` writes a HyperFrames composition: a canvas
painted by the stage (`Palco.desenhar(t)`, a pure function of time), the divider canvas and the video element
(muted). A paused GSAP timeline only carries time to the stage. HyperFrames renders the frames; FFmpeg then
puts the original audio stream back without re-encoding, and the QC compares durations and the audio MD5
with the source.

## Data formats

- `transcript.json`: `{"language", "duration", "words": [{"text", "start", "end", "prob"}]}`. Any transcript
  in this shape can be passed with `--transcript`.
- `edl.json`: `{"ranges": [{"start", "end"}], "decisions": [...], "status": "ok|blocked", ...}`.
- `renders/cut_vN.timeline.json`: `{"segments": [{"src_start", "src_end", "out_start", "out_end"}]}`.
