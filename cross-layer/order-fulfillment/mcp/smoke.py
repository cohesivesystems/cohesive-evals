#!/usr/bin/env python3
"""Unscored real-stdio integration exercise; never invokes a model or hidden scorer."""
import argparse
import json
from pathlib import Path
import queue
import shutil
import subprocess
import threading
import time
import prepare


class Session:
    def __init__(self, command, workspace, evidence):
        self.trace = (evidence/'mcp.jsonl').open('x')
        self.stderr = (evidence/'server.stderr').open('x')
        self.process = subprocess.Popen(command, cwd=workspace, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                        stderr=self.stderr, text=True)
        self.sequence = 0
        self.messages = queue.Queue()
        def read():
            try:
                for line in self.process.stdout:
                    self.messages.put(json.loads(line))
            except Exception as error:
                self.messages.put(error)
            finally:
                self.messages.put(EOFError('MCP stdout closed'))
        self.reader = threading.Thread(target=read, daemon=True)
        self.reader.start()

    def record(self, direction, message):
        self.trace.write(json.dumps({'time':prepare.runner.utc_now(),'direction':direction,'message':message})+'\n')
        self.trace.flush()

    def request(self, method, params, timeout=60):
        self.sequence += 1
        message = {'jsonrpc':'2.0','id':self.sequence,'method':method,'params':params}
        self.record('request', message)
        started = time.monotonic()
        self.process.stdin.write(json.dumps(message)+'\n'); self.process.stdin.flush()
        while True:
            remaining = timeout - (time.monotonic() - started)
            if remaining <= 0:
                raise queue.Empty('MCP request timed out')
            response = self.messages.get(timeout=remaining)
            if isinstance(response, Exception): raise response
            self.record('response', response)
            if response.get('id') == self.sequence:
                if 'error' in response: raise RuntimeError(response)
                self.record('latency', {'method':method,'seconds':time.monotonic()-started})
                return response['result']

    def initialize(self):
        result = self.request('initialize', {'protocolVersion':'2025-03-26','capabilities':{},
            'clientInfo':{'name':'fulfillment-integration-smoke','version':'1'}})
        notice = {'jsonrpc':'2.0','method':'notifications/initialized'}
        self.record('notification', notice)
        self.process.stdin.write(json.dumps(notice)+'\n'); self.process.stdin.flush()
        return result

    def call(self, name, arguments=None, expect_error=False):
        result = self.request('tools/call', {'name':name,'arguments':arguments or {}})
        if bool(result.get('isError')) != expect_error: raise RuntimeError(result)
        return result if expect_error else result['structuredContent']

    def close(self):
        self.process.stdin.close()
        try:
            self.process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            self.process.terminate()
            try: self.process.wait(timeout=10)
            except subprocess.TimeoutExpired: self.process.kill(); self.process.wait(timeout=10)
        self.reader.join(timeout=2)
        self.process.stdout.close()
        self.trace.close(); self.stderr.close()
        return self.process.returncode


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('preparation', type=Path)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    preparation = args.preparation.resolve()
    if json.loads((preparation/'preparation.json').read_text())['status'] != 'prepared':
        raise ValueError('Only a successful preparation can be exercised')
    evidence = args.output.resolve(); evidence.mkdir(parents=True, exist_ok=False)
    seed = preparation/'cohesive-mcp'
    expected_manifest = json.loads((preparation/'evidence/participant-manifest.json').read_text())
    if prepare.runner.manifest(seed) != expected_manifest:
        raise ValueError('Prepared participant files changed')
    workspace = evidence/'workspace'
    shutil.copytree(seed, workspace)
    source = workspace/'src/Fulfillment.Application/FulfillmentDomain.cs'
    original = source.read_bytes()
    session = None
    builds = 0
    result = {'status':'invalid','scored':False,'agentInvoked':False}
    def export():
        nonlocal builds
        with (evidence/f'export-{builds}.log').open('x') as log:
            subprocess.run(['dotnet','run','--project','Development','--',str(workspace)],cwd=workspace,
                           stdout=log,stderr=subprocess.STDOUT,check=True,timeout=600)
        builds += 1
    try:
        export()
        session = Session(['dotnet',str(workspace/'tools/server/Fulfillment.SemanticServer.dll'),str(workspace)], workspace, evidence)
        server = session.initialize()
        tools = session.request('tools/list', {})['tools']
        expected = {'learn','workspace','resolve','inspect','references','impact','check','compare','compatibility'}
        if {t['name'] for t in tools} != expected: raise ValueError('Tool discovery changed')
        guide = session.call('learn')
        if 'dotnet run --project Development' not in guide['content']: raise ValueError('Missing project export guidance')
        before = session.call('workspace')
        if before['changedInputs']: raise ValueError('Initial export is stale')
        snapshot = before['snapshotId']
        subjects = []; offset = 0
        while offset is not None:
            page = session.call('workspace', {'offset':offset,'limit':100})['result']
            subjects.extend(page['items']); offset=page.get('nextOffset')
        kinds = {s['kind'] for s in subjects}
        if not {'entity-state','relation-query'}.issubset(kinds): raise ValueError('Required model coverage is absent')
        resolved = session.call('resolve', {'query':'fulfillment/reserve','expectedSnapshot':snapshot})
        reserve = [s for s in resolved['result']['items'] if s['id']=='fulfillment/reserve']
        if len(reserve)!=1: raise ValueError('Reservation identity is missing or ambiguous')
        for name in ('inspect','references','impact'):
            session.call(name, {'id':reserve[0]['id'],'expectedSnapshot':snapshot})
        checks = []; offset=0
        while offset is not None:
            page=session.call('check',{'expectedSnapshot':snapshot,'offset':offset,'limit':100})['result']
            if any(not item['isValid'] for item in page['items']): raise ValueError('Invalid exported document')
            checks.extend(page['items']);offset=page.get('nextOffset')
        source.write_bytes(original+b'\n// Integration smoke: source-only edit.\n')
        if not session.call('workspace')['changedInputs']: raise ValueError('Source edit not detected')
        export()
        session.call('check',{'expectedSnapshot':snapshot},expect_error=True)
        comment = session.call('workspace')
        compared = session.call('compare',{'baselineSnapshot':snapshot,'expectedSnapshot':comment['snapshotId']})
        if compared['result']['changes']['total'] != 0: raise ValueError('Comment changed semantics')
        anchor=b'item.Available >= input.Quantity'
        if original.count(anchor)!=1: raise ValueError('Semantic-edit anchor drifted')
        source.write_bytes(original.replace(anchor,b'item.Available > input.Quantity'))
        export()
        after=session.call('workspace')
        changed=session.call('compare',{'baselineSnapshot':snapshot,'expectedSnapshot':after['snapshotId'],'limit':100})
        if after['changedInputs'] or changed['result']['changes']['total']==0: raise ValueError('Semantic edit was not exported')
        if not any(c['id']=='fulfillment/reserve' for c in changed['result']['changes']['items']):
            raise ValueError('Reservation semantic change absent')
        result.update(status='passed',server=server,toolNames=sorted(expected),subjectCount=len(subjects),
            documentChecks=len(checks),domainValidationUnavailable=[c['id'] for c in checks if not c['domainValidationAvailable']],
            baselineSnapshot=snapshot,commentSnapshot=comment['snapshotId'],changedSnapshot=after['snapshotId'],
            semanticChange=changed,limitations=['Scripted source edits, no coding agent',
                'No HTTP compatibility claims; HTTP handlers are outside this export',
                'Local process execution is not a security sandbox'])
    except Exception as error:
        result['error']=str(error)
        raise
    finally:
        source.write_bytes(original)
        try:
            if session:
                export()
                result['shutdownExitCode']=session.close();session=None
                if result['shutdownExitCode'] != 0:
                    result.update(status='invalid',error='Server did not shut down cleanly')
        except Exception as error:
            result.update(status='invalid',error='Cleanup/export failed: '+str(error))
            raise
        finally:
            if session: session.close()
            prepare.runner.write_json(evidence/'report.json',result)
    if result['status'] != 'passed': raise RuntimeError(result)
    print(json.dumps(result,indent=2))

if __name__ == '__main__': main()
