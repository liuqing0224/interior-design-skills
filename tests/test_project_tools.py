#!/usr/bin/env python3
import copy
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

R=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('tools',R/'skills/interior-orchestrator/scripts/project_tools.py')
t=importlib.util.module_from_spec(spec);spec.loader.exec_module(t)
MODEL=t.load(R/'projects/DEMO-APT-096/model/project.json')

class ProjectTests(unittest.TestCase):
    def mutate(self,fn,code):
        m=copy.deepcopy(MODEL);fn(m);r=t.check(m)
        self.assertFalse(r['passed']);self.assertIn(code,{i['code'] for i in r['issues']})
    def test_final_design(self):self.assertTrue(t.check(MODEL)['passed'])
    def test_historical_issues_are_observable(self):
        m=t.load(R/'projects/DEMO-APT-096/history/v0.1/project.json')
        self.assertEqual({x['code'] for x in t.check(m)['issues']},{'CLEARANCE','POINT_ACCESS'})
    def test_room_overlap(self):self.mutate(lambda m:m['rooms'][1]['rect'].__setitem__(0,8990),'ROOM_OVERLAP')
    def test_furniture_collision(self):self.mutate(lambda m:m['furniture'][1].__setitem__('rect',m['furniture'][0]['rect'][:]),'FURNITURE_COLLISION')
    def test_corridor_block(self):self.mutate(lambda m:m['furniture'][0].__setitem__('rect',[1000,3350,900,500]),'CLEAR_ZONE')
    def test_duplicate_id(self):self.mutate(lambda m:m['materials'][1].__setitem__('id','M01'),'DUPLICATE')
    def test_unknown_material(self):self.mutate(lambda m:m['rooms'][0].__setitem__('floor','MISSING'),'MATERIAL')
    def test_unknown_light_group(self):self.mutate(lambda m:m['lights'][0].__setitem__('group','G99'),'LIGHT_GROUP')
    def test_device_reference(self):self.mutate(lambda m:m['equipment'][0].__setitem__('object','F99'),'OBJECT_REF')
    def test_point_outside_room(self):self.mutate(lambda m:m['points'][0].__setitem__('xy',[-200,0]),'POSITION')
    def test_opening_exceeds_wall(self):self.mutate(lambda m:m['openings'][0].__setitem__('width',9000),'OPENING')
    def test_missing_budget_input(self):self.mutate(lambda m:m['budget'][0].__setitem__('rate',None),'BUDGET_INPUT')
    def test_budget_overrun(self):self.mutate(lambda m:m.__setitem__('budget_cny',1000),'BUDGET')
    def test_wrong_units(self):self.mutate(lambda m:m.__setitem__('units','m'),'UNITS')
    def test_invalid_dimension(self):self.mutate(lambda m:m['rooms'][0]['rect'].__setitem__(2,float('nan')),'GEOMETRY')
    def test_zero_rate_is_valid(self):
        m=copy.deepcopy(MODEL);m['budget'][0]['rate']=0
        self.assertTrue(t.check(m)['passed']);self.assertLess(t.totals(m)['total'],t.totals(MODEL)['total'])
    def test_quantity_updates_from_geometry(self):
        m=copy.deepcopy(MODEL);old=t.budget_rows(m)[0]['quantity'];m['rooms'][0]['rect'][2]-=1000
        self.assertAlmostEqual(old-t.budget_rows(m)[0]['quantity'],3.32)
    def test_half_up_quantity_and_line_amount(self):
        m=copy.deepcopy(MODEL)
        m['budget']=[{'id':'ROUND','quantity':1.23445,'waste':0,'rate':100}]
        row=t.budget_rows(m)[0]
        self.assertEqual(row['quantity'],1.2345)
        self.assertEqual(row['amount'],123.45)
    def test_half_cent_reserve_rounds_up(self):
        m=copy.deepcopy(MODEL)
        m['budget']=[{'id':'ROUND','quantity':1,'waste':0,'rate':1.25}]
        m['reserve_rate']=.1
        self.assertEqual(t.totals(m)['reserve'],.13)
        self.assertEqual(t.totals(m)['total'],1.38)
    def test_record_rejects_escape(self):
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaises(ValueError):t.record(d,R/'skills/interior-brief',['../outside.md'])
    def test_init_rejects_existing(self):
        with tempfile.TemporaryDirectory() as d:
            result=subprocess.run([sys.executable,str(R/'skills/interior-orchestrator/scripts/project_tools.py'),'init',d,'--name','test'],capture_output=True)
            self.assertNotEqual(result.returncode,0)
    def test_installer_preflight_no_partial_write(self):
        with tempfile.TemporaryDirectory() as d:
            existing=Path(d)/'interior-review';existing.mkdir();(existing/'keep.txt').write_text('keep')
            result=subprocess.run([sys.executable,str(R/'install.py'),'--target',d],capture_output=True)
            self.assertNotEqual(result.returncode,0);self.assertEqual([p.name for p in Path(d).iterdir()],['interior-review']);self.assertEqual((existing/'keep.txt').read_text(),'keep')

if __name__=='__main__':unittest.main(verbosity=2)
