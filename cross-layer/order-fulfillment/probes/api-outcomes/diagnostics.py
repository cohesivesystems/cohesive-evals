#!/usr/bin/env python3
"""Separate compile/registration witnesses from running-defect qualification."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import build
sys.path.insert(0,str(build.ROOT.parent/'portable-validation/pv1'))
from runtime import verification_run
runtime=build.load('ao1_diagnostic_runtime',build.ROOT/'verify.py')

def cases(condition):
    if condition=='conventional':
        return {
            'wrong-identity-type': ('compile','error CS1503:', [('FulfillmentBackend.cs','await store.Submit(id) switch','await store.Submit(42) switch')]),
            'wrong-input-type': ('compile','error CS1503:', [('FulfillmentBackend.cs','QuantityLimitInput.Get(context).MaxPerOrder','"wrong"')]),
        }
    if condition!='cohesive': raise ValueError(condition)
    return {
        'wrong-input-type':('compile','error CS0029:', [('FulfillmentBackend.cs','.Input(context => QuantityLimitInput.Get(context.HttpContext))','.Input(context => new StockQuantity(1))')]),
        'wrong-transition-reference':('registration','System.ArgumentException: Endpoint must reference the exact authored transition.',[
            ('FulfillmentBackend.cs','.Transition(domain.InventoryTransitions.SetLimit.Reference)','.Transition(domain.InventoryTransitions.SetQuarantine.Reference)')]),
        'wrong-response-contract':('registration','System.ArgumentException: Endpoint entity, kind, primary result, response type or body contract does not match the typed binding.',[
            ('FulfillmentBackend.cs','.Returns<InventoryView>()','.Returns<OrderSummary>()')]),
        'missing-input-binding':('registration','System.InvalidOperationException: Configure Input before completing the binding.',[
            ('FulfillmentBackend.cs','.Input(context => QuantityLimitInput.Get(context.HttpContext))','')]),
    }

def compile_detected(error, log, diagnostic):
    return isinstance(error, subprocess.CalledProcessError) and error.cmd[:2]==['dotnet','build'] and any(
        'FulfillmentBackend.cs(' in line and diagnostic in line for line in log.splitlines())

def registration_detected(error, log, diagnostic):
    return isinstance(error, RuntimeError) and 'host exited' in str(error) and diagnostic in log

def run(output):
    refs=build.materialize(output/'references')
    records=[]
    with verification_run(output/'execution','ao1-diagnostics',runtime.checks.BehavioralFailure) as session:
        for condition in build.harness.CONDITIONS:
            session.condition=condition
            folder=refs/condition
            # Same build, setup, database and registration path must succeed before fault injection.
            with (folder/'control-build.log').open('w') as log: build.build_tools.build_candidate(folder,log)
            world=runtime.pv1.World(folder,output/condition/'control',session.container,session.port,condition,runtime.checks.fixture())
            world.close()
            for name,(stage,diagnostic,edits) in cases(condition).items():
                out=output/condition/name;out.mkdir(parents=True)
                originals={}
                try:
                    for file,before,after in edits:
                        path=folder/'src/Fulfillment.Application'/file
                        original=path.read_text();originals.setdefault(path,original)
                        if original.count(before)!=1: raise ValueError(('anchor',name,file))
                        path.write_text(original.replace(before,after))
                    inputs=build.build_tools.input_hashes(folder)
                    (out/'inputs.json').write_text(json.dumps(inputs,indent=2)+'\n')
                    build_error=None
                    try:
                        with (out/'build.log').open('w') as log: build.build_tools.build_candidate(folder,log)
                    except subprocess.CalledProcessError as error: build_error=error
                    if stage=='compile':
                        text=(out/'build.log').read_text()
                        passed=compile_detected(build_error,text,diagnostic)
                    else:
                        if build_error: raise build_error
                        (out/'build-manifest.json').write_bytes((folder/'build-manifest.json').read_bytes())
                        startup_error=None
                        try:
                            world=runtime.pv1.World(folder,out/'host',session.container,session.port,condition,runtime.checks.fixture())
                            world.close()
                        except RuntimeError as error: startup_error=error
                        text=(out/'host/host.log').read_text()
                        passed=registration_detected(startup_error,text,diagnostic)
                        build.build_tools.verify_build(folder)
                    records.append(dict(condition=condition,case=name,stage=stage,passed=passed,
                        diagnostic=diagnostic,diagnosticLines=[line for line in text.splitlines() if diagnostic in line],
                        inputsSha256=hashlib.sha256((out/'inputs.json').read_bytes()).hexdigest()))
                    (output/'report.json').write_text(json.dumps({'passed':all(r['passed'] for r in records),'complete':len(records)==sum(len(cases(c)) for c in build.harness.CONDITIONS),'cases':records},indent=2)+'\n')
                    if not passed: raise RuntimeError(('expected diagnostic absent',condition,name))
                    print(condition,name,stage,'detected',flush=True)
                finally:
                    for path,original in originals.items():path.write_text(original)

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args();output=args.output.resolve();output.mkdir(parents=True,exist_ok=False)
    run(output)
