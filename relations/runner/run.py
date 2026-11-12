#!/usr/bin/env python3
"""Replay a dry submission in an isolated workspace and retain a versioned score."""
import argparse
from datetime import datetime, timezone
import hashlib
import io
import json
import os
from pathlib import Path, PurePosixPath
import platform
import re
import shutil
import subprocess
import sys
import tarfile
import time
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parent


class InfrastructureError(Exception):
    pass


def write_json(path, value):
    path.write_text(json.dumps(value, indent=2) + '\n')


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def utc_now():
    return datetime.now(timezone.utc).isoformat(timespec='seconds').replace('+00:00', 'Z')


def paths(root):
    for directory, dirs, files in os.walk(root, followlinks=False):
        if Path(directory) == root:
            dirs[:] = [d for d in dirs if d != '.git']
        for name in sorted(dirs + files):
            yield Path(directory)/name


def manifest(root):
    return {'schemaVersion': 'cohesive.relations.workspace-manifest/v1', 'files': [
        {'path': p.relative_to(root).as_posix(), 'size': p.stat().st_size, 'sha256': digest(p)}
        for p in sorted(paths(root)) if not p.is_symlink() and p.is_file()]}


def audit(root, config, condition, exact, log):
    errors = []
    for p in paths(root):
        relative = p.relative_to(root)
        if p.is_symlink():
            errors.append(f'Symlink: {relative}')
            continue
        if p.name in config['forbiddenPathNames'] or '.git' in relative.parts:
            errors.append(f'Forbidden path: {relative}')
        if p.is_file():
            content = p.read_bytes()
            if b'\0' not in content:
                for text in config['forbiddenText']:
                    if text.encode() in content:
                        errors.append(f'Forbidden text {text!r}: {relative}')
    if exact and {p.name for p in root.iterdir() if p.name != '.git'} != set(config['conditions'][condition]['allowedTopLevel']):
        errors.append('Top-level allowlist mismatch')
    log.write_text('\n'.join(errors or ['Audit passed.']) + '\n')
    return not errors


def validate_oracle(report, config, condition, exit_code):
    """Reject incomplete or contradictory scorer evidence, including vacuous passes."""
    def require(test, message):
        if not test:
            raise InfrastructureError('Invalid oracle report: ' + message)

    require(isinstance(report, dict), 'expected object')
    require(report.get('schemaVersion') == config['oracle']['reportSchemaVersion'], 'schema version')
    require(report.get('condition') == condition, 'condition')
    require(exit_code in (0, 1), f'unexpected process exit {exit_code}')

    def results(key, ids):
        values = report.get(key)
        require(isinstance(values, list), key)
        require(all(isinstance(v, dict) for v in values), key + ' entries')
        actual = [v.get('id') for v in values]
        require(len(actual) == len(ids) and set(actual) == set(ids), key + ' missing/duplicate/unexpected IDs')
        require(all(v.get('status') in ('passed', 'failed') for v in values), key + ' statuses')
        return {v['id']: v for v in values}

    allocation = config['oracle']['checksByObligation']
    checks = results('behavioralChecks', {c for ids in allocation.values() for c in ids})
    treatment = results('treatmentIntegrityChecks', config['conditions'][condition]['treatmentCheckIds'])
    obligations = results('obligations', config['obligationIds'])
    for key, ids in allocation.items():
        require(obligations[key].get('checks') == ids, key + ' check allocation')
        expected = 'passed' if all(checks[c]['status'] == 'passed' for c in ids) else 'failed'
        require(obligations[key]['status'] == expected, key + ' inconsistent aggregation')
    for value in list(checks.values()) + list(treatment.values()):
        require(isinstance(value.get('evidence'), str), 'check evidence')
    integrity = 'passed' if all(v['status'] == 'passed' for v in treatment.values()) else 'failed'
    hidden = 'passed' if all(v['status'] == 'passed' for v in obligations.values()) else 'failed'
    outcome = 'passed' if hidden == integrity == 'passed' else 'failed'
    require(report.get('treatmentIntegrity') == integrity and report.get('outcome') == outcome, 'inconsistent outcome')
    require(exit_code == (0 if outcome == 'passed' else 1), 'exit/outcome disagreement')
    return [obligations[k] for k in config['obligationIds']], hidden, integrity


