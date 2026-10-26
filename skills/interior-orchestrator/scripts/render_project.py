"""Run with Blender: blender -b -t 4 --python render_project.py -- PROJECT_DIR."""
import bpy
import json
import math
import sys
import hashlib
from pathlib import Path
from mathutils import Vector

P=Path(sys.argv[sys.argv.index('--')+1]).resolve()
m=json.loads((P/'model/project.json').read_text());out=P/'visuals';out.mkdir(exist_ok=True)
(out/'render-input.json').write_text((P/'model/project.json').read_text())
bpy.ops.wm.read_factory_settings(use_empty=True)
scene=bpy.context.scene
scene.render.engine='CYCLES';scene.cycles.samples=32;scene.cycles.use_denoising=True
scene.render.resolution_x=1600;scene.render.resolution_y=1060;scene.render.resolution_percentage=100
scene.render.image_settings.file_format='PNG';scene.render.film_transparent=False
scene.world=bpy.data.worlds.new('Warm daylight');scene.world.use_nodes=True
scene.world.node_tree.nodes['Background'].inputs[0].default_value=(.79,.83,.88,1)
scene.world.node_tree.nodes['Background'].inputs[1].default_value=.5
scene.view_settings.view_transform='AgX'
scene.view_settings.look='AgX - Medium High Contrast'
scene.view_settings.exposure=-0.35
scene.render.image_settings.color_mode='RGB'

def material(name,color,rough=.65,wood=False):
    rgb=tuple(int(color[i:i+2],16)/255 for i in [1,3,5])
    col=tuple(v/12.92 if v<.04045 else ((v+.055)/1.055)**2.4 for v in rgb)
    mat=bpy.data.materials.new(name);mat.diffuse_color=(*col,1);mat.use_nodes=True
    nodes=mat.node_tree.nodes;p=nodes.get('Principled BSDF');p.inputs['Base Color'].default_value=(*col,1);p.inputs['Roughness'].default_value=rough
    if wood:
        noise=nodes.new('ShaderNodeTexNoise');noise.inputs['Scale'].default_value=6;noise.inputs['Detail'].default_value=2
        mapping=nodes.new('ShaderNodeVectorMath');mapping.operation='MULTIPLY';mapping.inputs[1].default_value=(2,35,2)
        tc=nodes.new('ShaderNodeTexCoord');mat.node_tree.links.new(tc.outputs['Generated'],mapping.inputs[0]);mat.node_tree.links.new(mapping.outputs['Vector'],noise.inputs['Vector'])
        ramp=nodes.new('ShaderNodeValToRGB');ramp.color_ramp.elements[0].position=.1;ramp.color_ramp.elements[0].color=(*[c*.65 for c in col],1);ramp.color_ramp.elements[1].position=.9;ramp.color_ramp.elements[1].color=(*col,1)
        mat.node_tree.links.new(noise.outputs['Fac'],ramp.inputs[0]);mat.node_tree.links.new(ramp.outputs[0],p.inputs['Base Color'])
    return mat
M={x['id']:material(x['id']+' '+x['name'],x['color'],wood=x['id'] in ['M01','M06']) for x in m['materials']}
white=material('Linen white','#F5F1E8');dark=material('Bronze details','#4F584E',.4);glass=material('Window light blue','#D8E6E4',.3)
screen=material('TV screen','#202925',.32);pillow=material('Accent pillow','#84917B');base=material('Plinth','#DDD5C5')

def box(name,rect,z,h,mat,bevel=0,collection=None):
    x,y,w,d=[v/1000 for v in rect];z/=1000;h/=1000
    bpy.ops.mesh.primitive_cube_add(size=1,location=(x+w/2,y+d/2,z+h/2));o=bpy.context.object;o.name=name;o.dimensions=(w,d,h)
    bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
    o.data.materials.append(mat)
    if bevel:
        mod=o.modifiers.new('Soft edges','BEVEL');mod.width=bevel;mod.segments=3
        o.modifiers.new('Weighted normals','WEIGHTED_NORMAL')
    if collection:
        for c in list(o.users_collection):c.objects.unlink(o)
        collection.objects.link(o)
    return o

