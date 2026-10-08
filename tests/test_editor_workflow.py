import importlib.util
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch
import zipfile

ROOT = Path(__file__).resolve().parents[1]


def module(name, script):
    spec = importlib.util.spec_from_file_location(name, ROOT / 'scripts' / script)
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


editor = module('editor_test', 'editor.py')
workspace = module('workspace_test', 'workspace.py')
user = module('user_setup_test', 'user-setup.py')
media = module('media_workflow_test', 'media.py')


class ExtensionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        (self.root / 'config').mkdir()
        (self.root / 'config/editor-extensions.json').write_text('["test.feature"]')
        self.source = self.root / 'vsix'
        self.source.mkdir()
        self.patch = patch.object(editor, 'ROOT', self.root)
        self.patch.start()

    def tearDown(self):
        self.patch.stop()
        self.temp.cleanup()

    def vsix(self, identifier, dependencies=(), platform='universal', backend=False, pack=(), identity=False):
        publisher, name = identifier.split('.', 1)
        p = self.source / f'{identifier}.vsix'
        with zipfile.ZipFile(p, 'w') as z:
            z.writestr('extension/package.json', json.dumps(dict(publisher=publisher, name=name,
                       version='1.0.0', engines={'vscode': '^1.100.0'}, extensionDependencies=list(dependencies), extensionPack=list(pack))))
            if identity:
                xml = f'<PackageManifest><Identity TargetPlatform="{platform}"/></PackageManifest>'
            else:
                xml = f'<PackageManifest><Property Id="Microsoft.VisualStudio.Code.TargetPlatform" Value="{platform}"/></PackageManifest>'
            z.writestr('extension.vsixmanifest', xml)
            # Legacy property metadata remains supported.
            if backend:
                z.writestr('extension/server/rust-analyzer', 'fixture')
        return p

    def test_dependency_order_and_missing_dependency(self):
        self.vsix('test.feature', ['test.dependency'])
        with self.assertRaisesRegex(ValueError, 'test.dependency'):
            editor.validate(self.source)
        self.vsix('test.dependency')
        self.assertEqual([x['id'] for x in editor.validate(self.source)], ['test.dependency', 'test.feature'])

    def test_wrong_platform_and_absent_native_backend(self):
        p = self.vsix('rust-lang.rust-analyzer', platform='linux-arm64')
        with self.assertRaisesRegex(ValueError, 'linux-arm64'):
            editor.inspect(p)
        p = self.vsix('rust-lang.rust-analyzer', platform='linux-x64')
        with self.assertRaisesRegex(ValueError, 'backend'):
            editor.inspect(p)
        p = self.vsix('rust-lang.rust-analyzer', platform='linux-x64', backend=True)
        self.assertEqual(editor.inspect(p)['platform'], 'linux-x64')

    def test_real_identity_platform_metadata(self):
        p = self.vsix('rust-lang.rust-analyzer', platform='linux-x64', backend=True, identity=True)
        self.assertEqual(editor.inspect(p)['platform'], 'linux-x64')

    def test_pack_members_are_complete_but_not_cyclic_dependencies(self):
        self.vsix('test.feature', pack=['test.debugger'])
        with self.assertRaisesRegex(ValueError, 'test.debugger'):
            editor.validate(self.source)
        self.vsix('test.debugger', dependencies=['test.feature'])
        self.assertEqual([r['id'] for r in editor.validate(self.source)], ['test.feature', 'test.debugger'])

    def test_imported_package_tampering_rejected(self):
        self.vsix('test.feature')
        editor.bundle(self.source)
        folder = self.root / 'offline/editor'
        editor.locked(folder)
        p = folder / 'test.feature.vsix'
        with zipfile.ZipFile(p, 'a') as z:
            z.writestr('extension/extra.txt', 'changed after approval')
        with self.assertRaisesRegex(ValueError, 'locked'):
            editor.locked(folder)


class WorkspaceTests(unittest.TestCase):
    def test_export_and_seed_preserve_commit_and_existing_user_source(self):
        with tempfile.TemporaryDirectory() as t:
            root = Path(t)
            project = root / 'source'
            (project / 'scripts').mkdir(parents=True)
            for file in ('run-singlehost.sh', 'aclt-flow.py'):
                (project / 'scripts' / file).write_text('# fixture\n')
            def git(*args):
                return subprocess.check_output(['git', '-C', str(project), *args], text=True).strip()
            subprocess.run(['git', 'init', str(project)], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            git('add', 'scripts')
            git('-c', 'user.name=Fixture', '-c', 'user.email=fixture@example.invalid', 'commit', '-m', 'fixture')
            commit = git('rev-parse', 'HEAD')
            with patch.object(workspace, 'ROOT', root):
                workspace.bundle(project)
            payload = root / 'payload'
            payload.mkdir()
            (root / 'offline/workspace').rename(payload / 'project')
            target = root / 'user-workspace'
            target.mkdir()
            user.seed_project(payload, target)
            actual = subprocess.check_output(['git', '-C', str(target / 'ACLt'), 'rev-parse', 'HEAD'], text=True).strip()
            self.assertEqual(actual, commit)
            file = target / 'ACLt/scripts/aclt-flow.py'
            file.write_text('user work\n')
            user.seed_project(payload, target)
            self.assertEqual(file.read_text(), 'user work\n')
            (project / 'scripts/aclt-flow.py').write_text('uncommitted\n')
            with patch.object(workspace, 'ROOT', root):
                with self.assertRaisesRegex(ValueError, 'uncommitted'):
                    workspace.bundle(project)

    def test_readonly_extracted_iso_config_can_be_replaced(self):
        with tempfile.TemporaryDirectory() as t:
            path = Path(t) / 'grub.cfg'
            path.write_text('original')
            path.chmod(0o444)
            media.replace_extracted_text(path, 'modified')
            self.assertEqual(path.read_text(), 'modified')
            self.assertEqual(path.stat().st_mode & 0o777, 0o444)

    def test_custom_boot_keeps_interactive_fallback(self):
        original = 'menuentry "Ubuntu" { linux /casper/vmlinuz; initrd /casper/initrd; }\n'
        result = media.customize_boot(original)
        self.assertIn('subiquity.autoinstallpath=cdrom/zeromatrix/autoinstall.yaml', result)
        self.assertTrue(result.endswith(original))
        self.assertIn('interactive-sections:', (ROOT / 'config/autoinstall.yaml').read_text())


if __name__ == '__main__':
    unittest.main()
