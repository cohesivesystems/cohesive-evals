#!/usr/bin/env python3
"""Run both standalone fixtures against disposable PostgreSQL and compare public behavior."""
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import socket
import subprocess
import invariants
import time
import uuid
import urllib.request
import urllib.error

ROOT=Path(__file__).resolve().parents[1]
IMAGE='postgres:17.10-alpine3.24'

def run(*args,**kwargs):
 return subprocess.check_output(args,text=True,**kwargs).strip()

def free_port():
 with socket.socket() as listener:
  listener.bind(('127.0.0.1',0));return listener.getsockname()[1]

def main():
 parser=argparse.ArgumentParser(description=__doc__)
 parser.add_argument('--output',type=Path,default=ROOT/'artifacts/verification')
 args=parser.parse_args();args.output.mkdir(parents=True,exist_ok=True)
 (args.output/'report.json').unlink(missing_ok=True)
 for relative in ['src/Fulfillment.Application/Contracts.cs','src/Fulfillment.Application/Program.cs',
                  'src/Fulfillment.Application/OperationQueue.cs','tests/contract_tests.py',
                  'src/Fulfillment.Application/ReadResults.cs','CONTRACT.md','schemas.json','README.md']:
  assert (ROOT/'conditions/conventional'/relative).read_bytes()==(ROOT/'conditions/cohesive'/relative).read_bytes(),relative
 manifest=json.loads((ROOT/'conditions/cohesive/dependency-manifest.json').read_text())
 for package in manifest['packages']:
  path=ROOT/'conditions/cohesive/packages'/package['file']
  assert hashlib.sha256(path.read_bytes()).hexdigest()==package['sha256'],str(path)
 spec=importlib.util.spec_from_file_location('contract_tests',ROOT/'conditions/conventional/tests/contract_tests.py')
 suite=importlib.util.module_from_spec(spec);spec.loader.exec_module(suite)
 name='order-baseline-'+uuid.uuid4().hex[:12]
 image_id=run('docker','image','inspect',IMAGE,'--format','{{.Id}}')
 started=False
 observations={}
 invariant_results={}
 checker_defects=invariants.qualify_checker()
 try:
  run('docker','run','-d','--name',name,'-e','POSTGRES_PASSWORD=fixture-only','-p','127.0.0.1::5432',IMAGE);started=True
  for attempt in range(100):
   status=subprocess.run(['docker','exec',name,'pg_isready','-h','127.0.0.1','-U','postgres'],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
   if status.returncode==0:break
   time.sleep(.1)
  else:raise RuntimeError('PostgreSQL did not become ready')
  address=run('docker','port',name,'5432/tcp');db_port=address.rsplit(':',1)[1]
  for condition in ['conventional','cohesive']:
   run('docker','exec',name,'psql','-U','postgres','-c',f'CREATE DATABASE {condition}')
   folder=ROOT/'conditions'/condition
   executable=folder/'src/Fulfillment.Application/bin/Debug/net10.0/Fulfillment.Application.dll'
   if not executable.exists():raise RuntimeError(f'Build {condition} before verification')
   env=dict(os.environ,ConnectionStrings__Orders=f'Host=127.0.0.1;Port={db_port};Database={condition};Username=postgres;Password=fixture-only;Timeout=10',ASPNETCORE_ENVIRONMENT='Production')
   seed_file=args.output/(condition+'-seed.json');seed_file.write_text(json.dumps({key: suite.SEED[key]+invariants.fixture()[key] for key in suite.SEED}))
   log_path=args.output/(condition+'.log')
   with log_path.open('w') as log:
    subprocess.run(['dotnet',str(executable),'--seed',str(seed_file.resolve())],cwd=folder,
                   env=dict(env,FULFILLMENT_SETUP='1'),stdout=log,stderr=log,check=True,timeout=90)
    port=free_port();url=f'http://127.0.0.1:{port}'
    process=subprocess.Popen(['dotnet',str(executable),'--urls',url],cwd=folder,env=env,stdout=log,stderr=log)
    try:
     for attempt in range(100):
      if process.poll() is not None:raise RuntimeError(f'{condition} exited; see {log_path}')
      try:
       urllib.request.urlopen(url+'/orders/success',timeout=1).close();break
      except (urllib.error.URLError,TimeoutError):time.sleep(.1)
     else:raise RuntimeError(f'{condition} did not become ready; see {log_path}')
     observations[condition]=suite.exercise(url)
     invariant_output=args.output/condition
     invariant_output.mkdir(exist_ok=True)
     invariant_results[condition]=invariants.exercise(suite.Client, url,
         lambda seed: invariants.observe(run, name, condition, seed), invariant_output)
     (args.output/(condition+'-observations.json')).write_text(json.dumps(observations[condition],indent=2)+'\n')
    finally:
     process.terminate()
     try:process.wait(timeout=25)
     except subprocess.TimeoutExpired:process.kill();process.wait()
  assert observations['conventional']==observations['cohesive'],'Public observations differ; compare output JSON'
  assert invariant_results['conventional']==invariant_results['cohesive'], 'Invariant final facts differ'
  report={'passed':True,'checksPerCondition':len(observations['conventional']),
          'invariantSequences':invariant_results['conventional'],
          'invariantCommandsPerCondition':sum(r['commands'] for r in invariant_results['conventional']),
          'checkerSeededDefectsRejected':checker_defects,
          'postgresImage':IMAGE,'postgresImageId':image_id,'sdk':run('dotnet','--version'),
          'cohesiveSourceRevision':manifest['sourceRevision'],
          'limitations':['G0 only','Visible suite plus maintainer invariant checks; full hidden oracle not qualified', 'Sequential settled-state checks only; no crash or concurrency qualification','Independent baseline review pending','No agent runs']}
  (args.output/'report.json').write_text(json.dumps(report,indent=2)+'\n')
  print(json.dumps(report,indent=2))
 finally:
  if started:subprocess.run(['docker','rm','-f',name],stdout=subprocess.DEVNULL,check=True)

if __name__=='__main__':main()
