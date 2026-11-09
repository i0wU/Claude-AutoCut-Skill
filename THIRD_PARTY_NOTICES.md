# Third-party notices

## Included in this repository

| Component | Files | Author | License | License text |
|---|---|---|---|---|
| drawn-by-code paper-cutout engine (4 files, unchanged) | `.claude/skills/claude-autocut/scripts/claude_autocut/cartoon_template/engine/core.js`, `paper.js`, `kit.js`, `detail.js` | Copyright (c) 2026 illodev, https://github.com/illodev/drawn-by-code (commit 993968aba9dfb183ea04ecea256db85e0077fd09) | MIT | `cartoon_template/engine/LICENSE-drawn-by-code.txt` |
| Anton font | `cartoon_template/fonts/Anton-Regular.ttf` | Copyright 2020 The Anton Project Authors | SIL Open Font License 1.1 | `cartoon_template/fonts/OFL-Anton.txt` |
| Patrick Hand font | `cartoon_template/fonts/PatrickHand-Regular.ttf` | Copyright (c) 2010-2012 Patrick Wagesreiter | SIL Open Font License 1.1 | `cartoon_template/fonts/OFL-PatrickHand.txt` |

Only the four engine files above come from drawn-by-code. Its sound effects, example characters, example
scenes, rendered examples and scripts are not included. The fonts may be used, embedded and redistributed
with software under the OFL; they may not be sold by themselves.

Everything else in this repository (the Python package, the stage, the character, scenario and object
library, the documentation, the tests and the tools) is original to Claude AutoCut and released under the MIT
License in `LICENSE`.

## Installed separately (not included here)

| Dependency | How it is obtained | License |
|---|---|---|
| faster-whisper | `pip install` (requirements.txt) | MIT |
| CTranslate2 (used by faster-whisper) | `pip install` | MIT |
| Whisper models (CTranslate2 conversions) | downloaded from Hugging Face on first use | MIT (OpenAI Whisper weights) |
| NumPy | `pip install` | BSD-3-Clause |
| Pillow | `pip install` | MIT-CMU (HPND) |
| FFmpeg | installed by the user | LGPL-2.1+ / GPL depending on the build |
| HyperFrames 0.8.79 | `npx --yes hyperframes@0.8.79` (cartoon modes) | Apache-2.0 |
| GSAP 3.14.2 | `npm install` inside each cartoon project | GSAP Standard "No Charge" License (https://gsap.com/standard-license), not open source; not redistributed here |
| Node.js | installed by the user | MIT |
