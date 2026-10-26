#!/usr/bin/env python3
"""Create a twelve-page A3 design presentation and detail set from project assets."""
from pathlib import Path
import importlib.util
import json
import math
import os
import sys
import types
import zipfile

from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.pagesizes import A3,landscape
from reportlab.lib.colors import HexColor
from reportlab.lib.utils import ImageReader

ROOT=Path(__file__).resolve().parents[1]
P=Path(sys.argv[1]).resolve() if len(sys.argv)>1 else ROOT/'projects/DEMO-APT-096'
m=json.loads((P/'model/project.json').read_text())
if m['project_id']!='DEMO-APT-096':raise SystemExit('This is the original DEMO-APT-096 presentation. Use export_pdf.py for other projects.')
for mod,file in [('draw','drawing_lib.py'),('tools','project_tools.py')]:
    if mod=='draw':
        with zipfile.ZipFile(ROOT/'releases/baseline-v1-tools.zip') as archive:source=archive.read('skills/interior-orchestrator/scripts/drawing_lib.py')
        module=types.ModuleType('demo096_drawing');exec(compile(source,'demo096_drawing_v1','exec'),module.__dict__);globals()[mod]=module;continue
    spec=importlib.util.spec_from_file_location(mod,ROOT/'skills/interior-orchestrator/scripts'/file)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);globals()[mod]=module
font_candidates=[os.environ.get('INTERIOR_PDF_FONT',''),
    '/System/Library/Fonts/Supplemental/Arial Unicode.ttf',
    '/usr/share/fonts/truetype/arphic/uming.ttc']
font_path=next((Path(p) for p in font_candidates if p and Path(p).is_file()),None)
if font_path is None:
    raise SystemExit('Set INTERIOR_PDF_FONT to a Chinese TrueType font with embedding permission.')
FONT='InteriorCJK'
pdfmetrics.registerFont(TTFont(FONT,str(font_path)))
W,H=landscape(A3)
OUT=P/'documents/栖木之家_方案与深化图集.pdf'
OUT.parent.mkdir(exist_ok=True)
c=canvas.Canvas(str(OUT),pagesize=(W,H));c.setTitle('栖木之家 · 96㎡住宅方案与深化图集');c.setAuthor('Interior Skills Design Demonstration')
page=0

def text(x,y,value,size=12,color='#334A3D'):
    c.setFont(FONT,size);c.setFillColor(HexColor(color));c.drawString(x,y,str(value))
def wrap(x,y,value,width,size=12,leading=None,color='#4E5B50'):
    leading=leading or size*1.65;line=''
    for ch in value:
        if ch!='\n' and ch in '，。；：！？、）】》' and line:
            line+=ch
            continue
        if ch=='\n' or pdfmetrics.stringWidth(line+ch,FONT,size)>width:
            text(x,y,line,size,color);y-=leading;line='' if ch=='\n' else ch
        else:line+=ch
    if line:text(x,y,line,size,color);y-=leading
    return y
def box(x,y,w,h,fill,stroke=None):
    c.setFillColor(HexColor(fill));c.setStrokeColor(HexColor(stroke or fill));c.rect(x,y,w,h,stroke=bool(stroke),fill=1)
def image(name,x,y,w,h):
    path=P/'visuals'/name;c.drawImage(ImageReader(str(path)),x,y,w,h,preserveAspectRatio=True,anchor='c',mask='auto')
def begin(kicker,title,sub=''):
    global page
    page+=1;box(0,0,W,H,'#FAF9F4')
    text(52,H-43,kicker,10,'#9A876C');text(52,H-83,title,27)
    if sub:text(52,H-108,sub,11,'#7A8175')
    c.setStrokeColor(HexColor('#D6D9CF'));c.setLineWidth(.7);c.line(52,55,W-52,55)
    text(52,34,f'栖木之家 / {m["revision"]} / 2026-10-26 / 住宅示范设计',9,'#848A7E')
    c.setFont('Helvetica',9);c.drawRightString(W-52,34,f'{page:02d} / 12')
