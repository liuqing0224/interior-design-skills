#!/usr/bin/env python3
"""Refresh only 2D test deliverables and record actual command runtimes."""
import json
from pathlib import Path
import subprocess
import sys
import time

ROOT=Path(__file__).resolve().parents[1]
SCRIPT=ROOT/'skills/interior-orchestrator/scripts'
P=ROOT/'projects/TEST-L-084'

def main():
    results=[]
    for project in [P/'history/v1.0',P]:
        for part in ['state','drawings','schedules','documents']:(project/part).mkdir(exist_ok=True)
        commands=[['project_tools.py','check',str(project/'model/project.json'),'--out',str(project/'state/model-check.json')],
            ['project_tools.py','schedules',str(project/'model/project.json'),'--out',str(project/'schedules')],
            ['export_drawings.py',str(project)],['export_pdf.py',str(project)]]
        if project==P:commands[-1] += ['--previous',str(P/'history/v1.0')]
        for command in commands:
            start=time.perf_counter();run=subprocess.run([sys.executable,str(SCRIPT/command[0]),*command[1:]],capture_output=True,text=True)
            duration=round(time.perf_counter()-start,4)
            if run.returncode:raise RuntimeError(run.stdout+run.stderr)
            results.append(dict(project=str(project.relative_to(ROOT)),command=command[0:2],seconds=duration,returncode=run.returncode))
    (P/'state/refresh-timing.json').write_text(json.dumps({'measurement':'local wall clock; not a human efficiency comparison','commands':results},ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(results,ensure_ascii=False))

if __name__=='__main__':main()
