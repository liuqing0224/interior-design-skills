"""Same-source 2D drawing primitives for SVG, PDF and DXF."""
from pathlib import Path
import html
import math
from project_tools import cabinet_dimensions, outline

SHEETS=[('ID-01','家具与空间平面','furniture'),('ID-02','地材与铺装意向','finishes'),
 ('ID-03','灯位与控制分组','lighting'),('ID-04','设备与机电条件','mep'),
 ('ID-05','定位与开口尺寸','dimensions'),('ID-06','定制立面与剖面条件','joinery')]

class Scene:
    def __init__(self):self.items=[]
    def rect(self,x,y,w,h,fill='none',stroke='#33483F',sw=12,layer='FURNITURE',id=''):
        self.items.append(dict(kind='rect',x=x,y=y,w=w,h=h,fill=fill,stroke=stroke,sw=sw,layer=layer,id=id))
    def line(self,x1,y1,x2,y2,stroke='#33483F',sw=12,layer='LINE',dash=False):
        self.items.append(dict(kind='line',x1=x1,y1=y1,x2=x2,y2=y2,stroke=stroke,sw=sw,layer=layer,dash=dash))
    def circle(self,x,y,r,fill='none',stroke='#33483F',sw=12,layer='SYMBOL'):
        self.items.append(dict(kind='circle',x=x,y=y,r=r,fill=fill,stroke=stroke,sw=sw,layer=layer))
    def text(self,x,y,text,size=120,color='#273C32',anchor='middle',layer='TEXT'):
        self.items.append(dict(kind='text',x=x,y=y,text=str(text),size=size,color=color,anchor=anchor,layer=layer))
    def dimx(self,x1,x2,y,label=None):
        self.line(x1,y,x2,y,sw=7,layer='DIMENSION')
        for x in [x1,x2]:self.line(x,y-65,x,y+65,sw=7,layer='DIMENSION');self.line(x-35,y-35,x+35,y+35,sw=10,layer='DIMENSION')
        if label!='':self.text((x1+x2)/2,y+70,str(round(x2-x1)) if label is None else label,105,layer='DIMENSION')
    def dimy(self,y1,y2,x,label=None):
        self.line(x,y1,x,y2,sw=7,layer='DIMENSION')
        for y in [y1,y2]:self.line(x-65,y,x+65,y,sw=7,layer='DIMENSION')
        if label!='':self.text(x-50,(y1+y2)/2,str(round(y2-y1)) if label is None else label,105,anchor='end',layer='DIMENSION')

def wall_parts(w,openings):
    intervals=sorted([(o['start'],o['start']+o['width']) for o in openings if o['wall']==w['id']])
    cursor=w['start'];parts=[]
    for a,b in intervals:
        if a>cursor:parts.append((cursor,a))
        cursor=max(cursor,b)
    if cursor<w['end']:parts.append((cursor,w['end']))
    return parts

