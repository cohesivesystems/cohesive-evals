import hashlib
import json
import queue
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
import prepare
from smoke import Session


class PilotBoundaryTests(unittest.TestCase):
    def test_package_pin_hash_and_closure_are_required(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder); packages=root/'packages';packages.mkdir()
            package=packages/'Cohesive.nupkg';package.write_bytes(b'package')
            config={'frameworkRevision':'a'*40,'packageVersion':'0.1.0-test'}
            manifest={'sourceRevision':config['frameworkRevision'],'packageVersion':config['packageVersion'],
                      'packages':[{'file':package.name,'sha256':hashlib.sha256(package.read_bytes()).hexdigest()}]}
            (root/'dependency-manifest.json').write_text(json.dumps(manifest))
            self.assertEqual(manifest,prepare.verify_packages(packages,config))
            package.write_bytes(b'tampered')
            with self.assertRaises(ValueError):prepare.verify_packages(packages,config)
            package.write_bytes(b'package'); (packages/'unexpected.nupkg').write_bytes(b'extra')
            with self.assertRaises(ValueError):prepare.verify_packages(packages,config)
            (packages/'unexpected.nupkg').unlink()
            with self.assertRaises(ValueError):prepare.verify_packages(packages,{**config,'frameworkRevision':'b'*40})

    def test_archive_ignores_dirty_source_and_rejects_links(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);repo=root/'repo';repo.mkdir()
            def git(*args):return subprocess.check_output(['git','-C',str(repo),*args],text=True).strip()
            git('init','-q');(repo/'public.txt').write_text('committed')
            git('add','.');git('-c','user.name=Test','-c','user.email=test@localhost','commit','-qm','baseline')
            revision=git('rev-parse','HEAD');(repo/'public.txt').write_text('dirty')
            (repo/'private.txt').write_text('not committed')
            destination=root/'export';prepare.export_tree(repo,revision,destination)
            self.assertEqual('committed',(destination/'public.txt').read_text())
            self.assertFalse((destination/'private.txt').exists())
            (repo/'link').symlink_to('../private.txt');git('add','link')
            git('-c','user.name=Test','-c','user.email=test@localhost','commit','-qm','link')
            with self.assertRaises(ValueError):prepare.export_tree(repo,'HEAD',root/'linked')

    def test_stdio_error_and_timeout_are_not_success_and_process_closes(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder)
            script='''import sys,json
for line in sys.stdin:
 r=json.loads(line)
 if r['method']=='hang':continue
 print(json.dumps({'jsonrpc':'2.0','id':r['id'],'result':{'isError':True,'content':[]}}),flush=True)
'''
            session=Session([sys.executable,'-u','-c',script],root,root)
            try:
                with self.assertRaises(RuntimeError):session.call('check')
                self.assertTrue(session.call('check',expect_error=True)['isError'])
                with self.assertRaises(queue.Empty):session.request('hang',{},timeout=.05)
            finally:
                self.assertEqual(0,session.close())
            self.assertTrue((root/'mcp.jsonl').read_text())

    def test_custom_packaging_revision_requires_separate_output(self):
        script=prepare.HERE.parent/'packaging/build-packages.py'
        result=subprocess.run([sys.executable,str(script),str(prepare.REPO),'--revision','HEAD','--version','0.1.0-test'],capture_output=True,text=True)
        self.assertEqual(2,result.returncode)
        self.assertIn('--output',result.stderr)

if __name__=='__main__':unittest.main()
