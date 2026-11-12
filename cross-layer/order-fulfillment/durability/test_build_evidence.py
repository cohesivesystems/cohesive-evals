"""Check that evidence cannot silently refer to stale inputs or executables."""
import json
from pathlib import Path
import tempfile
import unittest

from build import artifact_hashes, input_hashes, verify_build


class BuildEvidenceTests(unittest.TestCase):
    def test_rejects_changes_and_missing_manifest(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            inputs = ['Program.cs', 'App.csproj', 'Directory.Build.props',
                      'Directory.Build.targets', 'global.json', 'NuGet.config',
                      'packages.lock.json', 'packages/dependency.nupkg']
            outputs = ['Fulfillment.Application.dll', 'dependency.dll',
                       'Fulfillment.Application.runtimeconfig.json']
            files = [root / name for name in inputs] + [
                root / 'src/Fulfillment.Application/bin/Debug/net10.0' / name
                for name in outputs]
            for path in files:
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(b'original')
            manifest = root / 'build-manifest.json'
            manifest.write_text(json.dumps({'inputs': input_hashes(root),
                                           'artifacts': artifact_hashes(root)}))
            original_digest = verify_build(root)
            for path in files:
                with self.subTest(path=path.relative_to(root)):
                    path.write_bytes(b'changed')
                    with self.assertRaises(AssertionError):
                        verify_build(root)
                    path.write_bytes(b'original')
                    self.assertEqual(original_digest, verify_build(root))
            extra = root / 'NewActivity.cs'
            extra.write_text('new input')
            with self.assertRaises(AssertionError):
                verify_build(root)
            extra.unlink()
            files[-1].unlink()
            with self.assertRaises(AssertionError):
                verify_build(root)
            manifest.unlink()
            with self.assertRaises(FileNotFoundError):
                verify_build(root)


if __name__ == '__main__':
    unittest.main()
