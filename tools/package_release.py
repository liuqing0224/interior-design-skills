#!/usr/bin/env python3
"""Versioned local delivery, byte manifests and ZIP readback. No external publish."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import urllib.parse
import zipfile

ROOT=Path(__file__).resolve().parents[1]

def digest(path):return hashlib.sha256(path.read_bytes()).hexdigest()

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--out',type=Path,required=True);a=parser.parse_args();out=a.out.resolve()
    dest=out/'interior-skills-v2';archive=out/'室内设计15Skills_v2_跨户型复用完整包.zip'
    if dest.exists() or archive.exists():raise SystemExit('Refusing to replace an existing versioned release')
    out.mkdir(parents=True,exist_ok=True);dest.mkdir()
    files=[]
    for source in sorted(ROOT.rglob('*')):
        rel=source.relative_to(ROOT)
        if any(part in {'.venv','node_modules','__pycache__','.git'} for part in rel.parts):continue
        if not source.is_file() or source.suffix in {'.pyc','.blend1'} or source.name.endswith('.inspect.ndjson'):continue
        if source.name=='PACKAGE-MANIFEST.json':continue
        target=dest/rel;target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(source,target);files.append(rel)
    viewer='http://127.0.0.1:4178/?'+urllib.parse.urlencode({'dir':str(dest),'file':'projects/TEST-L-084/drawings/interior-set.dxf'})
    (dest/'DELIVERY.md').write_text('# v2交付入口\n\n15个Skills及两个案例。新84㎡L形案例是二维跨户型测试；原96㎡完整示范保留。\n\n'
        '- [复用与价值验证](docs/复用升级与价值验证.md)\n'
        '- [8页图集](projects/TEST-L-084/documents/折庭_图集.pdf)\n'
        '- [预算工作簿](projects/TEST-L-084/schedules/折庭_预算.xlsx)\n'
        '- [DXF图纸](projects/TEST-L-084/drawings/interior-set.dxf)\n'
        '- [验证报告](VALIDATION.md)\n\n'
        f'[CAD Viewer 本地查看]({viewer})\n\n'
        '原15阶段按v1技能快照保留；新测试执行5个实际阶段。46项行为测试、15个技能格式和安装一致性通过。\n',encoding='utf-8')
    rows=[{'path':str(p.relative_to(dest)),'bytes':p.stat().st_size,'sha256':digest(p)} for p in sorted(dest.rglob('*')) if p.is_file()]
    (dest/'PACKAGE-MANIFEST.json').write_text(json.dumps({'release':'v2','files':rows},ensure_ascii=False,indent=2)+'\n')
    with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED) as z:
        for p in sorted(dest.rglob('*')):
            if p.is_file():z.write(p,str(Path(dest.name)/p.relative_to(dest)))
    with zipfile.ZipFile(archive) as z:
        if z.testzip() is not None:raise ValueError('ZIP CRC check failed')
        for row in rows:
            if hashlib.sha256(z.read(dest.name+'/'+row['path'])).hexdigest()!=row['sha256']:raise ValueError('ZIP member hash differs')
    for project_manifest in (dest/'projects').glob('*/state/delivery-manifest.json'):
        project=project_manifest.parent.parent
        for row in json.loads(project_manifest.read_text())['files']:
            member=project/row['path']
            if not member.is_file() or digest(member)!=row['sha256']:raise ValueError('Project manifest dependency missing/different: '+str(member))
    for original,name in [('documents/折庭_图集.pdf','折庭_v1.1_图集.pdf'),('schedules/折庭_预算.xlsx','折庭_v1.1_预算.xlsx')]:
        source=ROOT/'projects/TEST-L-084'/original;target=out/name
        if target.exists():raise ValueError('Standalone output already exists: '+name)
        shutil.copyfile(source,target)
        if digest(source)!=digest(target):raise ValueError('Standalone copy differs')
    report=out/'室内设计Skills_v2_复用与价值验证.md';shutil.copyfile(ROOT/'docs/复用升级与价值验证.md',report)
    result={'passed':True,'release':'v2','directory':str(dest),'archive':str(archive),'files':len(rows)+1,'archive_bytes':archive.stat().st_size,'archive_sha256':digest(archive),'member_hashes_verified':len(rows),'viewer_url':viewer}
    (out/'室内设计Skills_v2_交付核验.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(result,ensure_ascii=False,indent=2))

if __name__=='__main__':main()
