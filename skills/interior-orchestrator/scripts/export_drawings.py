#!/usr/bin/env python3
import argparse
import json
from pathlib import Path
from drawing_lib import SHEETS,plan,svg,dxf_document,sheet_layout,scene_bounds,save_dxf
from project_tools import check,dump,sha

def main():
    p=argparse.ArgumentParser();p.add_argument('project',type=Path);a=p.parse_args()
    m=json.loads((a.project/'model/project.json').read_text(encoding='utf-8'));out=a.project/'drawings';out.mkdir(exist_ok=True)
    result=check(m)
    if not result['passed']:raise SystemExit(json.dumps(result,ensure_ascii=False))
    for code,title,kind in SHEETS:svg(plan(m,kind),out/(code+'.svg'),title)
    doc=dxf_document(m);save_dxf(doc,out/'interior-set.dxf')
    (out/'interior-set.py').write_text('''from pathlib import Path
import json
import sys

HERE=Path(__file__).resolve().parent
ROOT=next((p for p in HERE.parents if (p/'skills/interior-orchestrator/scripts/drawing_lib.py').is_file()),None)
if ROOT is None:raise RuntimeError('Keep the generator inside the complete skills project package')
sys.path.insert(0,str(ROOT/'skills/interior-orchestrator/scripts'))
from drawing_lib import dxf_document,save_dxf

def gen_dxf():
    return dxf_document(json.loads((HERE.parent/'model/project.json').read_text(encoding='utf-8')))

if __name__=='__main__':save_dxf(gen_dxf(),HERE/'interior-set.dxf')
''',encoding='utf-8',newline='\n')
    dump(out/'drawing-manifest.json',{'revision':m['revision'],'model_sha256':sha(a.project/'model/project.json'),
        'generator_sha256':sha(Path(__file__).with_name('drawing_lib.py')),
        'sheets':[{'code':code,'title':title,'kind':kind,'offset_mm':[ox,oy],'bounds_mm':scene_bounds(s)} for (code,title,kind),(s,ox,oy) in zip(SHEETS,sheet_layout(m))]})
    print('Exported 6 SVG drawings and one 1:1 mm DXF drawing set')
if __name__=='__main__':main()
