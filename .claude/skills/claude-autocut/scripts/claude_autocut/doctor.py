"""Dependency check: what is installed, what each mode needs, and what is missing."""
from __future__ import annotations

import importlib
import platform
import shutil
import sys

from .common import run


def _version(cmd):
    path = shutil.which(cmd[0])
    if not path:
        return None
    r = run([path, *cmd[1:]])
    return (r.stdout or r.stderr).strip().splitlines()[0] if r.returncode == 0 and (r.stdout or r.stderr) else 'found'


def _module(name):
    try:
        m = importlib.import_module(name)
        return getattr(m, '__version__', 'installed')
    except Exception:
        return None


def doctor() -> dict:
    py_ok = sys.version_info >= (3, 10)
    checks = {
        'python': {'value': platform.python_version(), 'ok': py_ok, 'need': '3.10 or newer'},
        'faster_whisper': {'value': _module('faster_whisper'), 'need': 'pip install -r requirements.txt'},
        'numpy': {'value': _module('numpy'), 'need': 'pip install -r requirements.txt'},
        'pillow': {'value': _module('PIL'), 'need': 'pip install -r requirements.txt'},
        'ffmpeg': {'value': _version(['ffmpeg', '-version']), 'need': 'FFmpeg on PATH (https://ffmpeg.org/download.html)'},
        'ffprobe': {'value': _version(['ffprobe', '-version']), 'need': 'comes with FFmpeg'},
        'node': {'value': _version(['node', '--version']), 'need': 'Node.js 18+ (cartoon mode only)'},
        'npx': {'value': _version(['npx.cmd' if shutil.which('npx.cmd') else 'npx', '--version']), 'need': 'comes with Node.js (cartoon mode only)'},
    }
    for k, c in checks.items():
        c.setdefault('ok', bool(c['value']))
    auto = all(checks[k]['ok'] for k in ('python', 'faster_whisper', 'numpy', 'pillow', 'ffmpeg', 'ffprobe'))
    cartoon = auto and checks['node']['ok'] and checks['npx']['ok']
    return {'checks': checks, 'modes': {'auto_edit': auto, 'captions': auto, 'cartoon': cartoon, 'full_animated': cartoon,
                                        'complete': cartoon},
            'notes': ['the first transcription downloads the Whisper model from Hugging Face (tiny ~75 MB, small ~480 MB)',
                      'the first cartoon render downloads hyperframes@0.8.79 through npx and a headless browser',
                      'the cartoon project installs gsap 3.14.2 with npm (GSAP Standard License, not bundled here)']}
