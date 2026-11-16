"""Scan staged source additions without printing credential values."""
from pathlib import Path
import re
import subprocess

root = Path(__file__).resolve().parents[2]
status = subprocess.check_output(['git', 'status', '--porcelain', '--untracked-files=all'], cwd=root).decode('utf-8', 'replace')
evidence = root / 'docs/security/evidence/refresh-session-git-status.txt'
evidence.parent.mkdir(parents=True, exist_ok=True)
evidence.write_text(status, encoding='utf-8')
entries = status.splitlines()
print(f'Git status: {sum(line.startswith("??") for line in entries)} untracked files; '
      f'{sum(not line.startswith("??") for line in entries)} tracked changes; '
      f'{sum(line[0] not in " ?" for line in entries)} staged changes.')
tracked = subprocess.check_output(['git', 'diff', '--cached', '--unified=0', '--no-ext-diff'], cwd=root, stderr=subprocess.DEVNULL).decode('utf-8', 'replace')
untracked = subprocess.check_output(['git', 'ls-files', '--others', '--exclude-standard'], cwd=root).decode().splitlines()
patterns = {
    'AWS access key': re.compile(r'\b(?:AKIA|ASIA)[A-Z0-9]{16}\b'),
    'private key': re.compile(r'-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----'),
    'GitHub token': re.compile(r'\b(?:gh[pousr]_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{50,})\b'),
    'credentialed connection URL': re.compile(r'postgres(?:ql)?(?:\+psycopg)?://[^\s:/]+:[^\s@]+@'),
}
chunks = [('staged additions', '\n'.join(line[1:] for line in tracked.splitlines() if line.startswith('+') and not line.startswith('+++')))]
for name in untracked:
    path = root / name
    if path.suffix in {'.py', '.ts', '.tsx', '.md', '.css', '.mjs'} and path.is_file():
        chunks.append((name, path.read_text(encoding='utf-8', errors='replace')))
findings = []
for name, content in chunks:
    for kind, pattern in patterns.items():
        if pattern.search(content):
            findings.append((name, kind))
print(f'Scanned staged additions and {len(chunks)-1} untracked source/document files.')
for name, kind in findings:
    print(f'REVIEW: {name}: {kind} pattern (value omitted)')
print(f'Pattern findings: {len(findings)}; pattern scanning cannot prove absence of secrets.')
