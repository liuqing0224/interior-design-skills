#!/usr/bin/env python3
import json
from pathlib import Path
import re
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[1]
VALIDATOR=Path.home()/'.codex/skills/.system/skill-creator/scripts/quick_validate.py'

def main():
    if not VALIDATOR.is_file():raise SystemExit('Locate skill-creator/scripts/quick_validate.py first')
    skills=sorted((ROOT/'skills').glob('interior-*'));results=[];links=[]
    if len(skills)!=15:raise ValueError('Expected fifteen skills')
    for skill in skills:
        run=subprocess.run([sys.executable,str(VALIDATOR),str(skill)],capture_output=True,text=True)
        results.append({'skill':skill.name,'passed':run.returncode==0,'output':(run.stdout+run.stderr).strip()})
        for doc in skill.rglob('*.md'):
            for href in re.findall(r'\]\(([^)]+)\)',doc.read_text()):
                if '://' in href or href.startswith('#'):continue
                target=doc.parent/href.split('#')[0];links.append({'from':str(doc.relative_to(ROOT)),'target':href,'exists':target.is_file()})
    run=subprocess.run([sys.executable,'-m','unittest','discover','-s','tests','-v'],cwd=ROOT,capture_output=True,text=True)
    log=run.stdout+run.stderr;match=re.search(r'Ran (\d+) tests',log)
    out=ROOT/'validation';out.mkdir(exist_ok=True);(out/'v2-tests.txt').write_text(log)
    summary={'passed':all(row['passed'] for row in results) and all(row['exists'] for row in links) and run.returncode==0,
        'skill_validation':results,'relative_references':{'checked':len(links),'missing':[row for row in links if not row['exists']]},
        'behavior_tests':{'count':int(match.group(1)) if match else None,'passed':run.returncode==0}}
    (out/'v2-suite.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({'passed':summary['passed'],'skills':len(results),'references':len(links),'behavior_tests':summary['behavior_tests']},ensure_ascii=False))
    return 0 if summary['passed'] else 1

if __name__=='__main__':raise SystemExit(main())
