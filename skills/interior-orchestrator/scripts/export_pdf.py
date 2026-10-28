#!/usr/bin/env python3
"""Generic A3 2D set. No dependency on a project's render names or fixed dimensions."""
import argparse
import datetime as dt
import math
import os
from pathlib import Path
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.pagesizes import A3,landscape
from reportlab.lib.colors import HexColor
from drawing_lib import SHEETS,plan,pdf_scene,scene_bounds,joinery
from project_tools import load,check,totals,budget_rows,cabinet_dimensions,dump,sha

CJK_CANDIDATES=['/System/Library/Fonts/Supplemental/Arial Unicode.ttf','/System/Library/Fonts/PingFang.ttc',
    '/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc','/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc',
    '/usr/share/fonts/truetype/arphic/uming.ttc','C:/Windows/Fonts/msyh.ttc','C:/Windows/Fonts/simhei.ttf',
    'C:/Windows/Fonts/simsun.ttc']

def register_font():
    """Prefer INTERIOR_PDF_FONT, then the first usable embeddable CJK font."""
    tried=[];failure=''
    for candidate in [os.getenv('INTERIOR_PDF_FONT','')]+CJK_CANDIDATES:
        if not candidate:continue
        tried.append(candidate)
        if not Path(candidate).is_file():continue
        try:
            pdfmetrics.registerFont(TTFont('InteriorCJK',candidate,subfontIndex=0))
            return 'InteriorCJK'
        except Exception as exc:
            failure=str(exc)
    raise SystemExit('Set INTERIOR_PDF_FONT to an embeddable Chinese TrueType font. Tried: '+', '.join(tried)+((' / last error: '+failure) if failure else ''))