def plan(m,kind):
    if kind=='joinery':return joinery(m)
    s=Scene();mats={x['id']:x for x in m['materials']}
    for r in m['rooms']:
        x,y,w,d=r['rect'];fill=mats[r['floor']]['color'] if kind=='finishes' else '#F5F2EA'
        s.rect(x,y,w,d,fill,stroke='#DCD9D1',sw=5,layer='FLOOR',id=r['id'])
        if kind=='finishes':
            pattern=mats[r['floor']].get('pattern',{})
            px,py=pattern.get('spacing_mm',[0,0])
            if px>0:
                for n in range(1,math.ceil(w/px)):s.line(x+n*px,y,x+n*px,y+d,'#AA987A',3,layer='FINISH_JOINT')
            if py>0:
                for n in range(1,math.ceil(d/py)):s.line(x,y+n*py,x+w,y+n*py,'#A5A39A',3,layer='FINISH_JOINT')
    # Every opening is cut from the same wall object used by the 3D scene.
    walls={w['id']:w for w in m['walls']}
    for w in m['walls']:
        for a,b in wall_parts(w,m['openings']):
            if w['axis']=='x':s.rect(a,w['at'],b-a,w['thickness'],'#394B42','#394B42',5,'WALL')
            else:s.rect(w['at'],a,w['thickness'],b-a,'#394B42','#394B42',5,'WALL')
    for o in m['openings']:
        w=walls[o['wall']];a=o['start'];b=a+o['width'];t=w['thickness'];at=w['at'];color='#4D9296' if o['kind']=='window' else '#97754D'
        if o['kind']=='window':
            for z in [.15,.5,.85]:
                if w['axis']=='x':s.line(a,at+t*z,b,at+t*z,color,9,'WINDOW')
                else:s.line(at+t*z,a,at+t*z,b,color,9,'WINDOW')
        elif o['kind']=='sliding':
            if w['axis']=='x':s.rect(a,at+t*.45,o['width']*.55,20,'none',color,12,'DOOR');s.rect(a+o['width']*.45,at+t*.65,o['width']*.55,20,'none',color,12,'DOOR')
            else:s.rect(at+t*.45,a,20,o['width']*.55,'none',color,12,'DOOR');s.rect(at+t*.65,a+o['width']*.45,20,o['width']*.55,'none',color,12,'DOOR')
        elif w['axis']=='x':
            s.line(a,at+t,a,at+t+o['width'],color,12,'DOOR')
            pts=[(a+math.cos(k*math.pi/24)*o['width'],at+t+math.sin(k*math.pi/24)*o['width']) for k in range(13)]
            for p,q in zip(pts,pts[1:]):s.line(*p,*q,color,6,'DOOR',True)
        else:
            s.line(at,b,at-o['width'],b,color,12,'DOOR')
            pts=[(at-math.sin(k*math.pi/24)*o['width'],b-math.cos(k*math.pi/24)*o['width']) for k in range(13)]
            for p,q in zip(pts,pts[1:]):s.line(*p,*q,color,6,'DOOR',True)
        if kind=='dimensions':
            if w['axis']=='x':s.text((a+b)/2,at-150,o['id']+' '+str(o['width']),95)
            else:s.text(at-350,(a+b)/2,o['id']+' '+str(o['width']),95)
    if kind not in ['dimensions','finishes']:
        for f in sorted(m['furniture'],key=lambda x:x['kind']!='rug'):
            x,y,w,d=f['rect'];fill=mats[f['material']]['color'] if kind=='furniture' else '#ECE9E1'
            if f['kind']=='rug':fill='#DED7C6'
            s.rect(x,y,w,d,fill,'#6D756B',8,'FURNITURE',id=f['id'])
            if f['kind']=='joinery':
                front,depth,height=cabinet_dimensions(f);bays=f.get('joinery',{}).get('bays',max(1,math.ceil(front/800)))
                if f.get('front_axis','x' if w>=d else 'y')=='x':
                    for n in range(1,bays):s.line(x+front*n/bays,y,x+front*n/bays,y+d,'#8C7455',5)
                else:
                    for n in range(1,bays):s.line(x,y+front*n/bays,x+w,y+front*n/bays,'#8C7455',5)
            if kind=='furniture' and f['kind']!='rug':s.text(x+w/2,y+d/2,f['id'],95)
        for f in m.get('fixtures',[]):
            s.rect(*f['rect'],'none','#6F8180',12,'FIXTURE',id=f['id'])
    if m.get('shower'):
        sx,sy,sw,sd=m['shower']['rect']
        s.rect(sx,sy,sw,sd,'none','#5E9396',12,'FIXTURE')
        s.line(sx,sy,sx+sw,sy,'#5E9396',18,'GLASS')
        s.circle(sx+sw/2,sy+sd/2,min(sw,sd)*.07,stroke='#5E9396',layer='FIXTURE')
    if kind=='lighting':
        colors=['#987342','#517866','#777297','#9B5D57']
        for i,g in enumerate(m['control_groups']):
            ls=[l for l in m['lights'] if l['group']==g['id']]
            for a,b in zip(ls,ls[1:]):s.line(*a['xy'],*b['xy'],colors[i%4],9,'LIGHT_CONTROL',True)
        for l in m['lights']:
            x,y=l['xy'];s.circle(x,y,75,'#FAE8A9','#957135',12,'LIGHT')
            s.line(x-100,y,x+100,y,'#957135',7,'LIGHT');s.line(x,y-100,x,y+100,'#957135',7,'LIGHT')
            s.text(x+100,y+130,l['id']+'/'+l['group'],95,anchor='start',layer='LIGHT_LABEL')
    if kind=='mep':
        for e in m['equipment']:
            if 'xy' in e:x,y=e['xy']
            else:
                f=next(f for f in m['furniture'] if f['id']==e['object']);x,y,w,d=f['rect'];x+=w/2;y+=d/2
            s.rect(x-90,y-90,180,180,'#D5E4DC','#507F68',12,'EQUIPMENT')
            s.text(x+120,y+70,e['id'],100,anchor='start',layer='EQUIPMENT_LABEL')
        for p in m['points']:
            x,y=p['xy'];color='#437E95' if '水' in p['type'] or '排' in p['type'] else '#B7674E'
            s.circle(x,y,85,'#FFFDFC',color,15,'SERVICE_POINT')
            # Keep west-wall labels inside the room, clear of the dimension chain.
            room=next(r for r in m['rooms'] if r['id']==p['room'])
            left=x<room['rect'][0]+room['rect'][2]/2
            label_x=x+140 if left else x-140
            anchor='start' if left else 'end'
            s.line(x,y,label_x,y-130,color,6,'SERVICE_LABEL')
            s.text(label_x,y-180,p['id']+' z'+str(p['z_mm']),90,anchor=anchor,layer='SERVICE_LABEL')
    for r in m['rooms']:
        x,y,w,d=r['rect'];label_x,label_y=r.get('dimension_label_xy',[x+w/2,y+d/2]) if kind=='dimensions' else r.get('label_xy',[x+w/2,y+d-240])
        text=r['id']+' '+r['name']
        if kind=='finishes':text+=' '+r['floor']
        s.text(label_x,label_y,text,135)
    ex,ey,ew,ed=m['envelope']
    s.dimx(ex,ex+ew,ey+ed+750);s.dimy(ey,ey+ed,ex-750)
    # Segment chains include partition widths and are derived from actual zones.
    xs=sorted({ex,ex+ew}|{v for r in m['rooms'] for v in [r['rect'][0],r['rect'][0]+r['rect'][2]]})
    ys=sorted({ey,ey+ed}|{v for r in m['rooms'] for v in [r['rect'][1],r['rect'][1]+r['rect'][3]]})
    for a,b in zip(xs,xs[1:]):
        s.dimx(a,b,ey+ed+380,label='' if b-a<250 else None)
    for a,b in zip(ys,ys[1:]):
        s.dimy(a,b,ex-380,label='' if b-a<250 else None)
    if kind=='dimensions' and 'outline' in m:
        pts=outline(m)
        for a,b in zip(pts,pts[1:]+pts[:1]):s.line(*a,*b,'#B7674E',12,'FOOTPRINT',True)
    nx=ex+ew+500;ny=ey+ed
    s.line(nx,ny-850,nx,ny-150,sw=25,layer='NORTH');s.line(nx,ny-150,nx-120,ny-380,sw=20,layer='NORTH');s.line(nx,ny-150,nx+120,ny-380,sw=20,layer='NORTH');s.text(nx,ny+80,'N',180)
    return s

