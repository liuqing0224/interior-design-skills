from pathlib import Path
import importlib.util
import json

def gen_dxf():
    project=Path(__file__).resolve().parents[1]
    root=project.parents[1]
    source=root/'skills/interior-orchestrator/scripts/drawing_lib.py'
    spec=importlib.util.spec_from_file_location('interior_drawing_lib',source)
    lib=importlib.util.module_from_spec(spec);spec.loader.exec_module(lib)
    return lib.dxf_document(json.loads((project/'model/project.json').read_text()))
