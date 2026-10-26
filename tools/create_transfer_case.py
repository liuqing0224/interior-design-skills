#!/usr/bin/env python3
"""Reproducible synthetic transfer fixture. Never represents a measured home."""
import copy
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
P=ROOT/'projects/TEST-L-084'

def model():
    m=dict(project_id='TEST-L-084',title='折庭',revision='v1.0',units='mm',
        input_kind='design_assumption',location_status='synthetic_transfer_test',
        budget_cny=220000,reserve_rate=.1,envelope=[1000,2000,10500,9000],
        outline=[[1000,2000],[11500,2000],[11500,7500],[8500,7500],[8500,11000],[1000,11000]],
        ceiling_height_mm=2700,site_status='not_started',procurement_status='not_ordered')
    m['rooms']=[dict(id=id,name=name,rect=rect,floor=floor) for id,name,rect,floor in [
        ('LOUNGE','客餐厅',[1000,2000,7500,4300],'OAK'),
        ('COOK','厨房',[8620,2000,2880,4300],'STONE'),
        ('PASS','横厅通道',[1000,6420,10500,1080],'OAK'),
        ('SLEEP','卧室',[1000,7620,3480,3380],'OAK'),
        ('WORK','独立书房',[4600,7620,1780,3380],'OAK'),
        ('WASH','卫浴',[6500,7620,2000,3380],'WET')]]
    m['rooms'][0]['label_xy']=[4900,5950]
    m['rooms'][2]['label_xy']=[5200,6970]
    m['materials']=[dict(id=id,name=name,color=color,use=use,spec=spec,sample_status='not_submitted',pattern={'spacing_mm':spacing}) for id,name,color,use,spec,spacing in [
        ('OAK','浅木复合地板','#C9AD88','干区地面','板宽160mm',[160,0]),
        ('STONE','灰米厨房地砖','#CEC9BE','厨房地面','800×800',[800,800]),
        ('WET','浅灰卫浴砖','#B6BCB7','卫浴地面','300×600',[300,600]),
        ('WOOD','浅木柜面','#B69570','定制与桌面','18mm板',[0,0]),
        ('FABRIC','米白织物','#E4DFD2','沙发与床','示意色',[0,0]),
        ('METAL','暖灰金属','#7F8C87','家电与灯具','示意色',[0,0])]]
    def wall(id,axis,start,end,at,t,internal=False):return dict(id=id,axis=axis,start=start,end=end,at=at,thickness=t,height=2700,internal=internal)
    m['walls']=[wall('EXT-S','x',800,11700,1800,200),wall('EXT-E','y',2000,7700,11500,200),
        wall('NOTCH-S','x',8500,11500,7500,200),wall('NOTCH-W','y',7700,11200,8500,200),
        wall('EXT-N','x',800,8500,11000,200),wall('EXT-W','y',2000,11000,800,200),
        wall('PART-K','y',2000,6300,8500,120,True),wall('PART-S','x',1000,11500,6300,120,True),
        wall('PART-N','x',1000,8500,7500,120,True),wall('PART-B','y',7620,11000,4480,120,True),
        wall('PART-C','y',7620,11000,6380,120,True)]
    m['openings']=[dict(id=id,wall=w,start=start,width=width,height=height,sill=sill,kind=kind) for id,w,start,width,height,sill,kind in [
        ('ENTRY','EXT-E',6500,900,2100,0,'door'),('K-DOOR','PART-K',4200,900,2100,0,'sliding'),
        ('L-DOOR','PART-S',1800,900,2100,0,'door'),('K-HALL','PART-S',9400,900,2100,0,'door'),
        ('BED-DOOR','PART-N',1800,800,2100,0,'door'),('WORK-DOOR','PART-N',4700,800,2100,0,'sliding'),
        ('BATH-DOOR','PART-N',6600,800,2100,0,'sliding'),('GLAZE-S','EXT-S',1500,2200,1500,900,'window'),
        ('GLAZE-K','EXT-S',9100,1800,1500,900,'window'),('GLAZE-B','EXT-N',1600,1900,1500,900,'window'),
        ('GLAZE-W','EXT-N',4800,1200,1500,900,'window'),('GLAZE-H','EXT-N',6900,1000,700,1700,'window')]]
    m['furniture']=[]
    def furniture(id,name,room,rect,height,kind='furniture',material='WOOD',front=None):
        f=dict(id=id,name=name,room=room,rect=rect,height_mm=height,kind=kind,material=material)
        if kind=='joinery':f.update(front_axis=front or 'x',joinery=dict(panel_mm=18,back_mm=9,plinth_mm=80,scribe_mm=15,bays=3 if id=='CAB-A' else 2))
        m['furniture'].append(f)
    furniture('SOFA-A','双人沙发','LOUNGE',[1400,4800,2400,900],800,material='FABRIC')
    furniture('TABLE-C','茶几','LOUNGE',[1700,3600,1100,600],380)
    furniture('TV-LOW','电视矮柜','LOUNGE',[1500,2100,2400,350],550,'joinery')
    furniture('DINING','四人餐桌','LOUNGE',[5700,3500,1600,850],750)
    for id,x,y in [('SEAT-1',5800,2900),('SEAT-2',6700,2900),('SEAT-3',5800,4500),('SEAT-4',6700,4500)]:furniture(id,'餐椅','LOUNGE',[x,y,450,450],780)
    furniture('SIDE-A','餐边柜','LOUNGE',[7850,3000,450,2200],1000,'joinery',front='y')
    furniture('BED-A','双人床','SLEEP',[1400,8200,1600,2100],550,material='FABRIC')
    furniture('CAB-A','卧室衣柜','SLEEP',[3880,8200,600,2200],2200,'joinery',front='y')
    furniture('DESK-A','书房工作台','WORK',[4700,10350,1500,600],740)
    furniture('CHAIR-A','工作椅','WORK',[5100,9500,550,550],820)
    furniture('KT-BASE','厨房地柜','COOK',[8900,2100,2400,600],850,'joinery')
    furniture('FRIDGE','冰箱','COOK',[10600,5200,750,750],1900,'equipment','METAL')
    furniture('VANITY','浴室柜','WASH',[6500,9000,500,1200],850,'joinery',front='y')
    furniture('WC-A','坐便体量','WASH',[7500,8100,700,900],750,'equipment','METAL')
    m['fixtures']=[dict(id='SINK-A',room='COOK',rect=[10200,2200,650,400])]
    # A shower rectangle is intentionally absent: optional fixture handling is tested.
    m['equipment']=[dict(id='REF-E',room='COOK',object='FRIDGE',name='冰箱'),
        dict(id='AC-E',room='LOUNGE',xy=[8000,5700],name='分体空调'),
        dict(id='FAN-E',room='WASH',xy=[8200,10500],name='排风机')]
    m['control_groups']=[dict(id='G-'+r['id'],name=r['name']) for r in m['rooms']]
    m['lights']=[]
    for room,points in [('LOUNGE',[(2300,4200),(4600,4200),(6700,3900)]),('COOK',[(9500,3500),(10600,4400)]),('PASS',[(3500,6900),(9000,6900)]),('SLEEP',[(2700,9300)]),('WORK',[(5500,9200)]),('WASH',[(7600,10000)])]:
        for xy in points:m['lights'].append(dict(id='LAMP-'+str(len(m['lights'])+1),room=room,xy=list(xy),group='G-'+room,power_w=12,lumens=1000,name='吸顶或筒灯意向',z_mm=2600))
    m['points']=[dict(id=id,room=room,xy=xy,z_mm=z,type=typ,link=link,access_required=True,status='intent_not_construction') for id,room,xy,z,typ,link in [
        ('POWER-R','COOK',[10400,6000],1300,'冰箱可维护电源','REF-E'),
        ('POWER-D','WORK',[6200,10200],1100,'工作位电源','DESK-A'),
        ('WATER-K','COOK',[10900,2850],550,'厨房给排水条件','SINK-A'),
        ('WATER-H','WASH',[7100,9800],550,'浴室给排水条件','VANITY')]]
    m['clearances']=[dict(id='C-DINE',name='餐桌至餐边柜',**{'from':'DINING','to':'SIDE-A'},axis='x',target_mm=500,basis='project_design_target'),
        dict(id='C-BED',name='床侧至衣柜',**{'from':'BED-A','to':'CAB-A'},axis='x',target_mm=800,basis='project_design_target')]
    m['clear_zones']=[dict(id='CIRCULATION',name='横厅通道',rect=[1000,6420,10500,1080])]
    m['drawing']=dict(joinery_ids=['CAB-A','KT-BASE','SIDE-A'])
    m['budget']=[]
    def budget(id,category,name,rate,unit,rule=None,q=1,waste=0,basis='按模型对象计量'):
        b=dict(id=id,category=category,name=name,quantity=q,unit=unit,rate=rate,waste=waste,basis=basis,source='synthetic_estimate_not_quote')
        if rule:b['quantity_rule']=rule
        m['budget'].append(b)
    for id,mat,rate,waste in [('Q-OAK','OAK',235,.05),('Q-KT','STONE',245,.08),('Q-WET','WET',250,.08)]:budget(id,'硬装',mat+'地面供装',rate,'㎡',dict(kind='floor',materials=[mat]),waste=waste,basis='净分区面积，柜下满铺；加所列损耗')
    budget('Q-CEILING','硬装','顶面基层与涂装',125,'㎡',dict(kind='net_area'))
    budget('Q-DOORS','硬装','室内门及五金',2100,'套',dict(kind='count',collection='openings',ids=['K-DOOR','L-DOOR','K-HALL','BED-DOOR','WORK-DOOR','BATH-DOOR']))
    budget('Q-PAINT','硬装','墙面及湿区基层暂估',18000,'项',basis='综合暂估，未建立墙面展开量规则')
    budget('Q-PROTECT','硬装','保护与清运',4200,'项',basis='测试估算包项')
    for id,category,rate in [('CAB-A','定制',1050),('SIDE-A','定制',900),('TV-LOW','定制',900)]:budget('Q-'+id,category,id+'柜体',rate,'㎡',dict(kind='projection',ids=[id]),basis='front_axis正面宽度×高度；含板材五金')
    for id,rate in [('KT-BASE',3000),('VANITY',2700)]:budget('Q-'+id,'定制',id+'柜体及台面',rate,'m',dict(kind='length',ids=[id]),basis='沿front_axis正面长度，非最大包围边默认值')
    budget('Q-LAMPS','灯具','灯具与驱动',650,'盏',dict(kind='count',collection='lights'))
    budget('Q-POINTS','机电','条件点位施工暂估',600,'点',dict(kind='count',collection='points'),basis='每个条件点暂估，系统深化费用另列')
    budget('Q-MEP','机电','管线及系统深化暂估',14000,'项',basis='不重复点位；测试估算包项')
    budget('Q-EQUIP','家电设备','设备采购供装暂估',3800,'台',dict(kind='count',collection='equipment'),basis='每台测试统一估算；不代表选型报价')
    for id,name,rate in [('SOFA-A','双人沙发',5500),('TABLE-C','茶几',1800),('DINING','餐桌',3000),('BED-A','床及床垫',4800),('DESK-A','工作桌',1800),('CHAIR-A','工作椅',900),('WC-A','坐便器',2600)]:budget('Q-'+id,'家具洁具',name,rate,'件',dict(kind='count',ids=[id]))
    budget('Q-SEATS','家具洁具','餐椅',600,'把',dict(kind='count',ids=['SEAT-1','SEAT-2','SEAT-3','SEAT-4']))
    budget('Q-SOFT','软装','窗帘与饰品暂估',7000,'项',basis='测试估算包项')
    budget('Q-SERVICE','服务','设计与协调暂估',16000,'项',basis='测试预算结构设定')
    return m

def main():
    if P.exists():raise SystemExit('Refusing to replace existing transfer fixture')
    for part in ['model','state','drawings','schedules','documents','history/v1.0/model']:(P/part).mkdir(parents=True,exist_ok=True)
    before=model();after=copy.deepcopy(before);after['revision']='v1.1'
    cabinet=next(f for f in after['furniture'] if f['id']=='CAB-A');cabinet['rect'][3]=2600;cabinet['height_mm']=2450
    for path,value in [(P/'history/v1.0/model/project.json',before),(P/'model/project.json',after)]:path.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n')
    print(P)

if __name__=='__main__':main()