def selected_cabinets(m):
    objects={f['id']:f for f in m['furniture'] if f['kind']=='joinery'}
    ids=m.get('drawing',{}).get('joinery_ids')
    if ids is None:return sorted(objects.values(),key=lambda f:cabinet_dimensions(f)[0]*f['height_mm'],reverse=True)[:3]
    return [objects[id] for id in ids]

def joinery(m):
    """Parametric front elevation and section; no fabricated appliance cutouts."""
    s=Scene();selected=selected_cabinets(m)
    if not selected:
        s.text(0,0,'本版无选定柜体立剖',140,anchor='start');return s
    mats={x['id']:x for x in m['materials']}
    widths=[cabinet_dimensions(f)[0]+cabinet_dimensions(f)[1]+1600 for f in selected]
    pitch=max(widths);row_height=max(f['height_mm'] for f in selected)+1600
    columns=min(3,len(selected))
    for i,f in enumerate(selected):
        w,d,h=cabinet_dimensions(f);p=f.get('joinery',{})
        panel=p.get('panel_mm',18);back=p.get('back_mm',9);toe=p.get('plinth_mm',100);scribe=p.get('scribe_mm',20);bays=p.get('bays',max(1,math.ceil(w/800)))
        x=(i%columns)*pitch;y=-(i//columns)*row_height
        bay=(w-2*scribe-(bays+1)*panel)/bays
        s.text(x,y+h+480,f['id']+' '+f['name'],150,anchor='start')
        s.rect(x,y,w,h,mats[f['material']]['color'],'#48574B',15,'JOINERY_ELEVATION',id=f['id'])
        s.rect(x+scribe+panel,y+toe+panel,w-2*(scribe+panel),h-toe-2*panel,'#F0E8DB','#79664F',8,'JOINERY_INTERNAL')
        for n in range(1,bays):s.rect(x+scribe+panel+n*bay+(n-1)*panel,y+toe+panel,panel,h-toe-2*panel,'#A6865E','#79664F',6,'JOINERY_INTERNAL')
        s.dimx(x,x+w,y-250);s.dimy(y,y+h,x-250)
        sx=x+w+600
        s.rect(sx,y,d,h,mats[f['material']]['color'],'#48574B',15,'JOINERY_SECTION',id=f['id'])
        s.rect(sx+back,y+toe+panel,d-back-panel,h-toe-2*panel,'#F7F0E4','#79664F',8,'JOINERY_INTERNAL')
        s.dimx(sx,sx+d,y-250)
        s.text(x,y-560,f'外包 {w:g}×{d:g}×{h:g} mm；{bays}格 / 净宽 {bay:.1f}',110,anchor='start')
        s.text(x,y-760,f'板{panel:g} / 背{back:g} / 踢脚{toe:g} / 单侧收口{scribe:g} mm',105,anchor='start')
    s.text(0,-math.ceil(len(selected)/columns)*row_height+300,'立剖为模型参数条件，柜内功能与五金另行选定。完整柜体见 joinery.csv。',115,anchor='start')
    return s

def scene_bounds(s,pad=120):
    xs=[];ys=[]
    for p in s.items:
        if p['kind']=='rect':xx=[p['x'],p['x']+p['w']];yy=[p['y'],p['y']+p['h']]
        elif p['kind']=='line':xx=[p['x1'],p['x2']];yy=[p['y1'],p['y2']]
        elif p['kind']=='circle':xx=[p['x']-p['r'],p['x']+p['r']];yy=[p['y']-p['r'],p['y']+p['r']]
        else:
            width=sum(.6 if ord(c)<128 else 1 for c in p['text'])*p['size'];left=p['x']-({'start':0,'middle':width/2,'end':width}[p['anchor']])
            xx=[left,left+width];yy=[p['y']-p['size']*.25,p['y']+p['size']]
        xs.extend(xx);ys.extend(yy)
    return (min(xs)-pad,min(ys)-pad,max(xs)+pad,max(ys)+pad) if xs else (0,0,1,1)

def sheet_layout(m):
    scenes=[plan(m,kind) for _,_,kind in SHEETS]
    bounds=[scene_bounds(s) for s in scenes]
    pitch_x=max(b[2]-b[0] for b in bounds)+1800;pitch_y=max(b[3]-b[1] for b in bounds)+1800
    return [(s,(i%3)*pitch_x,-(i//3)*pitch_y) for i,s in enumerate(scenes)]

def svg(s,path,title):
    xmin,ymin,xmax,ymax=scene_bounds(s);v=[]
    for p in s.items:
        if p['kind']=='rect':v.append(f'<rect data-object="{html.escape(p["id"],quote=True)}" x="{p["x"]}" y="{-p["y"]-p["h"]}" width="{p["w"]}" height="{p["h"]}" fill="{p["fill"]}" stroke="{p["stroke"]}" stroke-width="{p["sw"]}"/>')
        elif p['kind']=='line':v.append(f'<line x1="{p["x1"]}" y1="{-p["y1"]}" x2="{p["x2"]}" y2="{-p["y2"]}" stroke="{p["stroke"]}" stroke-width="{p["sw"]}"'+(' stroke-dasharray="70 45"' if p.get('dash') else '')+'/>')
        elif p['kind']=='circle':v.append(f'<circle cx="{p["x"]}" cy="{-p["y"]}" r="{p["r"]}" fill="{p["fill"]}" stroke="{p["stroke"]}" stroke-width="{p["sw"]}"/>')
        else:v.append(f'<text x="{p["x"]}" y="{-p["y"]}" font-family="PingFang SC,Microsoft YaHei,sans-serif" font-size="{p["size"]}" text-anchor="{p["anchor"]}" fill="{p["color"]}">{html.escape(p["text"])}</text>')
    Path(path).write_text(f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="{xmin} {-ymax} {xmax-xmin} {ymax-ymin}"><title>{html.escape(title)}</title><rect x="{xmin}" y="{-ymax}" width="{xmax-xmin}" height="{ymax-ymin}" fill="#FFFEFA"/>'+''.join(v)+'</svg>')

def dxf_document(m):
    import ezdxf
    from ezdxf.enums import TextEntityAlignment
    doc=ezdxf.new('R2018');doc.units=ezdxf.units.MM
    doc.header['$INSUNITS']=4
    doc.appids.new('INTERIOR')
    doc.styles.new('CJK',dxfattribs={'font':'Arial Unicode.ttf'})
    ms=doc.modelspace()
    for (code,title,kind),(s,ox,oy) in zip(SHEETS,sheet_layout(m)):
        for p in s.items:
            layer=code+'_'+p['layer']
            if layer not in doc.layers:
                color=1 if 'SERVICE' in layer else 3 if 'LIGHT' in layer else 7
                doc.layers.new(layer,dxfattribs={'color':color})
            a={'layer':layer}
            if p['kind']=='rect':
                x,y,w,h=p['x']+ox,p['y']+oy,p['w'],p['h'];entity=ms.add_lwpolyline([(x,y),(x+w,y),(x+w,y+h),(x,y+h)],close=True,dxfattribs=a)
                if p['id']:entity.set_xdata('INTERIOR',[(1000,p['id'])])
            elif p['kind']=='line':ms.add_line((p['x1']+ox,p['y1']+oy),(p['x2']+ox,p['y2']+oy),dxfattribs=a)
            elif p['kind']=='circle':ms.add_circle((p['x']+ox,p['y']+oy),p['r'],dxfattribs=a)
            else:
                align={'middle':TextEntityAlignment.BOTTOM_CENTER,'start':TextEntityAlignment.BOTTOM_LEFT,'end':TextEntityAlignment.BOTTOM_RIGHT}[p['anchor']]
                ms.add_text(p['text'],dxfattribs={**a,'height':p['size'],'style':'CJK'}).set_placement((p['x']+ox,p['y']+oy),align=align)
        bound=scene_bounds(s)
        ms.add_text(code+' '+title+' / '+m['revision']+' / mm / '+m['project_id'],dxfattribs={'height':180,'style':'CJK'}).set_placement((ox+bound[0],oy+bound[3]+250))
    return doc

def pdf_scene(canvas,s,x,y,scale,font='STSong-Light'):
    from reportlab.lib.colors import HexColor
    canvas.saveState();canvas.translate(x,y);canvas.scale(scale,scale)
    for p in s.items:
        if p['kind']=='text':
            canvas.setFillColor(HexColor(p['color']));canvas.setFont(font,p['size'])
            method={'middle':canvas.drawCentredString,'start':canvas.drawString,'end':canvas.drawRightString}[p['anchor']]
            method(p['x'],p['y'],p['text']);continue
        canvas.setStrokeColor(HexColor(p['stroke']));canvas.setLineWidth(p['sw'])
        if p.get('fill','none')!='none':canvas.setFillColor(HexColor(p['fill']))
        canvas.setDash([70,45] if p.get('dash') else [])
        if p['kind']=='rect':canvas.rect(p['x'],p['y'],p['w'],p['h'],fill=int(p['fill']!='none'),stroke=1)
        elif p['kind']=='circle':canvas.circle(p['x'],p['y'],p['r'],fill=int(p['fill']!='none'),stroke=1)
        else:canvas.line(p['x1'],p['y1'],p['x2'],p['y2'])
    canvas.restoreState()