def visible_result(directory, exit_code):
    reports = list(directory.glob('*.trx'))
    if not reports:
        raise InfrastructureError('Visible test process produced no TRX report')
    executed = failed = 0
    for path in reports:
        counter = ET.parse(path).find('.//{*}Counters')
        if counter is None:
            raise InfrastructureError('Visible test report has no counters')
        executed += int(counter.attrib['executed'])
        failed += int(counter.attrib['failed'])
        if any(int(counter.attrib.get(k, 0)) for k in ('error', 'timeout', 'aborted')):
            raise InfrastructureError('Visible test host reported an infrastructure failure')
    if not executed or exit_code != (1 if failed else 0):
        raise InfrastructureError('Visible test exit/report disagreement or no executed tests')
    return 'failed' if failed else 'passed'


class Runner:
    def __init__(self, args):
        self.args = args
        self.config = json.loads(args.config.read_text())
        self.repo = Path(subprocess.check_output(['git', '-C', str(ROOT), 'rev-parse', '--show-toplevel'], text=True).strip())
        self.run = args.output_root.resolve()/args.run_id
        self.run.mkdir(parents=True, exist_ok=False)  # Never overwrite evidence.
        self.workspace = self.run/'workspace'
        self.submission = self.run/'scoring/submission'
        self.oracle = self.run/'scoring/oracle'
        self.logs = self.run/'evidence/logs'
        for path in (self.workspace, self.submission, self.oracle, self.logs,
                     self.run/'evidence/manifests', self.run/'inputs/patches', self.run/'agent'):
            path.mkdir(parents=True, exist_ok=True)
        self.env = dict(os.environ, DOTNET_CLI_HOME=os.environ.get('COHESIVE_EVAL_DOTNET_CLI_HOME', '/tmp/cohesive-evals-dotnet-home'),
                        DOTNET_SKIP_FIRST_TIME_EXPERIENCE='1', DOTNET_CLI_TELEMETRY_OPTOUT='1')
        self.dotnet = os.environ.get('DOTNET_CLI', 'dotnet')
        self.started = time.monotonic()
        cfg = self.config
        selected = cfg['conditions'][args.condition]
        self.record = {
            'schemaVersion': 'cohesive.relations.run-record/v1', 'runId': args.run_id,
            'phase': 'dryRun', 'condition': args.condition, 'validity': 'valid', 'invalidReason': None, 'outcome': 'incomplete',
            'configuration': {**{key: cfg[key] for key in ('runnerVersion', 'protocolVersion', 'caseId', 'taskId', 'task', 'baselineRevision')},
                'runnerSourceRevision': '', 'runnerSourceDirty': False, 'configSha256': digest(args.config),
                'conditionTree': selected['tree'], 'oracleRevision': cfg['oracle']['revision'], 'oracleTree': cfg['oracle']['tree'],
                'dotnetSdk': '', 'host': {'os': platform.system(), 'architecture': platform.machine()}},
            'timing': {'startedAt': utc_now()},
            'workspace': {'baselineCommit': None, 'changedFileCount': 0, 'preManifest': 'evidence/manifests/pre.json', 'postManifest': 'evidence/manifests/post.json'},
            'submission': {'appliedInputs': [], 'finalPatch': 'evidence/final.patch', 'patchLineCount': 0},
            'agent': {'mode': 'dryRunPatchReplay', 'invoked': False, 'stdout': 'agent/stdout.log', 'stderr': 'agent/stderr.log'},
            'gates': {key: 'notEvaluated' for key in ('preWorkspaceAudit', 'postWorkspaceAudit', 'workspaceAudit', 'dependencyRestore',
                'applicationBuild', 'visibleTests', 'oracleAdapterBuild', 'contractBuild', 'oracleExecution', 'hiddenChecks', 'treatmentIntegrity')},
            'obligations': [{'id': key, 'status': 'notEvaluated', 'checks': []} for key in cfg['obligationIds']],
            'evidence': {key: 'evidence/logs/'+name+'.log' for key, name in (
                ('applicationRestoreLog', 'application-restore'), ('applicationBuildLog', 'application-build'),
                ('visibleTestsLog', 'visible-tests'), ('oracleRestoreLog', 'oracle-restore'),
                ('oracleBuildLog', 'oracle-build'), ('oracleExecutionLog', 'oracle-execution'))}}
        self.record['gates']['oracleExitCode'] = None
        self.record['evidence'].update(oracleReport=None, gitStatus='evidence/git-status.txt')
        for path in list(self.record['evidence'].values()) + ['evidence/final.patch', 'agent/stdout.log', 'agent/stderr.log']:
            if path:
                (self.run/path).touch()
        for phase in ('pre', 'post'):
            write_json(self.run/f'evidence/manifests/{phase}.json', {'schemaVersion': 'cohesive.relations.workspace-manifest/v1', 'files': []})
        shutil.copy2(args.config, self.run/'inputs/config.json')
        shutil.copy2(ROOT/'run-record.schema.json', self.run/'inputs/run-record.schema.json')

    def command(self, args, cwd=None, log=None, check=True, env=None):
        with (self.logs/(log+'.log')).open('ab') if log else io.BytesIO() as output:
            result = subprocess.run([str(a) for a in args], cwd=cwd or self.repo, env=env or self.env,
                                    stdout=output if log else subprocess.PIPE, stderr=subprocess.STDOUT,
                                    timeout=self.config.get('commandTimeoutSeconds', 120))
        if check and result.returncode:
            raise InfrastructureError(f'Command failed ({result.returncode}): {args[0]}; see {log or "runner"} log')
        return result

    def git(self, *args, cwd=None):
        return self.command(['git', *args], cwd=cwd).stdout

    def export(self, revision, path, expected, destination):
        selection = f'{revision}:{path}'
        if self.git('rev-parse', selection).decode().strip() != expected:
            raise InfrastructureError('Pinned Git tree mismatch: ' + path)
        archive = self.git('archive', selection)
        with tarfile.open(fileobj=io.BytesIO(archive)) as tar:
            for member in tar:
                name = PurePosixPath(member.name)
                if name.is_absolute() or '..' in name.parts or not (member.isfile() or member.isdir()):
                    raise InfrastructureError('Unsafe archive entry: ' + member.name)
                target = destination.joinpath(*name.parts)
                if member.isdir():
                    target.mkdir(parents=True, exist_ok=True)
                else:
                    target.parent.mkdir(parents=True, exist_ok=True)
                    with tar.extractfile(member) as source, target.open('wb') as output:
                        shutil.copyfileobj(source, output)
                    target.chmod(member.mode & 0o777)

    def audit_phase(self, phase):
        passed = audit(self.workspace, self.config, self.args.condition, phase == 'pre', self.logs/(phase+'-workspace-audit.log'))
        write_json(self.run/f'evidence/manifests/{phase}.json', manifest(self.workspace))
        self.record['gates'][phase+'WorkspaceAudit'] = 'passed' if passed else 'failed'
        if not passed:
            self.record['gates']['workspaceAudit'] = 'failed'
            raise InfrastructureError(phase + '-run workspace audit failed')

    def dotnet_command(self, args, log):
        return self.command([self.dotnet, *args, '-m:1', '-p:UseSharedCompilation=false', '-nodeReuse:false'],
                            cwd=self.submission, log=log, check=False).returncode

    def build(self, project, gate, log, extra=()):
        args = ['build', project, '--no-restore', *extra]
        code = self.dotnet_command(args, log)
        if code:
            text = (self.logs/(log+'.log')).read_text(errors='replace')
            if re.search(r'MSB6006: "csc" exited with code (134|139)', text):
                # Retain the original retry allowance, but classify the retry's evidence afresh.
                retry_log = log+'-retry'
                code = self.dotnet_command(args, retry_log)
                text = (self.logs/(retry_log+'.log')).read_text(errors='replace')
                with (self.logs/(log+'.log')).open('a') as output:
                    output.write('\nCompiler retry:\n'+text)
            if code:
                self.record['gates'][gate] = 'failed'
                if code == 1 and re.search(r'\berror (?:CS|FS|BC)\d+\b', text):
                    self.record['gates']['contractBuild'] = 'failed'
                    return False
                raise InfrastructureError('Build process failed without submission compiler diagnostics: ' + log)
        self.record['gates'][gate] = 'passed'
        return True

    def execute(self):
        cfg, record, gates = self.config, self.record, self.record['gates']
        selected = cfg['conditions'][self.args.condition]
        record['configuration']['runnerSourceRevision'] = self.git('rev-parse', 'HEAD').decode().strip()
        record['configuration']['runnerSourceDirty'] = bool(self.git('status', '--porcelain', '--', 'relations/runner'))
        self.export(cfg['baselineRevision'], selected['path'], selected['tree'], self.workspace)
        self.audit_phase('pre')
        self.git('init', '-q', cwd=self.workspace)
        self.git('config', 'user.name', 'Cohesive Evaluation Runner', cwd=self.workspace)
        self.git('config', 'user.email', 'runner@invalid.local', cwd=self.workspace)
        self.git('add', '-A', cwd=self.workspace)
        date = self.git('show', '-s', '--format=%aI', cfg['baselineRevision']).decode().strip()
        self.command(['git', 'commit', '-q', '-m', 'Evaluation baseline'], cwd=self.workspace,
                     env=dict(self.env, GIT_AUTHOR_DATE=date, GIT_COMMITTER_DATE=date))
        record['workspace']['baselineCommit'] = self.git('rev-parse', 'HEAD', cwd=self.workspace).decode().strip()
        for index, patch in enumerate(self.args.patch, 1):
            source = patch if patch.is_absolute() else self.repo/patch
            target = self.run/'inputs/patches'/f'{index:02d}-{source.name}'
            shutil.copy2(source, target)
            record['submission']['appliedInputs'].append({'path': str(target.relative_to(self.run)), 'sha256': digest(target)})
            self.command(['git', 'apply', target], cwd=self.workspace, log='patch-application')
        (self.run/'agent/stdout.log').write_text('Dry-run patch replay; no coding agent was invoked.\n')
        # Preserve the submitted diff even when the post-audit rejects the workspace.
        status = self.git('status', '--porcelain=v1', '-z', cwd=self.workspace)
        (self.run/'evidence/git-status.txt').write_bytes(status)
        self.git('add', '-N', '-f', '--', '.', cwd=self.workspace)
        diff = self.git('diff', '--binary', '--no-ext-diff', cwd=self.workspace)
        (self.run/'evidence/final.patch').write_bytes(diff)
        record['workspace']['changedFileCount'] = len(status.rstrip(b'\0').split(b'\0')) if status else 0
        record['submission']['patchLineCount'] = len(diff.splitlines())
        self.audit_phase('post')
        gates['workspaceAudit'] = 'passed'
        shutil.copytree(self.workspace, self.submission, dirs_exist_ok=True, ignore=shutil.ignore_patterns('.git'))
        self.export(cfg['oracle']['revision'], cfg['oracle']['path'], cfg['oracle']['tree'], self.oracle)
        record['configuration']['dotnetSdk'] = self.command([self.dotnet, '--version'], cwd=self.submission).stdout.decode().strip()
        solution = self.submission/'LoadSearch.slnx'
        nuget = self.submission/'NuGet.config'
        code = self.dotnet_command(['restore', solution, '--configfile', nuget], 'application-restore')
        gates['dependencyRestore'] = 'failed' if code else 'passed'
        if code:
            raise InfrastructureError('Application dependency restore failed')
        if not self.build(solution, 'applicationBuild', 'application-build'):
            return
        test_results = self.run/'evidence/visible-results'
        code = self.dotnet_command(['test', solution, '--no-build', '--no-restore', '--logger', 'trx', '--results-directory', test_results], 'visible-tests')
        gates['visibleTests'] = visible_result(test_results, code)
        project = self.oracle/'LoadSearch.Oracle.csproj'
        extra = [f'-p:SubmissionRoot={self.submission}']
        if self.dotnet_command(['restore', project, '--configfile', nuget, *extra], 'oracle-restore'):
            raise InfrastructureError('Oracle dependency restore failed')
        if not self.build(project, 'oracleAdapterBuild', 'oracle-build', extra):
            return
        gates['contractBuild'] = 'passed'
        report_path = self.run/'evidence/oracle-report.json'
        result = self.command([self.dotnet, self.oracle/'bin/Debug/net10.0/LoadSearch.Oracle.dll',
            '--condition', self.args.condition, '--submission-root', self.submission, '--output', report_path], log='oracle-execution', check=False)
        gates['oracleExitCode'] = result.returncode
        gates['oracleExecution'] = 'failed'
        if report_path.exists():
            record['evidence']['oracleReport'] = 'evidence/oracle-report.json'
        try:
            report = json.loads(report_path.read_text())
            obligations, hidden, integrity = validate_oracle(report, cfg, self.args.condition, result.returncode)
        except (ValueError, TypeError, KeyError, OSError) as error:
            raise InfrastructureError('Missing or malformed oracle report: ' + str(error)) from error
        record['obligations'] = obligations
        gates.update(oracleExecution='passed', hiddenChecks=hidden, treatmentIntegrity=integrity)
        if all(gates[k] == 'passed' for k in ('contractBuild', 'visibleTests', 'hiddenChecks', 'treatmentIntegrity')):
            record['outcome'] = 'complete'

    def run_and_record(self):
        exit_code = 0
        try:
            self.execute()
        except (InfrastructureError, OSError, ValueError, KeyError, TypeError, ET.ParseError, subprocess.SubprocessError) as error:
            self.record.update(validity='invalid', outcome='notScored', invalidReason=str(error))
            (self.logs/'runner-error.log').write_text(f'{type(error).__name__}: {error}\n')
            exit_code = 2
        self.record['timing'].update(endedAt=utc_now(), elapsedSeconds=int(time.monotonic()-self.started))
        write_json(self.run/'inputs/patches.json', self.record['submission']['appliedInputs'])
        write_json(self.run/'evidence/obligations.json', self.record['obligations'])
        write_json(self.run/'run.json', self.record)
        print(f"Run {self.args.run_id}: {self.record['validity']}/{self.record['outcome']}\nRecord: {self.run/'run.json'}")
        return exit_code


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--condition', required=True, choices=['conventional', 'cohesive'])
    parser.add_argument('--run-id', required=True)
    parser.add_argument('--output-root', required=True, type=Path)
    parser.add_argument('--config', type=Path, default=ROOT/'config.v0.1.json')
    parser.add_argument('--patch', action='append', default=[], type=Path)
    args = parser.parse_args()
    if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9._-]*', args.run_id):
        parser.error('Provide a filesystem-safe run ID')
    try:
        return Runner(args).run_and_record()
    except FileExistsError:
        print('Run directory exists; refusing to overwrite evidence.', file=sys.stderr)
        return 73
    except (OSError, ValueError, KeyError, subprocess.SubprocessError) as error:
        print(f'Runner setup failed: {error}', file=sys.stderr)
        return 2


if __name__ == '__main__':
    sys.exit(main())
