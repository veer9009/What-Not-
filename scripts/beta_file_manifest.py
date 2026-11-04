"""Generate the review manifest from git status without changing the index."""
from pathlib import Path
import subprocess

root=Path(__file__).resolve().parents[1]
lines=subprocess.check_output(['git','-c','core.quotepath=false','status','--porcelain=v1','--untracked-files=all'],cwd=root,text=True).splitlines()
result=['# Controlled-beta working-tree file manifest','','Relative to HEAD `861c2cb`; includes inherited work and this continuation.',
        '',f'Files: **{len(lines)}**.','','| Git status | File |','| --- | --- |']
result.extend(f'| `{line[:2].strip()}` | `{line[3:]}` |' for line in lines)
result.extend(['','The ignored `.superpowers/beta-progress.md` ledger was also updated.',
    'Test logs, temporary PostgreSQL/Edge profiles and ignored dist output are not source changes.',
    'No file was staged, committed or pushed.'])
(root/'docs/BETA_CHANGED_FILES.md').write_text('\n'.join(result)+'\n',encoding='utf-8')
print(f'{len(lines)} changed/new source and documentation files')
