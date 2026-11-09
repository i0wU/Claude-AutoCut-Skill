#!/usr/bin/env python3
"""Audit the files that would be published: secrets, personal data, private paths, media and odd files.

    python tools/audit_public_tree.py [--deny-file private_terms.txt] [files...]

Without file arguments it audits `git ls-files` plus staged files. `--deny-file` is a local, never committed,
list of extra terms (one per line) that must not appear anywhere (names, hostnames, private projects).
Exit code 1 when anything is found. Values that look like secrets are never printed, only where they are.
"""
import argparse
import os
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

SECRET_PATTERNS = {
    'private key block': r'-----BEGIN (?:RSA |EC |OPENSSH |DSA |PGP )?PRIVATE KEY-----',
    'AWS access key': r'\bAKIA[0-9A-Z]{16}\b',
    'GitHub token': r'\b(?:gh[pousr]_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{40,})\b',
    'Slack token': r'\bxox[abposr]-[A-Za-z0-9-]{10,}\b',
    'Google API key': r'\bAIza[0-9A-Za-z_\-]{35}\b',
    'OpenAI/Anthropic key': r'\bsk-(?:ant-)?[A-Za-z0-9_\-]{20,}\b',
    'Hugging Face token': r'\bhf_[A-Za-z0-9]{30,}\b',
    'JWT': r'\beyJ[A-Za-z0-9_\-]{10,}\.[A-Za-z0-9_\-]{10,}\.[A-Za-z0-9_\-]{10,}\b',
    'bearer header': r'(?i)authorization:\s*bearer\s+[A-Za-z0-9._\-]{16,}',
    'assigned secret': r'(?i)\b(?:api[_-]?key|secret|password|passwd|token|access[_-]?key)\b\s*[:=]\s*[\'"][^\'"\s]{8,}[\'"]',
    'URL with credentials': r'https?://[^/\s:@]+:[^/\s@]+@',
}
PERSONAL_PATTERNS = {
    'Windows user folder': r'(?i)[A-Z]:\\+Users\\+(?!<|\{|you\b|name\b|USER)[^\\\s"\'<>]+',
    'Unix home folder': r'(?<![\w.])/(?:home|Users)/(?!<|\{|you\b|name\b|runner\b)[A-Za-z0-9._-]+',
    'e-mail address': r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b',
    'phone number': r'(?<!\d)(?:\+\d{1,3}[\s-]?)?\(?\d{2,3}\)?[\s-]?9?\d{4}[\s-]\d{4}(?!\d)',
    'CPF': r'\b\d{3}\.\d{3}\.\d{3}-\d{2}\b',
}
# e-mails that are allowed: GitHub noreply, example domains, and the font author's notice required by the OFL
ALLOWED_EMAILS = re.compile(r'(?i)(@users\.noreply\.github\.com|@example\.(?:com|org)|^mail@patrickwagesreiter\.at$|^noreply@anthropic\.com$)')
MEDIA_EXT = {'.mp4', '.mov', '.mkv', '.webm', '.avi', '.m4v', '.wav', '.mp3', '.m4a', '.aac', '.flac', '.ogg',
             '.png', '.jpg', '.jpeg', '.gif', '.webp', '.heic', '.bmp', '.tif', '.tiff', '.psd'}
FORBIDDEN_NAMES = re.compile(r'(?i)(^|/)(\.env(\..*)?|.*\.pem|.*\.key|id_rsa.*|.*\.p12|.*\.pfx|cookies?\.(txt|json|sqlite)|'
                             r'.*\.sqlite3?|.*\.db|credentials.*\.json|secrets?\..*|\.netrc|\.npmrc|\.pypirc)$')
BINARY_OK = {'.ttf', '.otf'}
MAX_BYTES = 5 * 1024 * 1024


SKIP_DIRS = {'.git', 'venv', '__pycache__', 'node_modules', '.pytest_cache'}


def tracked_files():
    """Files git would publish; outside a git checkout, every file of the tree (minus caches and envs)."""
    out = subprocess.run(['git', 'ls-files', '-z', '--cached', '--others', '--exclude-standard'], cwd=ROOT,
                         capture_output=True, text=True, encoding='utf-8')
    if out.returncode == 0:
        return [f for f in out.stdout.split('\0') if f]
    files = []
    for dirpath, dirnames, filenames in os.walk(ROOT):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS and not d.startswith('.venv')]
        files += [os.path.relpath(os.path.join(dirpath, f), ROOT).replace(os.sep, '/') for f in filenames]
    return files


def audit(files, deny):
    findings = []
    for rel in files:
        p = ROOT / rel
        if p.is_symlink():
            findings.append((rel, 'symlink'))
            continue
        if not p.is_file():
            continue
        if FORBIDDEN_NAMES.search(rel.replace(os.sep, '/')):
            findings.append((rel, 'forbidden file name (secrets, keys, cookies or databases)'))
        ext = p.suffix.lower()
        if ext in MEDIA_EXT:
            findings.append((rel, 'media file (no media may be published)'))
        size = p.stat().st_size
        if size > MAX_BYTES:
            findings.append((rel, f'large file ({size // 1024} KB)'))
        data = p.read_bytes()
        if ext in BINARY_OK:
            text = data.decode('latin-1')
        else:
            try:
                text = data.decode('utf-8')
            except UnicodeDecodeError:
                findings.append((rel, 'binary file that is not a font'))
                continue
        for line_no, line in enumerate(text.splitlines(), 1):
            for name, pat in SECRET_PATTERNS.items():
                if re.search(pat, line):
                    findings.append((f'{rel}:{line_no}', f'possible secret: {name}'))
            for name, pat in PERSONAL_PATTERNS.items():
                for m in re.finditer(pat, line):
                    if name == 'e-mail address' and ALLOWED_EMAILS.search(m.group(0)):
                        continue
                    findings.append((f'{rel}:{line_no}', f'{name}: {m.group(0)[:60]}'))
            low = line.lower()
            for term in deny:
                if term in low:
                    findings.append((f'{rel}:{line_no}', 'term from the private deny list'))
    return findings


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('files', nargs='*')
    ap.add_argument('--deny-file')
    a = ap.parse_args()
    deny = []
    if a.deny_file:
        deny = [t.strip().lower() for t in Path(a.deny_file).read_text(encoding='utf-8').splitlines() if t.strip() and not t.startswith('#')]
    files = a.files or tracked_files()
    found = audit(files, deny)
    for where, what in found:
        print(f'{where}: {what}')
    print(f'{len(files)} files audited, {len(found)} finding(s)')
    return 1 if found else 0


if __name__ == '__main__':
    sys.exit(main())
