#!/usr/bin/env python3
"""Capability witness only: reuse AO1 production sources with independent example expectations."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT.parents[1] / 'api-outcomes'))
import build

# Maintainer audit examples, not generated cases or the held-out MV1 defect suite.
EXAMPLES = [
    ('zero',10,4,True,0,'InvalidQuantity',10),
    ('negative',10,4,False,-1,'InvalidQuantity',10),
    ('quarantine',0,1,True,2,'InventoryQuarantined',0),
    ('limit',0,1,False,2,'QuantityLimitExceeded',0),
    ('short',1,4,False,2,'InsufficientStock',1),
    ('exact-limit',10,4,False,4,'Reserved',6),
    ('exact-stock',4,10,False,4,'Reserved',0),
    ('valid',10,4,False,2,'Reserved',8),
    ('int-max',2147483647,2147483647,False,2147483647,'Reserved',0),
    ('int-min',10,4,False,-2147483648,'InvalidQuantity',10),
]

def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()

def validate_rows(rows):
    expected=[dict(Name=n,Outcome=o,After=after,Unchanged=o!='Reserved') for n,_,_,_,_,o,after in EXAMPLES]
    observed=[{k:r[k] for k in expected[0]} for r in rows]
    if observed!=expected:raise AssertionError(('independent outcomes',observed))

def run(output, prepare_locks=False):
    output.mkdir(parents=True,exist_ok=False)
    refs=build.materialize(output/'references')
    audit=output/'audit';audit.mkdir()
    for name in ('Input.cs','packages'):
        source=ROOT/name
        if source.is_dir():shutil.copytree(source,audit/name)
        else:shutil.copy2(source,audit/name)
    manifest=json.loads((ROOT/'package-manifest.json').read_text())
    for name,want in manifest['packages'].items():
        if sha(audit/'packages'/name)!=want:raise ValueError('Audit package drift: '+name)
    shutil.copy2(refs/'cohesive/global.json',audit/'global.json')
    config=ET.Element('configuration');sources=ET.SubElement(config,'packageSources');ET.SubElement(sources,'clear')
    for key,value in [('production',str(refs/'cohesive/packages')),('audit',str(audit/'packages')),('public','https://api.nuget.org/v3/index.json')]:
        ET.SubElement(sources,'add',key=key,value=value)
    mapping=ET.SubElement(config,'packageSourceMapping')
    for key,pattern in [('production','Cohesive*'),('audit','Cohesive*'),('public','*')]:
        ET.SubElement(ET.SubElement(mapping,'packageSource',key=key),'package',pattern=pattern)
    ET.ElementTree(config).write(audit/'NuGet.config',encoding='unicode')
    inputs=[dict(Name=n,Available=a,MaxPerOrder=m,Quarantined=q,Quantity=v) for n,a,m,q,v,_,_ in EXAMPLES]
    (audit/'inputs.json').write_text(json.dumps(inputs,indent=2)+'\n')
    records={};provenance={}
    for condition in build.harness.CONDITIONS:
        folder=audit/condition;shutil.copytree(ROOT/condition,folder)
        before=build.build_tools.input_hashes(refs/condition)
        args=['-p:FixtureRoot='+str(refs)]
        with (output/(condition+'-build.log')).open('w') as log:
            subprocess.run(['dotnet','restore','Audit.csproj','--configfile',str(audit/'NuGet.config'),*args,
                *([] if prepare_locks else ['--locked-mode'])],cwd=folder,stdout=log,stderr=log,check=True,timeout=180)
            subprocess.run(['dotnet','build','Audit.csproj','--no-restore','-m:1','-nr:false',*args],cwd=folder,stdout=log,stderr=log,check=True,timeout=180)
        if before!=build.build_tools.input_hashes(refs/condition):raise ValueError('Production source drift')
        if prepare_locks:shutil.copy2(folder/'packages.lock.json',ROOT/condition/'packages.lock.json')
        result=subprocess.run(['dotnet',str(folder/'bin/Debug/net10.0/Audit.dll'),str(audit/'inputs.json'),str(output/'transition.json')],cwd=folder,text=True,capture_output=True,timeout=60)
        (output/(condition+'.json')).write_text(result.stdout)
        (output/(condition+'-stderr.log')).write_text(result.stderr)
        result.check_returncode()
        row=json.loads(result.stdout)
        validate_rows(row['rows'])
        records[condition]=row
        provenance[condition]={'applicationInputs':before,'auditArtifacts':{str(p.relative_to(folder)):sha(p) for p in sorted((folder/'bin').rglob('*')) if p.is_file()},
            'lockSha256':sha(folder/'packages.lock.json')}
    cohesive=records['cohesive']
    if cohesive['guardCount']!=4 or cohesive['admissionDiagnostic'] != "Admission 'fulfillment/reserve/body/auto/requires/1' uses unsupported expression 'ParameterExpr'." or cohesive['negativeVerdict']!='Violated':
        raise AssertionError(('capability control',cohesive))
    if cohesive['finiteOrderControl'] != {'verdict':'Satisfied','nonVacuity':'Satisfied','Visited':4,'EnumerationComplete':True}:
        raise AssertionError(('state-only finite control',cohesive['finiteOrderControl']))
    if 'authoring.expression.operatorUnsupported' not in cohesive['typedArithmetic'] or "'Subtract'" not in cohesive['typedArithmetic']:
        raise AssertionError(('typed arithmetic support changed',cohesive['typedArithmetic']))
    for row in cohesive['rows']:
        if row['Assurance']!=('Satisfied' if row['Outcome']=='Reserved' else 'not-evaluated-rejection'):raise AssertionError(row)
    report={'passed':True,'purpose':'Capability audit; no generated suite or held-out defect qualification',
        'sdkRevision':manifest['sdkRevision'],'casesPerCondition':len(EXAMPLES),'conditions':records,
        'provenance':provenance,'auditSourceSha256':{str(p.relative_to(ROOT)):sha(p) for p in sorted(ROOT.rglob('*')) if p.is_file() and '__pycache__' not in p.parts}}
    (output/'report.json').write_text(json.dumps(report,indent=2)+'\n')
    print('MV1 capability audit passed:',len(EXAMPLES),'examples per condition')

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--prepare-locks',action='store_true',help='Maintainer bootstrap only; normal reproduction uses locked restore')
    args=parser.parse_args()
    run(args.output.resolve(),args.prepare_locks)