def cyl(name,x,y,z,r,h,mat):
    bpy.ops.mesh.primitive_cylinder_add(vertices=32,radius=r/1000,depth=h/1000,location=(x/1000,y/1000,(z+h/2)/1000));o=bpy.context.object;o.name=name;o.data.materials.append(mat)
    mod=o.modifiers.new('Edge','BEVEL');mod.width=.01;mod.segments=2
    for p in o.data.polygons:p.use_smooth=True
    return o

full=bpy.data.collections.new('Walls - full');scene.collection.children.link(full)
cut=bpy.data.collections.new('Walls - cutaway');scene.collection.children.link(cut)
def wall_set(collection,limit):
    for w in m['walls']:
        opens=[o for o in m['openings'] if o['wall']==w['id']];bounds=sorted(set([w['start'],w['end']]+[v for o in opens for v in [o['start'],o['start']+o['width']]]))
        for a,b in zip(bounds,bounds[1:]):
            o=next((o for o in opens if o['start']<=(a+b)/2<o['start']+o['width']),None)
            zspans=[(0,min(o['sill'],limit)),(min(limit,o['sill']+o['height']),limit)] if o else [(0,limit)]
            rect=[a,w['at'],b-a,w['thickness']] if w['axis']=='x' else [w['at'],a,w['thickness'],b-a]
            for z1,z2 in zspans:
                if z2>z1:box(w['id'],rect,z1,z2-z1,M['M05'],.007,collection)
wall_set(full,2700);wall_set(cut,1050)
for r in m['rooms']:
    box(r['id']+' floor',r['rect'],-40,40,M[r['floor']],.003)
    x,y,w,d=r['rect']
    step=180 if r['floor']=='M01' else 600
    for xx in range(x+step,x+w,step):box('floor joint',[xx,y,2,d],.2,.3,base)
    if step==600:
        for yy in range(y+step,y+d,step):box('tile joint',[x,yy,w,2],.2,.3,base)
box('foundation',[-230,-230,12460,8460],-180,140,base,.025)
for o in m['openings']:
    if o['kind']!='window':continue
    w=next(w for w in m['walls'] if w['id']==o['wall']);a=o['start'];width=o['width'];sill=o['sill'];h=o['height'];at=w['at']
    if w['axis']=='x':
        rect=[a,at+85,width,30];frame=[a,at+30,width,140]
    else:rect=[at+85,a,30,width];frame=[at+30,a,140,width]
    box(o['id']+' glazing',rect,sill,h,glass,.002,full)
    box(o['id']+' sill',frame,sill-30,30,white,.005,full)
    box(o['id']+' head',frame,sill+h-25,25,dark,0,full)
    for k in range(4):
        if w['axis']=='x':rr=[a+width*k/3-12,at+30,24,140]
        else:rr=[at+30,a+width*k/3-12,140,24]
        box(o['id']+' mullion',rr,sill,h,dark,0,full)

