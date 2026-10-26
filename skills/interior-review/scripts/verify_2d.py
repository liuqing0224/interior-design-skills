#!/usr/bin/env python3
"""Read back SVG/DXF/PDF/XLSX/CSV, independent of a specific home or drawing size."""
import argparse
import csv
from decimal import Decimal,ROUND_HALF_UP
import json
from pathlib import Path
import sys
import xml.etree.ElementTree as ET
import ezdxf
from openpyxl import load_workbook
from pypdf import PdfReader

SCRIPTS=Path(__file__).resolve().parents[2]/'interior-orchestrator/scripts'
sys.path.insert(0,str(SCRIPTS))
import project_tools as t

def require(value,message):
    if not value:raise ValueError(message)

def bounds(e):
    pts=list(e.get_points('xy'));xs=[p[0] for p in pts];ys=[p[1] for p in pts]
    return [min(xs),min(ys),max(xs)-min(xs),max(ys)-min(ys)]

def close(a,b):return len(a)==len(b) and all(abs(x-y)<.01 for x,y in zip(a,b))

def object_id(e):
    return e.get_xdata('INTERIOR')[0].value if e.has_xdata('INTERIOR') else None

def independent_budget(m):
    """Separate implementation of model measurement and decimal arithmetic."""
    D=lambda v:Decimal(str(v))
    rounded=lambda v,places:v.quantize(Decimal(places),rounding=ROUND_HALF_UP)
    rows=[]
    for item in m['budget']:
        rule=item.get('quantity_rule');q=D(item['quantity'])
        if rule:
            k=rule['kind']
            if k in ['floor','net_area']:
                q=sum((D(r['rect'][2])*D(r['rect'][3])/D(1000000) for r in m['rooms'] if k=='net_area' or r['floor'] in rule['materials']),D(0))
            else:
                pool=m[rule.get('collection','furniture')];selected=[x for x in pool if 'ids' not in rule or x['id'] in rule['ids']]
                if k=='count':q=D(len(selected))
                else:
                    q=D(0)
                    for f in selected:
                        w,d=f['rect'][2:];axis=f.get('front_axis','x' if w>=d else 'y');front=D(w if axis=='x' else d)
                        q+=front/D(1000) if k=='length' else front*D(f['height_mm'])/D(1000000)
        q=rounded(q,'.0001');purchase=rounded(q*(D(1)+D(item.get('waste',0))),'.0001');amount=rounded(purchase*D(item['rate']),'.01')
        rows.append((item['id'],q,purchase,amount))
    base=sum((row[3] for row in rows),D(0));reserve=rounded(base*D(m['reserve_rate']),'.01');total=base+reserve
    return rows,dict(base=base,reserve=reserve,total=total,remaining=D(m['budget_cny'])-total)

