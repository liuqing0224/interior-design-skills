#!/usr/bin/env python3
"""Install all fifteen skills without replacing any existing directory."""
import argparse
import hashlib
import shutil
import datetime as dt
import tempfile
from pathlib import Path

def manifest(root):
    return {str(p.relative_to(root)):hashlib.sha256(p.read_bytes()).hexdigest() for p in root.rglob('*') if p.is_file() and '__pycache__' not in p.parts and p.suffix!='.pyc'}

def main():
    p=argparse.ArgumentParser();p.add_argument('--target',type=Path,default=Path.home()/'.codex/skills');p.add_argument('--check',action='store_true');p.add_argument('--update-from',type=Path,help='Previously delivered package root; only exact known versions may be updated');a=p.parse_args()
    sources=sorted((Path(__file__).parent/'skills').glob('interior-*'));target=a.target.expanduser()
    if len(sources)!=15:raise SystemExit('Expected exactly fifteen skills')
    if a.check:
        bad=[s.name for s in sources if not (target/s.name).is_dir() or manifest(s)!=manifest(target/s.name)]
        if bad:raise SystemExit('Mismatch: '+', '.join(bad))
        print('PASS: all 15 installed skills match canonical files');return
    conflicts=[s.name for s in sources if (target/s.name).exists()]
    if a.update_from:
        baseline=a.update_from.resolve()/'skills'
        if not baseline.is_dir():raise SystemExit('Missing baseline skills directory')
        unknown=[s.name for s in sources if (target/s.name).exists() and (not (target/s.name).is_dir() or (target/s.name).is_symlink() or not (baseline/s.name).is_dir() or manifest(target/s.name) not in [manifest(baseline/s.name),manifest(s)])]
        if unknown:raise SystemExit('No files written; unrecognized installed content: '+', '.join(unknown))
        target.mkdir(parents=True,exist_ok=True)
        backup=target.parent/'interior-skill-backups'/dt.datetime.now().strftime('%Y%m%d-%H%M%S-%f')
        backup.mkdir(parents=True)
        changed=[]
        with tempfile.TemporaryDirectory(prefix='.interior-stage-',dir=target.parent) as staging:
            stage=Path(staging)
            for s in sources:shutil.copytree(s,stage/s.name,ignore=shutil.ignore_patterns('__pycache__','*.pyc'))
            try:
                for s in sources:
                    dest=target/s.name;old=backup/s.name
                    if dest.exists():dest.rename(old)
                    changed.append((dest,old))
                    (stage/s.name).rename(dest)
                if any(manifest(s)!=manifest(target/s.name) for s in sources):raise ValueError('Post-update byte check failed')
            except Exception:
                for dest,old in reversed(changed):
                    if dest.exists():shutil.rmtree(dest)
                    if old.exists():old.rename(dest)
                raise
        print('Updated 15 known skills; previous files saved at '+str(backup));return
    if conflicts:raise SystemExit('No files written; existing directories: '+', '.join(conflicts))
    target.mkdir(parents=True,exist_ok=True)
    copied=[]
    try:
        for source in sources:
            shutil.copytree(source,target/source.name,ignore=shutil.ignore_patterns('__pycache__','*.pyc'));copied.append(target/source.name)
    except Exception:
        for path in copied:shutil.rmtree(path)
        raise
    print('Installed 15 skills into '+str(target))
if __name__=='__main__':main()