def end():c.showPage()
def table(x,y,width,headers,rows,ratios=None,size=11,rowh=29):
    ratios=ratios or [1]*len(headers);widths=[width*r/sum(ratios) for r in ratios]
    box(x,y-rowh,width,rowh,'#435D4E');xx=x
    for title,w in zip(headers,widths):text(xx+9,y-rowh+9,title,size,'#FFFFFF');xx+=w
    yy=y-rowh
    for i,row in enumerate(rows):
        if i%2==0:box(x,yy-rowh,width,rowh,'#EEEFE6')
        xx=x
        for value,w in zip(row,widths):
            val=str(value)
            if pdfmetrics.stringWidth(val,FONT,size)>w-16:
                # Wrap to at most two lines only when a row has enough height.
                wrap(xx+8,yy-12,val,w-16,size*.9,size*1.05)
            else:text(xx+9,yy-rowh+10,val,size)
            xx+=w
        yy-=rowh
    return yy

begin('INTERIOR DESIGN / 01','栖木之家','15个Skills串联的住宅设计示范')
text(62,615,'浅木 · 柔光 · 留白',30)
wrap(62,570,'两卧加书房，三口之家的日常与工作。用连续地材、集中收纳和独立任务照明组织约96㎡空间。',280,15,25)
for y,a,b in [(395,'96.00㎡','套内轮廓'),(315,'92.53㎡','净分区面积'),(235,'28.79万元','含10%预备费的示范估算')]:text(62,y,a,26);text(64,y-25,b,12,'#87816F')
image('01-axon.png',355,155,790,540)
text(62,105,'DEMO-APT-096 / 设计文件与现场配合准备 / 采购及施工未开展',11,'#87816F');end()

begin('BRIEF & PLAN / 02','给日常活动安排清楚的位置','东侧入户，南侧公共活动，北侧两卧与独立书房')
draw.pdf_scene(c,draw.plan(m,'furniture'),102,185,.052,font=FONT)
roomrows=[[r['id'],r['name'],f"{r['rect'][2]*r['rect'][3]/1e6:.2f}"] for r in m['rooms']]
table(845,678,290,['编号','空间','㎡'],roomrows,[.7,1.8,.7],11,31)
y=365
for line in ['1000mm走廊串联各房间。','主卧床尾780mm，厨房操作1350mm。','餐桌1400×800，侧向操作800mm。','书房有工作台及可展开沙发床。','净距是本项目设计目标。']:
    y=wrap(845,y,line,280,12,20)-9
end()

begin('MATERIAL & ATMOSPHERE / 03','用浅木和米白统一公共空间','同源模型表现：开口、家具和材料来自同一项目数据')
image('02-living.png',52,185,740,505)
palette=['M01','M05','M06','M08','M09']
for i,id in enumerate(palette):
    mat=next(x for x in m['materials'] if x['id']==id);y=650-i*80
    box(845,y-38,65,48,mat['color']);text(925,y-2,id+' '+mat['name'],13);wrap(925,y-22,mat['use'],205,10,15)
wrap(845,225,'干区连续木地板，厨卫浅石色砖；可见柜面保持同一浅木色。实际色差、触感和性能通过样品确认。',285,12,22)
text(62,110,'客厅电视背景改至西侧实墙，保留南窗；沙发与茶几同步转向，避免遮挡采光开口。',12);end()

begin('DETAIL & SERVICES / 04','把工作、收纳和设备接起来','两处独立学习工作位；柜体与点位按编号交接')
image('03-study.png',52,215,690,465)
text(785,665,'J01 主卧衣柜',18)
wrap(785,630,'2400×600×2400。板18、背板9、踢脚100、两侧收口各20；三分区内部净宽约762.7mm。',340,13,24)
text(785,505,'J07 / J08 厨房柜',18)
wrap(785,470,'L形地柜沿墙2480+2000=4480mm，台面高850。设备安装图先于开孔和生产订单。',340,13,24)
text(785,355,'设备与机电条件',18)
wrap(785,320,'11项设备、12处条件点位、28盏/条灯具与14个控制组。点位图表达接口需求，保护、容量、管径和坡度待专业深化。',340,13,24)
wrap(62,150,'书房工作台2000×650，书柜2100×450。沙发床常态1400×850；临时客用展开时移走工作椅。',1030,12,21)
end()

