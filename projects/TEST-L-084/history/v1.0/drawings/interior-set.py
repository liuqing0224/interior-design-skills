from pathlib import Path
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
