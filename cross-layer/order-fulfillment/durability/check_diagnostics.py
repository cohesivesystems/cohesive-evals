#!/usr/bin/env python3
"""Check result/binding diagnostics and fail-fast worker registration in isolated builds."""
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
from build import build_candidate, verify_build

ROOT = Path(__file__).resolve().parent

def main():
    references = ROOT.parent/'artifacts/durable-reference'
    verified = verify_build(references/'cohesive')
    output = ROOT.parent/'artifacts/durability-diagnostics'
    output.mkdir(parents=True, exist_ok=True)
    (output/'report.json').unlink(missing_ok=True)
    with tempfile.TemporaryDirectory(prefix='order-diagnostics-') as temp:
        root = Path(temp)
        probe = root/'probe'; probe.mkdir()
        binaries = references/'cohesive/src/Fulfillment.Application/bin/Debug/net10.0'
        (probe/'Probe.csproj').write_text(f'''<Project Sdk="Microsoft.NET.Sdk"><PropertyGroup><OutputType>Exe</OutputType><TargetFramework>net10.0</TargetFramework><ImplicitUsings>enable</ImplicitUsings><Nullable>enable</Nullable><NuGetAudit>false</NuGetAudit></PropertyGroup><ItemGroup><FrameworkReference Include="Microsoft.AspNetCore.App"/><Reference Include="{binaries}/*.dll"/></ItemGroup></Project>''')
        shutil.copy2(ROOT/'tests/Diagnostics.cs', probe/'Program.cs')
        with (output/'mapper-bindings.log').open('w') as log:
            subprocess.run(['dotnet','run','--project',str(probe/'Probe.csproj')],stdout=log,stderr=log,check=True,timeout=120)
        candidates=root/'references'
        shutil.copytree(references/'cohesive',candidates/'cohesive',ignore=shutil.ignore_patterns('bin','obj'))
        app=candidates/'cohesive/src/Fulfillment.Application'
        # Invoke the pinned compiler's private profile overload solely to supply a
        # deliberately unsupported target and exercise the real diagnostic report.
        unsupported='''(DurableTaskProcessPlanningResult)typeof(DurableTaskProcessRealizationCompiler)
                    .GetMethod("Compile", System.Reflection.BindingFlags.NonPublic | System.Reflection.BindingFlags.Static)!
                    .Invoke(null, [plan, new Cohesive.Processes.Compilation.ProcessInterpreterCapabilityProfile(
                        new("test/empty"), DurableTaskProcessTargetProfile.Executable.Target, [])])!'''
        cases=[
            ('missing-repository','FulfillmentBackend.cs','RepositoryBindings.Resolve(orders, inventory, reservations)','RepositoryBindings.Resolve(orders, inventory)','services.binding.repositoryMissing'),
            ('ambiguous-repository','FulfillmentBackend.cs','RepositoryBindings.Resolve(orders, inventory, reservations)','RepositoryBindings.Resolve(orders, inventory, reservations, orders)','services.binding.repositoryAmbiguous'),
            ('unsupported-realization','DurableSetup.cs','DurableTaskProcessRealizationCompiler.CompileExecutable(plan)',unsupported,'Durable process realization failed: processes.interpreter.realization.'),
            ('renamed-barrier','RecoveryHost.cs','["fulfillment/reserve"] = "reserve"','["fulfillment/renamed"] = "reserve"','Recovery barrier transitions differ:')]
        for name,file,before,after,expected in cases:
            path=app/file; original=path.read_text(); assert original.count(before)==1
            evidence=output/name;evidence.mkdir(exist_ok=True)
            try:
                path.write_text(original.replace(before,after))
                with (evidence/'build.log').open('w') as log: build_candidate(candidates/'cohesive',log)
                with (evidence/'verify.log').open('w') as log:
                    result=subprocess.run([sys.executable,'-B',str(ROOT/'verify.py'),'--condition','cohesive','--point','none','--references',str(candidates),'--output',str(evidence)],stdout=log,stderr=log,timeout=120)
                host=(evidence/'cohesive/none/host.log').read_text()
                assert result.returncode and expected in host, (name,'Expected startup diagnostic missing',host[-3000:])
                print(name,'diagnostic passed',flush=True)
            finally: path.write_text(original)
    assert verified==verify_build(references/'cohesive')
    (output/'report.json').write_text(json.dumps({'passed':True,'mapperAndBindingChecks':5,'startupDiagnostics':[c[0] for c in cases],'buildManifest':verified},indent=2)+'\n')

if __name__=='__main__':main()
