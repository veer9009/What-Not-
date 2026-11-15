"""Read-only heuristic scan; emits locations/rule names, never matched values.

Not a replacement for Gitleaks. Run from repository root with the backend Python.
"""
import importlib.metadata as metadata
import importlib.util
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys


def git(*args):
    return subprocess.check_output(['git', *args])


RULES = {
    'private-key': re.compile(r'-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----'),
    'aws-access-key': re.compile(r'\b(?:AKIA|ASIA)[A-Z0-9]{16}\b'),
    'service-token': re.compile(r'\b(?:gh[pousr]_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{50,}|sk_live_[A-Za-z0-9]{15,})'),
    'credential-url': re.compile(r'(?:postgres(?:ql)?(?:\+psycopg)?|mysql|mongodb(?:\+srv)?|redis)://[^\s:@]+:[^\s@]+@'),
    'literal-secret': re.compile(r'''(?i)(?:jwt_secret_key|api_key|secret_key|smtp_password|access_token|password)\s*[:=]\s*["']([^"'\n]{8,})["']'''),
}


def scan(label, data):
    if b'\0' in data:
        return []
    return [dict(path=label, line=n, rule=rule)
            for n, line in enumerate(data.decode('utf-8', 'replace').splitlines(), 1)
            for rule, pattern in RULES.items() if pattern.search(line)]


def main():
    print('Python', sys.version.split()[0])
    for package in ['fastapi', 'starlette', 'pydantic', 'pytest', 'SQLAlchemy', 'PyJWT', 'argon2-cffi']:
        print(package, metadata.version(package))
    for tool in ['gitleaks', 'pip-audit', 'bandit', 'semgrep', 'trivy', 'node', 'npm', 'pnpm']:
        print('TOOL', tool, shutil.which(tool) or 'UNAVAILABLE ON PATH')
    for module in ['pip_audit', 'bandit', 'semgrep']:
        print('MODULE', module, bool(importlib.util.find_spec(module)))
    tracked = [p for p in git('ls-files', '-z').decode().split('\0') if p]
    hits = []
    for name in tracked:
        path = Path(name)
        if path.is_file():
            hits.extend(scan(name, path.read_bytes()))
    print('TRACKED_FILES', len(tracked))
    print('TRACKED_CANDIDATES', json.dumps(hits))
    for name in ['backend/.env', '.env', '.env.local']:
        path = Path(name)
        if path.exists():
            ignored = subprocess.run(['git', 'check-ignore', '-q', name]).returncode == 0
            print('LOCAL_ENV', name, 'ignored', ignored)
            print('LOCAL_CANDIDATES', json.dumps(scan(name, path.read_bytes())))
    objects = git('rev-list', '--objects', '--all').decode().splitlines()
    batch = subprocess.Popen(['git', 'cat-file', '--batch'], stdin=subprocess.PIPE, stdout=subprocess.PIPE)
    hits, blobs = [], 0
    try:
        for obj in objects:
            oid, _, name = obj.partition(' ')
            batch.stdin.write((oid + '\n').encode())
            batch.stdin.flush()
            header = batch.stdout.readline().split()
            data = batch.stdout.read(int(header[2]))
            batch.stdout.read(1)
            if header[1] == b'blob':
                blobs += 1
                hits.extend(scan(oid[:12] + ':' + name, data))
    finally:
        batch.stdin.close()
        batch.wait()
    print('REACHABLE_COMMITS', git('rev-list', '--all', '--count').decode().strip())
    print('HISTORY_BLOBS', blobs)
    print('HISTORY_CANDIDATES', json.dumps(hits))
    if '--artifacts' in sys.argv:
        # Include ignored logs/dist and untracked audit files, but never installed
        # dependencies, Git internals, caches or other directories outside this repo.
        excluded = {'.git', 'node_modules', '.venv', 'venv', '__pycache__',
                    '.pytest_cache', '.superpowers', '.audit-npm-cache'}
        hits, count = [], 0
        for parent, directories, files in os.walk('.'):
            directories[:] = [name for name in directories if name not in excluded]
            for name in files:
                path = Path(parent) / name
                if path.stat().st_size > 10_000_000:
                    continue
                count += 1
                hits.extend(scan(path.as_posix(), path.read_bytes()))
        print('WORKSPACE_ARTIFACT_FILES', count)
        print('WORKSPACE_ARTIFACT_CANDIDATES', json.dumps(hits))


if __name__ == '__main__':
    main()
