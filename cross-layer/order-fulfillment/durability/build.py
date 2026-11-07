#!/usr/bin/env python3
"""Materialize maintainer-only reference solutions without altering participant G0."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess

ROOT=Path(__file__).resolve().parent

def reference_fingerprint(folder):
    digest=hashlib.sha256()
    for path in sorted((folder/'src/Fulfillment.Application').iterdir()):
        if path.is_file() and (path.suffix in ['.cs','.csproj'] or path.name=='packages.lock.json'):
            digest.update(path.name.encode()+b'\0'+path.read_bytes())
    return digest.hexdigest()


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
            worker.AddTasks(tasks => { tasks.AddOrchestrator<FulfillmentWorkflow>("Fulfillment"); tasks.AddActivity<FulfillmentStep>("FulfillmentStep"); });
            worker.UseDurableTaskScheduler(connection);
        });
'''
        setup+='''        services.AddDurableTaskClient(client => client.UseDurableTaskScheduler(connection));
    }
}
'''
        (app/'DurableSetup.cs').write_text(setup)
        subprocess.run(['dotnet','restore','--locked-mode'],cwd=folder,check=True)
        subprocess.run(['dotnet','build','--no-restore','-m:1','-nr:false'],cwd=folder,check=True)

if __name__=='__main__':main()
