#!/usr/bin/env python3
"""Behavior checks on a second geometry and a known cabinet change."""
import copy
import csv
import importlib.util
from pathlib import Path
import subprocess
import shutil
import sys
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'skills/interior-orchestrator/scripts'))
import project_tools as t
import drawing_lib as d
P=ROOT/'projects/TEST-L-084'
BEFORE=t.load(P/'history/v1.0/model/project.json');AFTER=t.load(P/'model/project.json')

class TransferTests(unittest.TestCase):
    def reject(self,fn,code):
        model=copy.deepcopy(AFTER);fn(model);r=t.check(model)
        self.assertFalse(r['passed']);self.assertIn(code,{i['code'] for i in r['issues']})
    def test_both_versions_cover_true_footprint(self):
        for m in [BEFORE,AFTER]:
            r=t.check(m);self.assertTrue(r['passed'],r['issues']);self.assertEqual(r['envelope_area_m2'],84);self.assertEqual(r['bounding_box_area_m2'],94.5);self.assertEqual(r['net_area_m2'],80.5128)
    def test_notch_is_outside(self):self.reject(lambda m:m['rooms'].append(dict(id='IN-NOTCH',name='bad',floor='OAK',rect=[9000,8000,1000,1000])),'OUTSIDE')
    def test_concavity_requires_more_than_corners(self):
        m={'envelope':[0,0,10,10],'outline':[[0,0],[10,0],[10,10],[7,10],[7,4],[3,4],[3,10],[0,10]]}
        t.validate_outline(m)
        self.assertTrue(all(t.inside_outline(m,x,y) for x,y in [(1,7),(9,7),(9,9),(1,9)]))
        self.assertFalse(t.rect_in_footprint(m,[1,7,8,2]))
    def test_diagonal_outline_rejected(self):self.reject(lambda m:m['outline'][1].__setitem__(1,2100),'GEOMETRY')
    def test_bounding_box_mismatch_rejected(self):self.reject(lambda m:m['envelope'].__setitem__(2,11000),'GEOMETRY')
    def test_repeated_outline_vertex_rejected(self):self.reject(lambda m:m['outline'].append(m['outline'][0][:]),'GEOMETRY')
    def test_self_intersection_rejected(self):
        self.reject(lambda m:m.__setitem__('outline',[[1000,2000],[11500,2000],[11500,11000],[5000,11000],[5000,1000],[7000,1000],[7000,7500],[1000,7500]]),'GEOMETRY')
    def test_real_gap_still_reported(self):self.reject(lambda m:m['rooms'][0]['rect'].__setitem__(2,7000),'AREA_GAP')
    def test_no_shower_is_supported(self):
        self.assertNotIn('shower',AFTER)
        for _,_,kind in d.SHEETS:self.assertGreater(len(d.plan(AFTER,kind).items),0)
    def test_cabinet_change_expected_quantities(self):
        get=lambda m:next(row for row in t.budget_rows(m) if row['id']=='Q-CAB-A')
        self.assertEqual(get(BEFORE)['quantity'],4.84);self.assertEqual(get(AFTER)['quantity'],6.37)
        self.assertAlmostEqual(get(AFTER)['amount']-get(BEFORE)['amount'],1606.5)
        self.assertAlmostEqual(t.totals(AFTER)['total']-t.totals(BEFORE)['total'],1767.15)
    def test_explicit_front_axis_controls_projection(self):
        m=copy.deepcopy(AFTER);next(f for f in m['furniture'] if f['id']=='CAB-A')['front_axis']='x'
        self.assertEqual(next(row for row in t.budget_rows(m) if row['id']=='Q-CAB-A')['quantity'],1.47)
    def test_collection_counts_update(self):
        m=copy.deepcopy(AFTER);extra=copy.deepcopy(m['lights'][0]);extra['id']='NEW-LAMP';m['lights'].append(extra)
        get=lambda m:next(row for row in t.budget_rows(m) if row['id']=='Q-LAMPS')['quantity']
        self.assertEqual(get(m)-get(AFTER),1)
    def test_bad_quantity_reference(self):self.reject(lambda m:m['budget'][0].__setitem__('quantity_rule',{'kind':'count','ids':['MISSING']}),'BUDGET_INPUT')
    def test_duplicate_quantity_reference(self):self.reject(lambda m:m['budget'][0].__setitem__('quantity_rule',{'kind':'count','ids':['BED-A','BED-A']}),'BUDGET_INPUT')
    def test_invalid_cabinet_interior(self):self.reject(lambda m:next(f for f in m['furniture'] if f['id']=='CAB-A')['joinery'].__setitem__('panel_mm',1000),'JOINERY')
    def test_unknown_cabinet_selection(self):self.reject(lambda m:m['drawing'].__setitem__('joinery_ids',['MISSING']),'DRAWING_REF')
    def test_plan_and_elevation_use_changed_geometry(self):
        plan=d.plan(AFTER,'furniture');p=next(p for p in plan.items if p.get('id')=='CAB-A')
        self.assertEqual((p['w'],p['h']),(600,2600))
        elevation=d.joinery(AFTER);p=next(p for p in elevation.items if p.get('id')=='CAB-A' and p['layer']=='JOINERY_ELEVATION')
        self.assertEqual((p['w'],p['h']),(2600,2450))
    def test_total_dimensions_are_derived(self):
        labels={p['text'] for p in d.plan(AFTER,'dimensions').items if p['kind']=='text' and p['layer']=='DIMENSION'}
        self.assertTrue({'10500','9000'}<=labels);self.assertNotIn('12000',labels)
    def test_joinery_schedule_is_updated(self):
        with tempfile.TemporaryDirectory() as tmp:
            t.schedules(AFTER,tmp)
            with (Path(tmp)/'joinery.csv').open(encoding='utf-8-sig') as stream:rows=list(csv.DictReader(stream))
            row=next(x for x in rows if x['id']=='CAB-A')
            self.assertEqual(float(row['front_width_mm']),2600);self.assertEqual(float(row['height_mm']),2450);self.assertEqual(float(row['projection_m2']),6.37)
    def test_translated_negative_origin(self):
        m=copy.deepcopy(AFTER);dx,dy=-15000,3500
        def xy(v):v[0]+=dx;v[1]+=dy
        xy(m['envelope'])
        for p in m['outline']:xy(p)
        for k in ['rooms','furniture','clear_zones','fixtures']:
            for obj in m[k]:xy(obj['rect'])
        for obj in m['rooms']:
            if 'label_xy' in obj:xy(obj['label_xy'])
        walls={w['id']:w for w in m['walls']}
        for w in m['walls']:
            axis_shift=dx if w['axis']=='x' else dy;w['start']+=axis_shift;w['end']+=axis_shift;w['at']+=dy if w['axis']=='x' else dx
        for o in m['openings']:o['start']+=dx if walls[o['wall']]['axis']=='x' else dy
        for k in ['lights','equipment','points']:
            for obj in m[k]:
                if 'xy' in obj:xy(obj['xy'])
        self.assertTrue(t.check(m)['passed']);self.assertEqual(t.totals(m),t.totals(AFTER))
        s=d.plan(m,'dimensions');self.assertLess(d.scene_bounds(s)[0],-14000)
    def test_update_refuses_unknown_installed_content(self):
        with tempfile.TemporaryDirectory() as tmp:
            target=Path(tmp)/'skills';target.mkdir();(target/'interior-review').mkdir();(target/'interior-review/foreign.txt').write_text('unowned')
            result=subprocess.run([sys.executable,str(ROOT/'install.py'),'--target',str(target),'--update-from',str(ROOT)],capture_output=True)
            self.assertNotEqual(result.returncode,0);self.assertEqual((target/'interior-review/foreign.txt').read_text(),'unowned');self.assertEqual(len(list(target.iterdir())),1)
    def test_known_update_preserves_backup(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);baseline=root/'baseline';shutil.copytree(ROOT/'skills',baseline/'skills',ignore=shutil.ignore_patterns('__pycache__','*.pyc'))
            old=baseline/'skills/interior-review/SKILL.md';old.write_text(old.read_text(encoding='utf-8')+'\nOld known version.\n',encoding='utf-8')
            target=root/'installed';shutil.copytree(baseline/'skills',target)
            result=subprocess.run([sys.executable,str(ROOT/'install.py'),'--target',str(target),'--update-from',str(baseline)],capture_output=True)
            self.assertEqual(result.returncode,0,result.stderr);self.assertEqual((target/'interior-review/SKILL.md').read_bytes(),(ROOT/'skills/interior-review/SKILL.md').read_bytes())
            saved=list((root/'interior-skill-backups').glob('*/interior-review/SKILL.md'));self.assertEqual(len(saved),1);self.assertEqual(saved[0].read_bytes(),old.read_bytes())
    def test_fixture_room_is_validated(self):self.reject(lambda m:m['fixtures'][0].__setitem__('room','MISSING'),'ROOM_REF')
    def test_old_model_exports_through_new_drawing_engine(self):
        old=t.load(ROOT/'projects/DEMO-APT-096/model/project.json');doc=d.dxf_document(old);audit=doc.audit()
        self.assertFalse(audit.errors);self.assertFalse(audit.fixes);self.assertEqual(doc.units,4)
        ms=doc.modelspace();self.assertEqual(len(ms.query('LWPOLYLINE[layer=="ID-01_FLOOR"]')),7)
        furniture={e.get_xdata('INTERIOR')[0].value:list(e.get_points('xy')) for e in ms.query('LWPOLYLINE[layer=="ID-01_FURNITURE"]')}
        self.assertEqual(len(furniture),30)
        for f in old['furniture']:
            xs=[p[0] for p in furniture[f['id']]];ys=[p[1] for p in furniture[f['id']]]
            self.assertEqual([min(xs),min(ys),max(xs)-min(xs),max(ys)-min(ys)],f['rect'])

if __name__=='__main__':unittest.main(verbosity=2)