begin('COST & REVISION / 05','预算随设计修改，问题保留复查证据','单价是示范估算输入；金额口径为CNY，包含10%预备费')
tot=tools.totals(m);cats={}
for b in tools.budget_rows(m):cats[b['category']]=cats.get(b['category'],0)+b['amount']
rows=[[k,f'{v:,.2f}'] for k,v in cats.items()]+[['基础合计',f'{tot["base"]:,.2f}'],['预备费',f'{tot["reserve"]:,.2f}'],['总估算',f'{tot["total"]:,.2f}'],['预算余量',f'{tot["remaining"]:,.2f}']]
table(52,680,450,['费用项','金额（元）'],rows,[1.4,1],12,37)
y=655
for title,detail in [
('ISS01 餐桌侧向净距','初稿2000mm桌长造成200mm净距；改为1400mm，复查为800mm，含预备费减少1430元。'),
('ISS02 冰箱电源可达','初稿电源点落在冰箱机身后；移至相邻可达区，点位表及条件图同步。'),
('ISS03 电视背景与南窗','立面协调发现冲突；保持原门窗，将客厅家具转向西实墙，P01同步移位。')]:
    text(570,y,title,18);y=wrap(570,y-35,detail,545,13,24)-42
wrap(570,155,'前两项由可计算检查发现，第三项来自设计者立面协调。修订前后模型、问题台账和复查结果分别保存。',540,12,22)
end()

begin('SKILLS & DELIVERY / 06','15个技能完成同一套项目交付','每个阶段保留输入、技能与输出哈希，现场工作不因模板生成而自动完成')
catalog=json.loads((ROOT/'catalog.json').read_text())['skills']
rows=[[str(i+1).zfill(2),x['name'],x['title']] for i,x in enumerate(catalog)]
table(52,685,705,['序号','Skill','本轮阶段'],rows,[.45,2.2,1.4],11,32)
text(805,665,'交付入口',18)
y=625
for line in ['本册：方案汇报+6张深化图。','CAD：6组图，模型空间1:1 mm。','SVG：各图可单独查看与编辑。','模型：Blender源文件与GLB。','清单：材料、家具、灯具、设备、点位。','预算：可重算工作簿与CSV。','记录：3项问题、2次设计变更。','现场：交底、送样和变更模板。']:
    y=wrap(805,y,line,325,12,21)-14
wrap(805,190,'示范尺寸与单价均有标记。下一步真实项目应用先接收实测及专业条件，再沿用相同编号与流程。',325,12,22)
end()

notes={
'furniture':['主体净距：C01 800 / C02 780 / C03 600 / C04 1350mm。','1000mm走廊保持连续，不设柜体。','浅色填充为家具/定制，开口与房间编号见模型。','尺寸及单价为本项目示范设定。'],
'finishes':['M01干区74.1336㎡，加5%损耗。','M02厨房9.2160㎡；M03卫浴9.1848㎡，各加8%损耗。','房间净面积含柜下满铺，不含门洞墙厚投影。','门口同完成面，基层厚度与实测高差联合确定。'],
'lighting':['28盏/条、14个控制组；虚线仅示分组，不代表配线。','公共与休息区3000K；厨房与工作区3500K意向。','编号和功率、流明、安装标高详灯具表。','配光、眩光及控制接线按选定产品深化。'],
'mep':['方形为设备意向；圆形为条件点位。','P07已移至冰箱相邻可达区。','标高z自完成地面起，单位mm。','图示不含回路保护、管径、坡度或完整施工系统。'],
'dimensions':['总轮廓12000×8000。','内隔墙厚120；外墙厚200，为示范设定。','门窗按墙轴坐标定位，含高窗投影示意。','现场复尺、结构属性及服务基线仍须按真实项目补齐。'],
'joinery':['J01外包尺寸及内净尺寸分开。','柜门采用滑门意向，五金安装图复核。','厨房柜身730+踢脚100+台面20。','节点表达设计意向，不替代厂家生产图。']}
for code,title,kind in draw.SHEETS:
    begin(code,title,'栖木之家 / '+m['revision']+' / 设计深化示范 / 单位mm')
    draw.pdf_scene(c,draw.plan(m,kind),115,150,.0566929134,font=FONT)
    box(900,160,235,535,'#EFEEE5')
    text(918,665,'图面说明',15);y=625
    for i,line in enumerate(notes[kind],1):y=wrap(918,y,f'{i}. '+line,198,11,20)-24
    text(918,210,'平面比例 1:50（A3原幅）' if kind!='joinery' else '柜体1:50 / 节点示意',10)
    text(918,188,'CAD模型空间为1:1',10);end()

c.save();print(json.dumps({'pdf':str(OUT),'pages':page,'revision':m['revision']},ensure_ascii=False))
