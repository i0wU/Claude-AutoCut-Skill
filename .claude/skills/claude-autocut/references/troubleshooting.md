# Troubleshooting

| Symptom | Cause and fix |
|---|---|
| `ffmpeg was not found on PATH` | Install FFmpeg and make sure `ffmpeg` and `ffprobe` run in a new terminal. |
| `faster-whisper is not installed` | Activate the virtual environment and `pip install -r requirements.txt`. |
| The first run is slow or downloads a lot | The Whisper model is downloaded once from Hugging Face (`tiny` ~75 MB, `small` ~480 MB, `medium` ~1.5 GB). Later runs reuse it. Set `HF_HOME` to choose where it is stored. |
| Words are wrong, language wrong | Pass `--language` (e.g. `en`, `pt`, `es`) and a larger model (`--model medium`). The transcript of a file is reused per model, so a new model transcribes again. |
| "text over silence" in the analysis | Whisper wrote text over a silent part (often fake subtitle credits). It is removed from the edit and from the cartoon. Nothing to do. |
| "audible sound without transcript ... was kept" | There is sound with no words (missed speech, laughter, music). It is never cut automatically. Listen; add a cut in `overrides.json` if it should go. |
| `stopped at the gate` | A manual cut removes words that are not said anywhere else. Show the span to the user; record an approval only with their explicit yes (`approve`), or remove the cut. |
| Verification FAILED | The edit was transcribed again and some expected words were not found. Open `verify_vN.json`, watch those moments; it can be a real clipped word or just a different reading by Whisper. |
| `npx (Node.js) was not found` | Install Node.js 18+ (cartoon modes only). |
| `GSAP is not installed in the project` | Run `npm install` inside the cartoon project folder (needs internet once). |
| HyperFrames render is slow or the machine runs out of memory | Rendering opens a headless browser per worker. Use `--workers 1`, close heavy programs, test a short part with `--range 0-6` first. |
| The HyperFrames CLI says an update is available | Ignore it: the skill pins `hyperframes@0.8.79` on purpose. |
| On-screen text error in `cartoon check` | The storyboard shows a word that is not spoken near that time. Use only words from `speech.md`. |
| Captions too big or covering a face | `--caption-size 54 --caption-y 0.8` (pixels, fraction of the height). |
| Windows console shows broken accents | Set `PYTHONIOENCODING=utf-8` before running the commands. |