def main():
    parser=argparse.ArgumentParser();parser.add_argument('project',type=Path);parser.add_argument('--previous',type=Path);a=parser.parse_args()
    p=a.project.resolve();m=load(p/'model/project.json');result=check(m)
    if not result['passed']:raise SystemExit('Model check failed')
    old=load(a.previous/'model/project.json') if a.previous else None
    F=register_font()
    width,height=landscape(A3);out=p/'documents'/(m['title']+'_图集.pdf');out.parent.mkdir(exist_ok=True)
    c=canvas.Canvas(str(out),pagesize=(width,height));c.setTitle(m['title']+' / '+m['revision']+' / 室内图集')
    page=0;pages=8 if old else 7;scales=[]
    def text(x,y,value,size=11,color='#35483D'):
        c.setFont(F,size);c.setFillColor(HexColor(color));c.drawString(x,y,str(value))
    def wrap(x,y,value,maxwidth,size=11):
        line=''
        for char in str(value):
            if pdfmetrics.stringWidth(line+char,F,size)>maxwidth:
                text(x,y,line,size);y-=size*1.6;line=''
            line+=char
        if line:text(x,y,line,size)
        return y-size*1.6
    def begin(code,title):
        nonlocal page
        page+=1;c.setFillColor(HexColor('#FAF9F4'));c.rect(0,0,width,height,fill=1,stroke=0)
        text(46,height-40,m['title']+' / '+code,10,'#96836D');text(46,height-79,title,24)
        c.setStrokeColor(HexColor('#D5D9CF'));c.line(46,55,width-46,55)
        text(46,33,f'{m["project_id"]} / {m["revision"]} / {dt.date.today().isoformat()} / {m["input_kind"]}',9,'#7E857B')
        text(width-92,33,f'{page:02d} / {pages:02d}',9)
    def fit(scene,x,y,w,h):
        left,bottom,right,top=scene_bounds(scene)
        raw=min(w/(right-left),h/(top-bottom))
        denominator=max(1,math.ceil((72/25.4/raw)/5)*5)
        scale=72/25.4/denominator
        xx=x+(w-(right-left)*scale)/2-left*scale
        yy=y+(h-(top-bottom)*scale)/2-bottom*scale
        pdf_scene(c,scene,xx,yy,scale,font=F)
        return denominator
    def table(x,y,headers,rows,colwidths,rowh=29):
        c.setFillColor(HexColor('#425C4D'));c.rect(x,y-rowh,sum(colwidths),rowh,fill=1,stroke=0)
        for i,row in enumerate([headers]+rows):
            xx=x
            for value,w in zip(row,colwidths):
                text(xx+7,y-i*rowh-20,value,10,'#FFFFFF' if i==0 else '#35483D');xx+=w
        return y-(len(rows)+1)*rowh
    b=totals(m)
    begin('PROJECT','模型、空间与预算')
    fit(plan(m,'furniture'),46,110,680,600)
    text(785,690,f'轮廓面积 {result["envelope_area_m2"]:.2f} ㎡',19)
    text(785,653,f'净分区 {result["net_area_m2"]:.4f} ㎡',13)
    text(785,614,f'总估算 {b["total"]:,.2f} 元',18)
    text(785,583,f'预备费率 {m["reserve_rate"]:.0%}；预算余量 {b["remaining"]:,.2f} 元',11)
    y=table(785,547,['编号','空间','㎡'],[[r['id'],r['name'],f'{r["rect"][2]*r["rect"][3]/1e6:.2f}'] for r in m['rooms']],[88,120,65])
    linked=sum('quantity_rule' in row for row in m['budget'])
    y=wrap(785,y-36,f'预算 {len(m["budget"])} 行，其中 {linked} 行由模型规则计量。单价来源与计量口径见预算明细。',330)
    note='本案例为跨户型设计设定。' if m.get('location_status')=='synthetic_transfer_test' else f'输入类型：{m["input_kind"]}。'
    wrap(785,y-14,note+'图集由当前模型生成，尺寸单位mm；CAD模型空间1:1。',330)
    c.showPage()
    if old:
        begin('CHANGE','柜体修改与费用联动')
        oldmap={f['id']:f for f in old['furniture']};changes=[]
        for f in m['furniture']:
            if f['id'] in oldmap and (f['rect']!=oldmap[f['id']]['rect'] or f['height_mm']!=oldmap[f['id']]['height_mm']):changes.append(f)
        for i,f in enumerate(changes[:2]):
            oldm={**old,'drawing':{'joinery_ids':[f['id']]}};newm={**m,'drawing':{'joinery_ids':[f['id']]}}
            text(70,697-i*250,'修改前 '+old['revision'],14);text(650,697-i*250,'修改后 '+m['revision'],14)
            fit(joinery(oldm),60,410-i*250,480,250);fit(joinery(newm),640,410-i*250,480,250)
        before=totals(old)
        table(70,350,['费用','修改前（元）','修改后（元）','差额（元）'],[[label,f'{before[key]:,.2f}',f'{b[key]:,.2f}',f'{b[key]-before[key]:+,.2f}'] for key,label in [('base','基础费用'),('reserve','预备费'),('total','含预备费总额')]],[190,220,220,220],35)
        wrap(70,158,'修改对象按编号保留：正面宽度、深度和高度分别进入平面、立剖、joinery.csv与投影面积计价。历史版本单独保存。',1000,12)
        c.showPage()
    for code,title,kind in SHEETS:
        begin(code,title)
        denominator=fit(plan(m,kind),50,115,820,600);scales.append({'code':code,'scale_denominator':denominator})
        text(917,690,'图面与模型',15)
        lines=[f'模型版本 {m["revision"]}',f'A3原幅比例 1:{denominator}','坐标X向东、Y向北，Z向上。']
        if kind=='finishes':lines += [f'{mat["id"]} {mat["name"]}' for mat in m['materials'] if any(r['floor']==mat['id'] for r in m['rooms'])]+['铺装间距来自材料pattern参数。']
        elif kind=='lighting':lines += [f'{len(m["lights"])}盏/条灯，{len(m.get("control_groups",[]))}个分组。','虚线表达分组关系。']
        elif kind=='mep':lines += [f'{len(m["equipment"])}项设备、{len(m["points"])}处条件点位。','点位z值自完成地面起。']
        elif kind=='dimensions':lines += [f'包围框 {m["envelope"][2]:g}×{m["envelope"][3]:g} mm',f'实际轮廓面积 {result["envelope_area_m2"]:.2f}㎡','红色虚线表达正交轮廓。']
        elif kind=='joinery':lines += ['立面、剖面由柜体参数生成。','选定柜体见图，全部柜体见清单。','柜内功能、设备开孔和五金另行深化。']
        else:lines += [f'{r["id"]} {r["name"]}' for r in m['rooms']]
        y=645
        for line in lines:y=wrap(917,y,line,220,11)-14
        c.showPage()
    c.save()
    dump(p/'documents/pdf-manifest.json',{'file':out.name,'pages':page,'model_sha256':sha(p/'model/project.json'),'revision':m['revision'],'scales':scales,'generator_sha256':sha(Path(__file__))})
    print(out)

if __name__=='__main__':main()
