"""Structure of the skill, the CLI surface and the public-content audit."""
import re
import subprocess
import sys

from conftest import ROOT, SKILL


def frontmatter(text):
    m = re.match(r'^---\n(.*?)\n---\n', text, re.S)
    assert m, 'SKILL.md must start with a YAML frontmatter block'
    out = {}
    for line in m.group(1).splitlines():
        k, _, v = line.partition(':')
        assert _ and k.strip() and v.strip(), f'bad frontmatter line: {line!r}'
        out[k.strip()] = v.strip()
    return out


def test_skill_frontmatter():
    fm = frontmatter((SKILL / 'SKILL.md').read_text(encoding='utf-8'))
    assert fm['name'] == 'claude-autocut' == SKILL.name
    assert re.fullmatch(r'[a-z0-9-]{1,64}', fm['name'])
    assert 50 < len(fm['description']) <= 1024 and '<' not in fm['description']
    for term in ('video', 'captions', 'cartoon', 'pauses'):
        assert term in fm['description'].lower()


def test_skill_files_exist():
    for p in ('SKILL.md', 'requirements.txt', 'scripts/autocut.py', 'references/editing.md', 'references/cartoon.md',
              'references/troubleshooting.md', 'scripts/claude_autocut/cartoon_template/engine/LICENSE-drawn-by-code.txt'):
        assert (SKILL / p).exists(), p
    body = (SKILL / 'SKILL.md').read_text(encoding='utf-8')
    for ref in re.findall(r'`(references/[\w.-]+)`', body):
        assert (SKILL / ref).exists(), ref


def test_every_cli_command_documented_exists():
    out = subprocess.run([sys.executable, str(SKILL / 'scripts' / 'autocut.py'), '--help'], capture_output=True, text=True)
    assert out.returncode == 0
    cmds = set(re.findall(r'\{([a-z,]+)\}', out.stdout)[0].split(','))
    body = (SKILL / 'SKILL.md').read_text(encoding='utf-8') + (ROOT / 'README.md').read_text(encoding='utf-8')
    used = set(re.findall(r'autocut\.py"? (\w+)', body)) | set(re.findall(r'`(\w+) (?:VIDEO|PROJECT|input)', body))
    assert used and used <= cmds, used - cmds


def test_missing_input_exit_code(tmp_path):
    out = subprocess.run([sys.executable, str(SKILL / 'scripts' / 'autocut.py'), 'edit', str(tmp_path / 'none.mp4'),
                          '-o', str(tmp_path / 'p')], capture_output=True, text=True)
    assert out.returncode == 2 and 'not found' in out.stderr


def test_no_absolute_paths_or_private_data_in_code():
    out = subprocess.run([sys.executable, str(ROOT / 'tools' / 'audit_public_tree.py')], capture_output=True, text=True, cwd=ROOT)
    assert out.returncode == 0, out.stdout