def verify(p,records=False):
    p=Path(p).resolve();m=t.load(p/'model/project.json');source=t.sha(p/'model/project.json');result=t.check(m)
    require(result['passed'],'Model check failed')
    manifest=t.load(p/'drawings/drawing-manifest.json')
    require(manifest['model_sha256']==source and manifest['revision']==m['revision'],'Stale drawing input')
    require(manifest['generator_sha256']==t.sha(SCRIPTS/'drawing_lib.py'),'Drawing generator changed; regenerate drawings')
    require(len(manifest['sheets'])==6,'Expected six drawing sheets')
    doc=ezdxf.readfile(p/'drawings/interior-set.dxf');audit=doc.audit();ms=doc.modelspace()
    require(not audit.errors and not audit.fixes,'DXF audit failed')
    require(doc.units==4 and doc.header['$INSUNITS']==4,'DXF units differ')
    require(all(e.closed for e in ms.query('LWPOLYLINE')),'Unclosed DXF rectangles')
    rect_count=0
    for sheet in manifest['sheets']:
        code=sheet['code'];ox,oy=sheet['offset_mm']
        root=ET.parse(p/'drawings'/(code+'.svg')).getroot()
        require(root.tag.endswith('svg'),'Malformed SVG')
        vx,vy,vw,vh=map(float,root.attrib['viewBox'].split())
        for r in root.findall('{http://www.w3.org/2000/svg}rect'):
            x,y,w,h=[float(r.attrib[key]) for key in ['x','y','width','height']]
            require(w>=0 and h>=0 and x>=vx-.1 and y>=vy-.1 and x+w<=vx+vw+.1 and y+h<=vy+vh+.1,'SVG rectangle is clipped')
        if sheet['kind']=='joinery':continue
        actual={object_id(e):bounds(e) for e in ms.query(f'LWPOLYLINE[layer=="{code}_FLOOR"]')}
        require(set(actual)=={r['id'] for r in m['rooms']},'DXF room IDs differ')
        for room in m['rooms']:
            x,y,w,d=room['rect'];require(close(actual[room['id']],[x+ox,y+oy,w,d]),'DXF room dimensions differ: '+room['id']);rect_count+=1
        lines=list(ms.query(f'LINE[layer=="{code}_DIMENSION"]'))
        require(any(abs(abs(e.dxf.end.x-e.dxf.start.x)-m['envelope'][2])<.01 for e in lines),'Missing total X dimension')
        require(any(abs(abs(e.dxf.end.y-e.dxf.start.y)-m['envelope'][3])<.01 for e in lines),'Missing total Y dimension')
    furniture={object_id(e):bounds(e) for e in ms.query('LWPOLYLINE[layer=="ID-01_FURNITURE"]')}
    for f in m['furniture']:require(f['id'] in furniture and close(furniture[f['id']],f['rect']),'DXF furniture differs: '+f['id'])
    labels={e.dxf.text for e in ms.query('TEXT')}
    require(all(o['id']+' '+str(o['width']) in labels for o in m['openings']),'DXF opening labels differ')
    elevations={object_id(e):bounds(e) for e in ms.query('LWPOLYLINE[layer=="ID-06_JOINERY_ELEVATION"]')}
    sections={object_id(e):bounds(e) for e in ms.query('LWPOLYLINE[layer=="ID-06_JOINERY_SECTION"]')}
    allcab={f['id']:f for f in m['furniture'] if f['kind']=='joinery'}
    selected=m.get('drawing',{}).get('joinery_ids')
    if selected is not None:require(set(elevations)==set(selected),'Cabinet selection differs')
    for id,r in elevations.items():
        f=allcab[id];w,d=f['rect'][2:];front=w if f.get('front_axis','x' if w>=d else 'y')=='x' else d;depth=d if front==w else w
        require(close(r[2:],[front,f['height_mm']]),'Cabinet elevation dimensions differ: '+id)
        require(close(sections[id][2:],[depth,f['height_mm']]),'Cabinet section dimensions differ: '+id)
    with (p/'schedules/joinery.csv').open(encoding='utf-8-sig') as stream:cabinets=list(csv.DictReader(stream))
    require({row['id'] for row in cabinets}==set(allcab),'Cabinet schedule IDs differ')
    for row in cabinets:
        f=allcab[row['id']];w,d=f['rect'][2:];front=w if f.get('front_axis','x' if w>=d else 'y')=='x' else d
        require(float(row['front_width_mm'])==front and float(row['height_mm'])==f['height_mm'],'Cabinet schedule stale')
    rows,budget=independent_budget(m)
    bookpath=p/'schedules'/(m['title']+'_预算.xlsx')
    evidence=t.load(p/'state/workbook-check.json')
    require(evidence['model_sha256']==source and evidence['xlsx_sha256']==t.sha(bookpath),'Workbook source/output hash differs')
    cached=load_workbook(bookpath,data_only=True,read_only=True);formulas=load_workbook(bookpath,data_only=False,read_only=True)
    require(cached.sheetnames==['预算总览','工程量计价'],'Workbook sheets differ')
    for key,cell in evidence['cells'].items():require(abs(Decimal(str(cached['预算总览'][cell].value))-budget[key])<Decimal('.005'),'Workbook summary differs: '+key)
    for i,(id,q,purchase,amount) in enumerate(rows,5):
        s=cached['工程量计价'];require(s[f'A{i}'].value==id,'Workbook row ID differs')
        for col,wanted in [('D',q),('G',purchase),('I',amount)]:require(abs(Decimal(str(s[f'{col}{i}'].value))-wanted)<Decimal('.00001'),'Workbook quantity/amount differs: '+id+'/'+col)
        require(formulas['工程量计价'][f'I{i}'].data_type=='f','Missing amount formula')
    cached.close();formulas.close()
    with (p/'schedules/budget.csv').open(encoding='utf-8-sig') as stream:csvrows=list(csv.DictReader(stream))
    require(len(csvrows)==len(rows),'Budget CSV row count differs')
    for actual,(id,q,purchase,amount) in zip(csvrows,rows):require(actual['id']==id and Decimal(actual['quantity'])==q and Decimal(actual['amount'])==amount,'Budget CSV differs')
    require('matched 0 entries' in (p/'state/workbook-error-scan.txt').read_text(),'Workbook errors detected')
    pm=t.load(p/'documents/pdf-manifest.json');require(pm['model_sha256']==source,'PDF source hash differs')
    pdf=PdfReader(p/'documents'/pm['file']);require(len(pdf.pages)==pm['pages'],'PDF page count differs')
    texts=[page.extract_text() or '' for page in pdf.pages]
    require(m['title'] in texts[0] and f'{budget["total"]:,.2f}' in texts[0],'PDF title/budget differs')
    require(all(row['code'] in texts[-6+i] for i,row in enumerate(manifest['sheets'])),'PDF drawing IDs differ')
    require(all(abs(float(page.mediabox.width)-1190.5512)<.1 and abs(float(page.mediabox.height)-841.8898)<.1 for page in pdf.pages),'PDF paper size differs')
    require(any('/FontFile2' in font.get_object()['/FontDescriptor'].get_object() for font in pdf.pages[0]['/Resources']['/Font'].values() if '/FontDescriptor' in font.get_object()),'PDF TrueType font not embedded')
    latest={}
    if records:
        for row in t.load(p/'state/execution-log.json'):latest[row['skill']]=row
        require(set(latest)=={'interior-orchestrator','interior-layout','interior-drawings','interior-cost','interior-review'},'Transfer scope requires five actual skill records')
        for name,row in latest.items():
            require(row['input_sha256']==source and row['skill_sha256']==t.sha(SCRIPTS.parents[1]/name/'SKILL.md'),'Stale skill record: '+name)
            for output in row['output_files']:require(t.sha(p/output['path'])==output['sha256'],'Stale recorded output: '+output['path'])
    return dict(passed=True,project_id=m['project_id'],revision=m['revision'],model_sha256=source,scope='2D drawings, schedules and budget',
        footprint_m2=result['envelope_area_m2'],net_area_m2=result['net_area_m2'],dxf_audit_errors=0,dxf_audit_fixes=0,
        room_rectangles_checked=rect_count,furniture_checked=len(furniture),cabinet_elevations_checked=len(elevations),
        svg_files=6,pdf_pages=len(pdf.pages),budget_rows=len(rows),linked_budget_rows=sum('quantity_rule' in b for b in m['budget']),
        budget={key:float(value) for key,value in budget.items()},latest_skill_records_checked=len(latest))

def main():
    parser=argparse.ArgumentParser();parser.add_argument('project',type=Path);parser.add_argument('--check-records',action='store_true');a=parser.parse_args()
    try:result=verify(a.project,a.check_records)
    except Exception as exc:result={'passed':False,'error':str(exc)}
    t.dump(a.project/'state/2d-artifact-check.json',result);print(json.dumps(result,ensure_ascii=False,indent=2))
    return 0 if result['passed'] else 1

if __name__=='__main__':raise SystemExit(main())