for f in m['furniture']:
    x,y,w,d=f['rect'];h=f['height_mm'];mat=M[f['material']];id=f['id']
    if f['kind']=='rug':box(id,f['rect'],3,8,mat,.014);continue
    if id=='F01':
        # Sofa faces west; long axis follows Y in this project's final layout.
        box(id+' base',[x+40,y+30,w-80,d-60],80,270,mat,.07)
        box(id+' back',[x+w-170,y,w and 170,d],320,480,mat,.07)
        for yy in [y,y+d-170]:box(id+' arm',[x,yy,w,170],250,470,mat,.065)
        for i in range(3):box(id+' seat',[x+30,y+190+i*(d-380)/3,w-220,(d-400)/3],350,150,mat,.055)
        for yy in [y+550,y+d-850]:box('pillow',[x+w-300,yy,150,400],500,260,pillow,.05)
    elif id in ['F09','F10']:
        box(id+' bed frame',f['rect'],80,220,M['M06'],.05)
        box(id+' mattress',[x+25,y+25,w-50,d-50],300,200,white,.08)
        if id=='F09':
            box('master headboard',[x-35,y-35,90,d+70],0,1000,M['M06'],.03)
            for yy in [y+180,y+d-650]:box('pillow',[x+150,yy,500,450],500,100,white,.08)
            box('bed throw',[x+1100,y+20,600,d-40],505,35,pillow,.015)
        else:
            box('child headboard',[x-35,y+d-40,w+70,90],0,950,M['M06'],.03)
            box('child pillow',[x+130,y+d-550,w-260,400],500,100,white,.07)
            box('child throw',[x+20,y+200,w-40,700],505,30,pillow,.01)
    elif id in ['F04','F11','F13','F02']:
        box(id+' top',f['rect'],h-40,40,mat,.02)
        for xx in [x+55,x+w-100]:
            for yy in [y+55,y+d-100]:box(id+' leg',[xx,yy,45,45],0,h-40,M['M06'],.005)
    elif id in ['F03','F05','F06','F07','F08','F12','F14']:
        box(id+' seat',[x,y,w,d],380,100,mat,.045)
        box(id+' back',[x,y+d-80,w,80],450,h-450,mat,.035)
        for xx in [x+35,x+w-65]:
            for yy in [y+35,y+d-65]:box(id+' leg',[xx,yy,30,30],0,380,dark,.003)
    elif id=='F15':
        box(id,f['rect'],100,350,mat,.06);box(id+' back',[x,y+d-150,w,150],420,360,mat,.06)
        for xx in [x,x+w-120]:box(id+' arm',[xx,y,120,d],300,350,mat,.04)
    elif f['kind']=='joinery':
        box(id,f['rect'],0,h,M['M06'],.008)
        if w>d:
            for xx in range(int(x+600),int(x+w),600):box('cabinet seam',[xx,y-1,2,2],100,h-130,dark)
        else:
            for yy in range(int(y+600),int(y+d),600):box('cabinet seam',[x-1,yy,2,2],100,h-130,dark)
        if id in ['J07','J08']:box(id+' stone top',f['rect'],h-20,20,M['M07'],.005)
        if id=='J09':box(id+' stone top',f['rect'],h-30,30,white,.015);box('basin',[x+60,y+300,430,600],h,140,white,.04)
        if id=='J04':
            # Readable open shelf fronts on the west face, within external envelope.
            for yy in [y+80,y+780,y+1480]:
                for zz in [1050,1500,1950]:
                    box('book shelf recess',[x-2,yy,20,610],zz,360,dark,.005)
                    for i in range(4):box('book',[x-20,yy+50+i*65,55,40],zz+20,220,M['M05'] if i%2 else pillow,.003)
    elif id=='F17':
        box(id,f['rect'],0,h,M['M09'],.025);box('fridge split',[x,y-2,w,4],1200,3,dark)
    elif id=='F18':
        box(id,f['rect'],0,h,white,.02)
        for z in [470,1390]:
            # Front-loading doors face east toward the bathroom operating zone.
            o=cyl('washer round',x+w/2,y-8,z,210,25,dark);o.rotation_euler.x=math.pi/2
    elif id=='F19':
        box('cistern',[x+80,y+d-270,w-160,270],0,750,white,.05)
        box('toilet pan',[x+70,y,w-140,d-180],0,420,white,.12)
    else:box(id,f['rect'],0,h,mat,.02)

# Fixed details follow the same equipment intent, not independent room geometry.
box('TV screen west wall',[40,1150,55,1400],900,800,screen,.012,full)
box('range hood',[9930,190,800,400],1580,450,dark,.025)
box('sink inset',[11500,1450,350,550],850,25,dark,.04)
for xx,yy in [(10000,370),(10350,370),(10000,600),(10350,600)]:cyl('cooktop',xx,yy,850,80,8,dark)
shx,shy,shw,shd=m['shower']['rect']
box('Shower glass',[shx,shy,shw,15],0,2100,glass,.003)
box('Shower rail',[shx+shw-100,shy+shd-100,25,25],1000,900,dark,.005)
box('Shower head',[shx+shw-250,shy+shd-150,250,220],2050,20,dark,.015)
box('Bath mirror',[9460,5900,25,800],1100,1050,glass,.01)
for f in m['furniture']:
    if f['id'] in ['F11','F13']:
        x,y,w,d=f['rect'];box('desk monitor',[x+w/2-230,y+d-100,460,45],950,280,screen,.008)
        box('keyboard',[x+w/2-210,y+d-270,420,150],f['height_mm']+2,12,dark,.008)

