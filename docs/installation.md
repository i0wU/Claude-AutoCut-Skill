# Installation

## 1. Get the skill

```bash
git clone https://github.com/i0wU/Claude-AutoCut-Skill.git
```

Claude Code loads skills from `.claude/skills/` in the project you open and from `~/.claude/skills/` for
all projects. Use the repository folder as it is, or copy `.claude/skills/claude-autocut` to
`~/.claude/skills/claude-autocut`. The skill folder is self-contained: its `scripts/` hold all the code and
the cartoon template.

## 2. Python environment

Python 3.10 or newer.

```bash
python -m venv .venv
# Windows (PowerShell):  .venv\Scripts\Activate.ps1
# Windows (cmd):         .venv\Scripts\activate.bat
# macOS / Linux:         source .venv/bin/activate
pip install -r .claude/skills/claude-autocut/requirements.txt
```

If the skill is in `~/.claude/skills`, tell Claude the path of this Python (for example
`~/venvs/autocut/bin/python`) the first time you use it.

## 3. FFmpeg

| System | Command |
|---|---|
| Windows | `winget install Gyan.FFmpeg` (or download a build from https://ffmpeg.org/download.html and add `bin` to PATH) |
| macOS | `brew install ffmpeg` |
| Debian/Ubuntu | `sudo apt install ffmpeg` |

Open a new terminal and check `ffmpeg -version` and `ffprobe -version`.

## 4. Node.js (cartoon modes only)

Node.js 18 or newer from https://nodejs.org (includes npm and npx). The first cartoon render runs
`npx --yes hyperframes@0.8.79`, which downloads HyperFrames and a headless browser once. Each cartoon project
runs `npm install` to get GSAP 3.14.2. The version of HyperFrames is pinned; the CLI may announce newer
versions, which the skill does not use.

## 5. Check

```bash
python .claude/skills/claude-autocut/scripts/autocut.py doctor
```

It lists every dependency and which modes are ready.

## Models and offline use

The first transcription downloads a Whisper model from Hugging Face into its cache
(`~/.cache/huggingface` by default; set `HF_HOME` to change it). After that, Auto Edit and Captions work
offline. The cartoon mode needs internet once per machine (HyperFrames) and once per project (GSAP).

## Optional: the `autocut` command

`pip install .` in the repository root installs the same code as a package with an `autocut` command
(`autocut doctor`, `autocut edit ...`).

## Uninstall

Delete the skill folder, the virtual environment and, if you want the space back, the Whisper models in the
Hugging Face cache and the npx cache (`npm cache clean --force`).
