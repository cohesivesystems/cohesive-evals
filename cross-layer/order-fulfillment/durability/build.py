#!/usr/bin/env python3
"""Materialize maintainer-only reference solutions without altering participant G0."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess

ROOT=Path(__file__).resolve().parent

def input_hashes(folder):
    paths=[p for p in folder.rglob('*') if p.is_file() and not {'bin','obj','__pycache__'}.intersection(p.relative_to(folder).parts)
           and (p.suffix in ['.cs','.csproj','.props','.targets','.nupkg'] or p.name in ['global.json','NuGet.config','packages.lock.json'])]
    return {str(p.relative_to(folder)):hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(paths)}


def artifact_hashes(folder):
    output=folder/'src/Fulfillment.Application/bin/Debug/net10.0'
    return {str(p.relative_to(folder)):hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(output.rglob('*')) if p.is_file()}


def reference_fingerprint(folder):
    return hashlib.sha256(json.dumps(input_hashes(folder),sort_keys=True).encode()).hexdigest()


def build_candidate(folder, log=None):
    manifest=folder/'build-manifest.json'
    manifest.unlink(missing_ok=True)
    before=input_hashes(folder)
    subprocess.run(['dotnet','restore','--locked-mode'],cwd=folder,stdout=log,stderr=log,check=True,timeout=120)
    subprocess.run(['dotnet','build','--no-restore','--no-incremental','-m:1','-nr:false'],cwd=folder,stdout=log,stderr=log,check=True,timeout=120)
    assert before==input_hashes(folder), 'Inputs changed during build'
    artifacts=artifact_hashes(folder)
    assert any(p.endswith('/Fulfillment.Application.dll') for p in artifacts), 'Application binary missing'
    manifest.write_text(json.dumps({'inputs':before,'artifacts':artifacts,
        'sdk':subprocess.check_output(['dotnet','--version'],cwd=folder,text=True).strip()},indent=2)+'\n')


def verify_build(folder):
    manifest=json.loads((folder/'build-manifest.json').read_text())
    assert manifest['inputs']==input_hashes(folder), 'Source/configuration changed since build'
    assert manifest['artifacts']==artifact_hashes(folder), 'Executable artifacts changed since build'
    assert any(p.endswith('/Fulfillment.Application.dll') for p in manifest['artifacts']), 'Application binary missing'
    return hashlib.sha256((folder/'build-manifest.json').read_bytes()).hexdigest()


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,default=ROOT.parent/'artifacts/durable-reference')
    args=parser.parse_args();args.output=args.output.resolve()
    manifest=json.loads((ROOT/'dependency-manifest.json').read_text())
    for p in manifest['packages']:
        assert hashlib.sha256((ROOT/'packages'/p['file']).read_bytes()).hexdigest()==p['sha256']
    for condition in ['conventional','cohesive']:
        folder=args.output/condition
        if folder.exists(): shutil.rmtree(folder)
        shutil.copytree(ROOT.parent/'conditions'/condition,folder,ignore=shutil.ignore_patterns('bin','obj','__pycache__'))
        app=folder/'src/Fulfillment.Application'
        for overlay in ['common',condition]:
            for p in (ROOT/'reference'/overlay).glob('*'): shutil.copy2(p,app/p.name)
        p=app/'Program.cs';s=p.read_text()
        s=s.replace('builder.Services.AddSingleton<IFulfillmentBackend, FulfillmentBackend>();','builder.Services.AddSingleton<FulfillmentBackend>();\nbuilder.Services.AddSingleton<IFulfillmentBackend>(p => p.GetRequiredService<FulfillmentBackend>());\nbuilder.Services.AddSingleton<IDurableExecution, DurableExecution>();')
        s=s.replace('var app = builder.Build();', 'DurableSetup.Configure(builder.Services);\nvar app = builder.Build();')
        s=s.replace('HostSetup.Configure(app);', 'await app.Services.GetRequiredService<OperationQueue>().Initialize();\nHostSetup.Configure(app);')
        p.write_text(s)
        p=app/'Fulfillment.Application.csproj';s=p.read_text().replace('</Project>', '<ItemGroup><PackageReference Include="Microsoft.DurableTask.Client.AzureManaged" Version="1.25.0" /><PackageReference Include="Microsoft.DurableTask.Worker.AzureManaged" Version="1.25.0" /></ItemGroup></Project>')
        if condition=='cohesive':
            s=s.replace('</Project>','<ItemGroup><PackageReference Include="Cohesive.Adapters.DurableTask" Version="0.1.0-eval.b0af008" /></ItemGroup></Project>')
            for package in (ROOT/'packages').glob('*.nupkg'):shutil.copy2(package,folder/'packages'/package.name)
            b=app/'FulfillmentBackend.cs';t=b.read_text().replace('HostedServiceProcess<FulfillOrder, FulfillmentResult> hosted = null!;', 'public PreparedServiceProcess Prepared { get; private set; } = null!;')
            t=t.replace('hosted = Service.Define','Prepared = Service.Define')
            t=t.replace('.ExecuteEphemerally(TimeSpan.FromSeconds(15))','.ReturnAfterDurableAdmission()')
            t=t.replace('.Bind(process.Definition, orders, inventory, reservations)\n            .Build("fulfillment", new IdentityServiceInvocationAuthorization("demo", new(FulfillmentDomain.PartitionField)))', '.PrepareProcess(process.Definition, contract => new IEntityRepository[] { orders, inventory, reservations }.Single(r => ValueContract.FromShape(r.EntityDefinition.Shape) == contract))')
            start=t.index('    public async Task<Completion> Fulfill(');end=t.index('\n}\n\npublic static class HostSetup',start)
            t=t[:start]+'    public Task<Completion> Fulfill(string operationId, FulfillmentRequest request) => throw new NotSupportedException("Use durable execution.");\n'+t[end:];b.write_text(t)
        p.write_text(s)
        setup='''using Microsoft.DurableTask;
using Microsoft.DurableTask.Client;
using Microsoft.DurableTask.Worker;
using Microsoft.DurableTask.Client.AzureManaged;
using Microsoft.DurableTask.Worker.AzureManaged;
'''
        if condition=='cohesive': setup+='using Cohesive.Adapters.DurableTask;\nusing Cohesive.Processes.Execution;\n'
        setup+='''namespace Fulfillment.Application;
public static class DurableSetup
{
    public static void Configure(IServiceCollection services)
    {
        var connection = Environment.GetEnvironmentVariable("DURABLE_TASK_CONNECTION") ?? throw new InvalidOperationException("Missing scheduler connection.");
'''
        if condition=='cohesive': setup+='''        services.AddSingleton<IAsyncProcessReferenceHost, RecoveryHost>();
        services.AddDurableTaskWorker(worker => {
            worker.AddCohesiveSequentialProcesses(p => new DurableTaskSequentialProcessPlanCatalog([
                DurableTaskProcessRealizationCompiler.CompileExecutable(p.GetRequiredService<FulfillmentBackend>().Prepared.Plan).Plan! ]));
            worker.UseDurableTaskScheduler(connection);
        });
'''
        else: setup+='''        services.AddDurableTaskWorker(worker => {
            worker.AddTasks(tasks => { tasks.AddOrchestrator<FulfillmentWorkflow>(nameof(FulfillmentWorkflow));
                tasks.AddActivity<ReadOrder>(nameof(ReadOrder)); tasks.AddActivity<ReadReservation>(nameof(ReadReservation));
                tasks.AddActivity<ReadInventory>(nameof(ReadInventory)); tasks.AddActivity<ReserveStock>(nameof(ReserveStock));
                tasks.AddActivity<SubmitOrder>(nameof(SubmitOrder)); tasks.AddActivity<CreateReservation>(nameof(CreateReservation));
                tasks.AddActivity<ReleaseStock>(nameof(ReleaseStock)); });
            worker.UseDurableTaskScheduler(connection);
        });
'''
        setup+='''        services.AddDurableTaskClient(client => client.UseDurableTaskScheduler(connection));
    }
}
'''
        (app/'DurableSetup.cs').write_text(setup)
        build_candidate(folder)

if __name__=='__main__':main()