for l in m['lights']:
    x,y=l['xy'];z=l['z_mm']
    if l['type']=='餐桌线性吊灯':
        box(l['id'],[x-550,y-25,1100,50],z,50,dark,.01)
        for xx in [x-450,x+450]:box('pendant suspension',[xx-2,y-2,4,4],z+50,2700-z-50,dark)
    elif l['type'] in ['筒灯','面板灯','吸顶灯','湿区防护灯']:
        o=cyl(l['id'],x,y,2650,70,35,white)
        for c in list(o.users_collection):c.objects.unlink(o)
        full.objects.link(o)
    else:box(l['id'],[x-90,y-15,180,30],z,35,white,.005)

def area(name,loc,energy,size,target):
    data=bpy.data.lights.new(name,'AREA');data.energy=energy;data.shape='DISK';data.size=size
    o=bpy.data.objects.new(name,data);scene.collection.objects.link(o);o.location=loc
    o.rotation_euler=(Vector(target)-o.location).to_track_quat('-Z','Y').to_euler();return o
area('Softbox south',(5,-4,8),1800,7,(6,4,0))
area('Softbox west',(-3,3,6),1100,6,(3,4,1))
area('Interior ambient',(6,4,5),600,8,(6,4,0))
for room,loc in [('living',(2.8,1.8,2.65)),('dining',(7,1.6,2.6)),('master',(1.8,6.6,2.65)),('child',(5.2,6.4,2.65)),('study',(8,6.4,2.65)),('bath',(10.8,6.2,2.65))]:area(room,loc,65 if room=='bath' else 90,2,(loc[0],loc[1],0))

data=bpy.data.cameras.new('Camera');camera=bpy.data.objects.new('Camera',data);scene.collection.objects.link(camera);scene.camera=camera
manifest={'model_sha256':hashlib.sha256((P/'model/project.json').read_bytes()).hexdigest(),'revision':m['revision'],'engine':'Cycles CPU','samples':32,'views':[]}
def render(name,loc,target,orthographic=False,lens=28):
    camera.location=loc;camera.rotation_euler=(Vector(target)-camera.location).to_track_quat('-Z','Y').to_euler()
    data.type='ORTHO' if orthographic else 'PERSP';data.lens=lens
    if orthographic:data.ortho_scale=17.2
    full.hide_render=orthographic;cut.hide_render=not orthographic
    scene.render.filepath=str(out/(name+'.png'))
    bpy.ops.render.render(write_still=True)
    manifest['views'].append({'file':name+'.png','camera':list(loc),'target':list(target),'type':data.type,'lens':lens,'cutaway_wall_height_mm':1050 if orthographic else None})

render('01-axon',(17,-17,20),(6,4,0),True)
render('02-living',(5.45,3.12,2.05),(1.7,1.65,1.05),False,25)
render('03-study',(7.25,4.82,1.85),(8.15,7.25,1.15),False,23)
full.hide_render=False;cut.hide_render=True
bpy.ops.wm.save_as_mainfile(filepath=str(out/'qimu-home.blend'))
full.hide_viewport=False;cut.hide_viewport=True
bpy.ops.object.select_all(action='DESELECT')
for o in scene.objects:
    if o.type=='MESH' and not any(c==cut for c in o.users_collection):o.select_set(True)
bpy.ops.export_scene.gltf(filepath=str(out/'qimu-home.glb'),use_selection=True,export_format='GLB',export_cameras=False,export_lights=False)
(out/'render-manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')
print('RENDER_COMPLETE',len(manifest['views']))
