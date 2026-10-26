#!/usr/bin/env python3
"""Verify real exported before/after files for the synthetic cabinet change."""
import copy
from decimal import Decimal
import importlib.util
import json
from pathlib import Path
import shutil
import tempfile

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('verify2d',ROOT/'skills/interior-review/scripts/verify_2d.py')
v=importlib.util.module_from_spec(spec);spec.loader.exec_module(v)
t=v.t

def main():
    p=ROOT/'projects/TEST-L-084';previous=p/'history/v1.0'
    before=v.verify(previous);after=v.verify(p)
    old=t.load(previous/'model/project.json');new=t.load(p/'model/project.json')
    delta=new.copy();delta['revision']=old['revision'];delta['furniture']=copy.deepcopy(new['furniture'])
    next(f for f in delta['furniture'] if f['id']=='CAB-A').update(copy.deepcopy(next(f for f in old['furniture'] if f['id']=='CAB-A')))
    v.require(delta==old,'Changes extend beyond the named cabinet and revision')
    oldrows,oldbudget=v.independent_budget(old);newrows,newbudget=v.independent_budget(new)
    changes=[(a,b) for a,b in zip(oldrows,newrows) if a!=b]
    v.require(len(changes)==1 and changes[0][0][0]=='Q-CAB-A','Unexpected budget row changes')
    v.require(changes[0][0][1]==Decimal('4.84') and changes[0][1][1]==Decimal('6.37'),'Projection quantity differs')
    v.require(newbudget['total']-oldbudget['total']==Decimal('1767.15'),'Total change differs')
    files=['drawings/ID-01.svg','drawings/ID-06.svg','drawings/interior-set.dxf','schedules/furniture.csv','schedules/joinery.csv','schedules/budget.csv','schedules/折庭_预算.xlsx','documents/折庭_图集.pdf']
    v.require(all(t.sha(previous/f)!=t.sha(p/f) for f in files),'A dependent output did not update')
    v.require((previous/'schedules/rooms.csv').read_bytes()==(p/'schedules/rooms.csv').read_bytes(),'Unchanged room areas drifted')
    with tempfile.TemporaryDirectory(prefix='interior-stale-test-') as tmp:
        test=Path(tmp)/'test';shutil.copytree(p,test,ignore=shutil.ignore_patterns('history','__pycache__'))
        stale=t.load(test/'model/project.json');stale['revision']='unexported';t.dump(test/'model/project.json',stale)
        try:v.verify(test)
        except ValueError as exc:v.require('Stale drawing input' in str(exc),'Unexpected stale-input response')
        else:raise ValueError('Stale input accepted')
    result=dict(passed=True,test_kind='synthetic_transfer_and_change',object_id='CAB-A',
        before=before,after=after,projection_m2={'before':4.84,'after':6.37},
        amount_change_cny=1606.5,reserve_change_cny=160.65,total_change_cny=1767.15,
        dependent_files_changed=files,unaffected_rooms_unchanged=True,stale_input_rejected=True)
    t.dump(p/'state/change-verification.json',result)
    print(json.dumps({k:result[k] for k in ['passed','projection_m2','total_change_cny','stale_input_rejected']},ensure_ascii=False))

if __name__=='__main__':main()
