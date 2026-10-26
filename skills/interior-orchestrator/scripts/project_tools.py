#!/usr/bin/env python3
"""Interior project data operations. Standard library, coordinates in millimeters."""
import argparse
import csv
import datetime as dt
import hashlib
import json
import math
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path

def load(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))

def dump(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')

def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def number(v):
    return isinstance(v, (int, float)) and not isinstance(v, bool) and math.isfinite(v)

def overlap(a, b):
    return max(0, min(a[0]+a[2],b[0]+b[2])-max(a[0],b[0])) * max(0,min(a[1]+a[3],b[1]+b[3])-max(a[1],b[1]))

def contains(a,b,tol=0.1):
    return b[0]>=a[0]-tol and b[1]>=a[1]-tol and b[0]+b[2]<=a[0]+a[2]+tol and b[1]+b[3]<=a[1]+a[3]+tol

def outline(m):
    """Inner boundary. Legacy rectangular envelope is still accepted."""
    if 'outline' in m:return m['outline']
    x,y,w,d=m['envelope']
    return [[x,y],[x+w,y],[x+w,y+d],[x,y+d]]

def footprint_area(m):
    pts=outline(m)
    return abs(sum(a[0]*b[1]-b[0]*a[1] for a,b in zip(pts,pts[1:]+pts[:1])))/2

def validate_outline(m):
    env=m['envelope']
    if len(env)!=4 or not all(number(v) for v in env) or min(env[2:])<=0:
        raise ValueError('envelope must be a positive bounding rectangle')
    pts=outline(m)
    if not isinstance(pts,list) or len(pts)<4 or any(not isinstance(p,list) or len(p)!=2 or not all(number(v) for v in p) for p in pts):
        raise ValueError('outline requires at least four finite XY vertices')
    if len({tuple(p) for p in pts})!=len(pts):raise ValueError('outline contains repeated vertices; omit closing vertex')
    edges=list(zip(pts,pts[1:]+pts[:1]))
    for a,b in edges:
        if (a[0]==b[0])==(a[1]==b[1]):raise ValueError('outline edges must be nonzero and axis aligned')
    for i,(a,b) in enumerate(edges):
        for j,(c,d) in enumerate(edges[i+1:],i+1):
            if j==i+1 or (i==0 and j==len(edges)-1):continue
            if (max(min(a[0],b[0]),min(c[0],d[0]))<=min(max(a[0],b[0]),max(c[0],d[0])) and
                max(min(a[1],b[1]),min(c[1],d[1]))<=min(max(a[1],b[1]),max(c[1],d[1]))):
                raise ValueError('outline self-intersects or touches itself')
    xs=[p[0] for p in pts];ys=[p[1] for p in pts]
    bounds=[min(xs),min(ys),max(xs)-min(xs),max(ys)-min(ys)]
    if any(abs(a-b)>.1 for a,b in zip(env,bounds)):raise ValueError('envelope must equal outline bounding box')
    if footprint_area(m)<=0:raise ValueError('outline has no area')

def inside_outline(m,x,y):
    pts=outline(m);inside=False
    for a,b in zip(pts,pts[1:]+pts[:1]):
        if min(a[0],b[0])<=x<=max(a[0],b[0]) and min(a[1],b[1])<=y<=max(a[1],b[1]) and (a[0]==b[0] or a[1]==b[1]):return True
        if (a[1]>y)!=(b[1]>y) and x<(b[0]-a[0])*(y-a[1])/(b[1]-a[1])+a[0]:inside=not inside
    return inside

def rect_in_footprint(m,r):
    if not contains(m['envelope'],r):return False
    if not r[2] and not r[3]:return inside_outline(m,r[0],r[1])
    # Corners alone miss rectangles spanning a concave notch.
    xs=sorted({r[0],r[0]+r[2]}|{p[0] for p in outline(m) if r[0]<p[0]<r[0]+r[2]})
    ys=sorted({r[1],r[1]+r[3]}|{p[1] for p in outline(m) if r[1]<p[1]<r[1]+r[3]})
    return all(inside_outline(m,(a+b)/2,(c+d)/2) for a,b in zip(xs,xs[1:]) for c,d in zip(ys,ys[1:]))

def cabinet_dimensions(f):
    w,d=f['rect'][2:]
    axis=f.get('front_axis','x' if w>=d else 'y')
    if axis not in ['x','y']:raise ValueError('Invalid front_axis: '+f['id'])
    return (w,d,f['height_mm']) if axis=='x' else (d,w,f['height_mm'])

def wall_rect(w):
    t=w['thickness']
    return [w['start'],w['at'],w['end']-w['start'],t] if w['axis']=='x' else [w['at'],w['start'],t,w['end']-w['start']]

def clearance(m,c):
    objects={x['id']:x for x in m['furniture']}
    a,b=objects[c['from']]['rect'],objects[c['to']]['rect']
    if c['axis']=='x':
        if min(a[1]+a[3],b[1]+b[3])<=max(a[1],b[1]):
            raise ValueError('Clearance objects have no perpendicular overlap: '+c['id'])
        return max(a[0],b[0])-min(a[0]+a[2],b[0]+b[2])
    if min(a[0]+a[2],b[0]+b[2])<=max(a[0],b[0]):
        raise ValueError('Clearance objects have no perpendicular overlap: '+c['id'])
    return max(a[1],b[1])-min(a[1]+a[3],b[1]+b[3])

def quantity_for(m,item):
    rule=item.get('quantity_rule')
    if not rule:return item['quantity']
    kind=rule['kind']
    if kind=='floor':
        if not rule['materials'] or not set(rule['materials'])<={x['id'] for x in m['materials']}:raise ValueError('Unknown/empty floor material selection: '+item['id'])
        return sum(r['rect'][2]*r['rect'][3]/1e6 for r in m['rooms'] if r['floor'] in rule['materials'])
    if kind=='net_area':return sum(r['rect'][2]*r['rect'][3]/1e6 for r in m['rooms'])
    collection=rule.get('collection','furniture')
    if collection not in ['furniture','lights','equipment','points','openings']:raise ValueError('Unsupported quantity collection: '+collection)
    objects={x['id']:x for x in m[collection]}
    if 'ids' in rule:
        if not rule['ids'] or len(set(rule['ids']))!=len(rule['ids']):raise ValueError('Empty/duplicate quantity IDs: '+item['id'])
        selected=[objects[id] for id in rule['ids']]
    else:
        if kind!='count':raise ValueError('Length/projection rules require explicit IDs')
        selected=list(objects.values())
    if kind=='length':return sum(cabinet_dimensions(x)[0]/1000 for x in selected)
    if kind=='projection':return sum(cabinet_dimensions(x)[0]*x['height_mm']/1e6 for x in selected)
    if kind=='count':return len(selected)
    raise ValueError('Unknown quantity rule: '+kind)

def budget_rows(m):
    rows=[]
    for item in m['budget']:
        raw_q,w,r=quantity_for(m,item),item.get('waste',0),item['rate']
        if not all(number(v) and v>=0 for v in [raw_q,w,r]):
            raise ValueError('Invalid budget input: '+item['id'])
        q=float(Decimal(str(raw_q)).quantize(Decimal('0.0001'),rounding=ROUND_HALF_UP))
        purchase=(Decimal(str(q))*(Decimal(1)+Decimal(str(w)))).quantize(Decimal('0.0001'),rounding=ROUND_HALF_UP)
        amount=(purchase*Decimal(str(r))).quantize(Decimal('.01'),rounding=ROUND_HALF_UP)
        rows.append({**item,'quantity':q,'purchase_quantity':float(purchase),'amount':float(amount)})
    return rows

def totals(m):
    rows=budget_rows(m)
    rate=m['reserve_rate'];budget=m['budget_cny']
    if not all(number(v) and v>=0 for v in [rate,budget]):
        raise ValueError('Invalid project budget or reserve rate')
    base=sum((Decimal(str(x['amount'])) for x in rows),Decimal(0))
    reserve=(base*Decimal(str(rate))).quantize(Decimal('.01'),rounding=ROUND_HALF_UP)
    total=base+reserve
    remaining=(Decimal(str(budget))-total).quantize(Decimal('.01'),rounding=ROUND_HALF_UP)
    return {'base':float(base),'reserve':float(reserve),'total':float(total),
            'budget':budget,'remaining':float(remaining)}

def check(m):
    issues=[]
    def issue(code,obj,message,**extra):
        issues.append({'code':code,'object':obj,'message':message,**extra})
    required=['project_id','revision','units','envelope','rooms','walls','openings','materials','furniture','lights','equipment','points','budget','clearances','clear_zones','budget_cny','reserve_rate']
    for key in required:
        if key not in m: issue('SCHEMA',key,'Missing required field')
    if issues: return {'passed':False,'issues':issues}
    if m['units']!='mm': issue('UNITS','project','Expected millimeters')
    try:validate_outline(m)
    except (TypeError,ValueError,KeyError) as exc:
        issue('GEOMETRY','outline',str(exc));return {'passed':False,'issues':issues}
    collections=['rooms','walls','openings','materials','furniture','lights','equipment','points','budget','fixtures','control_groups']
    ids=[]
    for key in collections:
        for x in m.get(key,[]):
            if not isinstance(x.get('id'),str): issue('SCHEMA',key,'Missing string id')
            ids.append(x.get('id'))
    for x in set(ids):
        if ids.count(x)>1: issue('DUPLICATE',x,'Identifier is repeated')
    rooms={r['id']:r for r in m['rooms']}
    materials={x['id']:x for x in m['materials']}
    envelope=m['envelope']
    for key in ['rooms','furniture']:
        for x in m[key]:
            r=x.get('rect',[])
            if len(r)!=4 or not all(number(v) for v in r) or r[2]<=0 or r[3]<=0:
                issue('GEOMETRY',x['id'],'Invalid rectangle'); continue
            if not rect_in_footprint(m,r): issue('OUTSIDE',x['id'],'Outside project footprint')
    if any(i['code']=='GEOMETRY' for i in issues): return {'passed':False,'issues':issues}
    for i,a in enumerate(m['rooms']):
        for b in m['rooms'][i+1:]:
            if overlap(a['rect'],b['rect'])>1: issue('ROOM_OVERLAP',a['id'],b['id'])
        if a.get('floor') not in materials: issue('MATERIAL',a['id'],'Unknown floor material')
    for f in m['furniture']:
        if f.get('room') not in rooms: issue('ROOM_REF',f['id'],'Unknown room')
        elif not contains(rooms[f['room']]['rect'],f['rect']): issue('ROOM_BOUNDARY',f['id'],'Outside assigned room')
        if f.get('material') not in materials: issue('MATERIAL',f['id'],'Unknown material')
        if not number(f.get('height_mm')) or f['height_mm']<=0:
            issue('GEOMETRY',f['id'],'Invalid furniture height');continue
        if f.get('front_axis','x') not in ['x','y']:
            issue('GEOMETRY',f['id'],'Invalid front_axis');continue
        if f.get('kind')=='joinery':
            width,depth,height=cabinet_dimensions(f)
            p=f.get('joinery',{})
            panel=p.get('panel_mm',18);back=p.get('back_mm',9);toe=p.get('plinth_mm',100);scribe=p.get('scribe_mm',20);bays=p.get('bays',max(1,math.ceil(width/800)))
            if (not all(number(v) and v>=0 for v in [panel,back,toe,scribe]) or not isinstance(bays,int) or isinstance(bays,bool) or bays<1 or width<=2*scribe+(bays+1)*panel or height<=toe+2*panel or depth<=back+panel):
                issue('JOINERY',f['id'],'Cabinet parameters leave no positive internal space')
    cabinets={f['id'] for f in m['furniture'] if f['kind']=='joinery'}
    selected=m.get('drawing',{}).get('joinery_ids',[])
    if len(selected)!=len(set(selected)) or not set(selected)<=cabinets:issue('DRAWING_REF','joinery_ids','Unknown or repeated cabinet selection')
    for fixture in m.get('fixtures',[])+([m['shower']] if m.get('shower') else []):
        rect=fixture.get('rect',[]);id=fixture.get('id','SHOWER')
        if len(rect)!=4 or not all(number(v) for v in rect) or min(rect[2:])<=0:issue('GEOMETRY',id,'Invalid fixture rectangle')
        elif not rect_in_footprint(m,rect):issue('OUTSIDE',id,'Fixture outside footprint')
        elif fixture.get('room') and (fixture['room'] not in rooms or not contains(rooms[fixture['room']]['rect'],rect)):issue('ROOM_REF',id,'Fixture room missing or boundary differs')
    solids=[f for f in m['furniture'] if f.get('kind') not in ['rug','decor','clearance']]
    for i,a in enumerate(solids):
        for b in solids[i+1:]:
            if overlap(a['rect'],b['rect'])>1: issue('FURNITURE_COLLISION',a['id'],b['id'])
    for z in m['clear_zones']:
        for f in solids:
            if f['id'] not in z.get('ignore',[]) and overlap(z['rect'],f['rect'])>1:
                issue('CLEAR_ZONE',f['id'],'Blocks '+z['id'])
    for c in m['clearances']:
        try:
            actual=clearance(m,c)
            if actual<c['target_mm']: issue('CLEARANCE',c['id'],'Below project design target',actual_mm=actual,target_mm=c['target_mm'],basis_type='project_design_target')
        except (KeyError,ValueError) as exc: issue('CLEARANCE_INPUT',c['id'],str(exc))
    walls={w['id']:w for w in m['walls']}
    for w in m['walls']:
        if w.get('axis') not in ['x','y'] or not all(number(w.get(k)) for k in ['start','end','at','thickness','height']) or w['start']>=w['end'] or w['thickness']<=0:
            issue('WALL',w['id'],'Invalid wall');continue
        if w.get('internal'):
            if not rect_in_footprint(m,wall_rect(w)):issue('OUTSIDE',w['id'],'Partition outside footprint')
            for r in rooms.values():
                if overlap(wall_rect(w),r['rect'])>1: issue('ROOM_WALL',r['id'],'Overlaps '+w['id'])
    for o in m['openings']:
        w=walls.get(o.get('wall'))
        if not w: issue('WALL_REF',o['id'],'Unknown wall');continue
        if not all(number(o.get(k)) for k in ['start','width','height']) or not number(o.get('sill',0)) or o['width']<=0 or o['height']<=0 or o.get('sill',0)<0:
            issue('OPENING',o['id'],'Invalid opening dimensions');continue
        if o['start']<w['start'] or o['start']+o['width']>w['end'] or o['height']+o.get('sill',0)>w['height']:
            issue('OPENING',o['id'],'Opening exceeds wall')
    for key in ['lights','equipment','points']:
        for x in m[key]:
            if x.get('room') not in rooms: issue('ROOM_REF',x['id'],'Unknown room')
            elif 'xy' in x:
                pos=x['xy']
                if len(pos)!=2 or not all(number(v) for v in pos):issue('POSITION',x['id'],'Invalid point coordinate')
                elif not contains(rooms[x['room']]['rect'],[*pos,0,0]):issue('POSITION',x['id'],'Outside assigned room')
    objects={f['id'] for f in m['furniture']}
    equipment={e['id'] for e in m['equipment']}
    for e in m['equipment']:
        if e.get('object') and e['object'] not in objects:issue('OBJECT_REF',e['id'],'Unknown equipment geometry')
    fixtures={f['id'] for f in m.get('fixtures',[])}
    if m.get('shower'):fixtures.add(m['shower'].get('id','SHOWER'))
    for p in m['points']:
        if p.get('link') not in objects|equipment|fixtures:issue('OBJECT_REF',p['id'],'Unknown linked object')
    groups={x['id'] for x in m.get('control_groups',[])}
    for l in m['lights']:
        if l.get('group') not in groups: issue('LIGHT_GROUP',l['id'],'Unknown control group')
        if not all(number(l.get(k)) and l[k]>=0 for k in ['power_w','lumens']): issue('LIGHT_DATA',l['id'],'Missing lighting data')
    for p in m['points']:
        if p.get('access_required'):
            for f in solids:
                x,y=p['xy'];fx,fy,fw,fd=f['rect']
                if fx<x<fx+fw and fy<y<fy+fd:
                    issue('POINT_ACCESS',p['id'],'Service point behind '+f['id'])
    try:
        amount=totals(m)
        if amount['remaining']<0:issue('BUDGET','project','Budget exceeded',total=amount['total'])
    except (KeyError,ValueError) as exc:
        amount={};issue('BUDGET_INPUT','project',str(exc))
    # Cell decomposition checks exact cover by net room zones and internal partitions.
    rects=[r['rect'] for r in rooms.values()]+[wall_rect(w) for w in m['walls'] if w.get('internal')]
    xs=sorted(set([p[0] for p in outline(m)]+[v for r in rects for v in [r[0],r[0]+r[2]]]))
    ys=sorted(set([p[1] for p in outline(m)]+[v for r in rects for v in [r[1],r[1]+r[3]]]))
    gap=0
    for x1,x2 in zip(xs,xs[1:]):
        for y1,y2 in zip(ys,ys[1:]):
            mid=[(x1+x2)/2,(y1+y2)/2,0,0]
            if inside_outline(m,*mid[:2]) and not any(contains(r,mid) for r in rects):gap+=(x2-x1)*(y2-y1)
    if gap>1:issue('AREA_GAP','project','Net zones plus partitions do not cover envelope',gap_m2=gap/1e6)
    return {'project_id':m['project_id'],'revision':m['revision'],'passed':not issues,'issues':issues,
        'scope':['simple orthogonal footprint','rectangular room boundaries','furniture collision','design clearances','ID references','opening limits','control groups','service access','budget arithmetic','area cover'],
        'not_checked':['structural safety','electrical protection','pipe sizing and gradients','statutory compliance','site conditions','client approval'],
        'envelope_area_m2':footprint_area(m)/1e6,'bounding_box_area_m2':envelope[2]*envelope[3]/1e6,
        'net_area_m2':round(sum(r['rect'][2]*r['rect'][3]/1e6 for r in rooms.values()),4),'budget':amount}

def schedules(m,out):
    out=Path(out);out.mkdir(parents=True,exist_ok=True)
    tables={
      'rooms':[{**{k:r[k] for k in ['id','name','floor']},'width_mm':r['rect'][2],'depth_mm':r['rect'][3],'area_m2':round(r['rect'][2]*r['rect'][3]/1e6,4)} for r in m['rooms']],
      'materials':m['materials'],'furniture':m['furniture'],'lights':m['lights'],'equipment':m['equipment'],'points':m['points'],'budget':budget_rows(m),
      'joinery':[{**f,'front_width_mm':cabinet_dimensions(f)[0],'depth_mm':cabinet_dimensions(f)[1],'projection_m2':round(cabinet_dimensions(f)[0]*f['height_mm']/1e6,4)} for f in m['furniture'] if f.get('kind')=='joinery']}
    for name,rows in tables.items():
        keys=list(dict.fromkeys(k for r in rows for k in r))
        with (out/(name+'.csv')).open('w',newline='',encoding='utf-8-sig') as f:
            writer=csv.DictWriter(f,fieldnames=keys);writer.writeheader()
            writer.writerows({k:json.dumps(v,ensure_ascii=False) if isinstance(v,(dict,list)) else v for k,v in r.items()} for r in rows)
    dump(out/'budget-summary.json',totals(m))
    dump(out/'budget-inputs.json',budget_rows(m))

def record(project,skill,outputs):
    project=Path(project).resolve();skill=Path(skill).resolve()
    items=[]
    for value in outputs:
        path=(project/value).resolve()
        if not path.is_relative_to(project) or not path.is_file():raise ValueError('Output must be a file within project: '+value)
        items.append({'path':str(path.relative_to(project)),'sha256':sha(path)})
    log=project/'state/execution-log.json';rows=load(log) if log.exists() else []
    rows.append({'skill':skill.name,'skill_sha256':sha(skill/'SKILL.md'),'input_sha256':sha(project/'model/project.json'),
        'output_files':items,'executed_at':dt.datetime.now(dt.timezone(dt.timedelta(hours=8))).isoformat(),
        'result':'design_deliverables_created','site_work_completed':False})
    dump(log,rows)

def main():
    p=argparse.ArgumentParser();s=p.add_subparsers(dest='command',required=True)
    q=s.add_parser('check');q.add_argument('model');q.add_argument('--out',required=True)
    q=s.add_parser('schedules');q.add_argument('model');q.add_argument('--out',required=True)
    q=s.add_parser('record');q.add_argument('project');q.add_argument('--skill',required=True);q.add_argument('--outputs',nargs='+',required=True)
    q=s.add_parser('init');q.add_argument('project');q.add_argument('--name',required=True)
    a=p.parse_args()
    if a.command=='init':
        root=Path(a.project)
        if root.exists():raise SystemExit('Refusing to overwrite existing project')
        for d in ['model','state','drawings','schedules','visuals','documents']:(root/d).mkdir(parents=True,exist_ok=True)
        dump(root/'model/project.json',{'project_id':root.name,'title':a.name,'revision':'v0.1','units':'mm','input_kind':'unknown'})
        (root/'README.md').write_text('# '+a.name+'\n\n补充真实输入后，按共享项目契约建立模型。此骨架尚不构成可校核设计。\n')
    elif a.command=='check':
        try:r=check(load(a.model))
        except (ValueError,TypeError,KeyError) as exc:r={'passed':False,'issues':[{'code':'INPUT_ERROR','message':str(exc)}]}
        dump(a.out,r);print(json.dumps(r,ensure_ascii=False,indent=2));return 0 if r['passed'] else 1
    elif a.command=='schedules':schedules(load(a.model),a.out)
    else:record(a.project,a.skill,a.outputs)
    return 0

if __name__=='__main__':raise SystemExit(main())
