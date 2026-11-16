"""Exercise the actual autodoc steps against untrusted files and a local remote."""
import os
import pathlib
import shutil
import subprocess
import tempfile
import unittest

import yaml

ROOT = pathlib.Path(__file__).resolve().parents[2]
WORKFLOW = yaml.safe_load((ROOT / '.github/workflows/autodoc.yaml').read_text())


class AutodocTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='autodoc-')
        self.addCleanup(self.temp.cleanup)
        self.root = pathlib.Path(self.temp.name)
        self.env = os.environ.copy()
        self.env.update(HOME=str(self.root), GIT_CONFIG_NOSYSTEM='1',
                        GIT_CONFIG_GLOBAL='/dev/null', GITHUB_OUTPUT=str(self.root / 'output'))
        (self.root / 'output').touch()
        self.git('init', '--bare', str(self.root / 'remote.git'))
        self.git('init', '-b', 'feature', str(self.root / 'head'))
        self.git('-C', 'head', 'config', 'user.name', 'test')
        self.git('-C', 'head', 'config', 'user.email', 'test@example.com')
        head = self.root / 'head'
        (head / '.github/workflows').mkdir(parents=True)
        (head / '.github/scripts').mkdir()
        (head / '.github/workflows/workflow.yaml').write_text(
            'on:\n  workflow_call:\n    inputs:\n      hostile:\n        type: string\n')
        (head / 'README.md').write_text('<!-- autodoc start -->\nold\n<!-- autodoc end -->\n')
        # These would execute if the PR's generator or Python import path were trusted.
        (head / '.github/scripts/autodoc.py').write_text("open('PWNED','w').write('bad')\n")
        (head / 'yaml.py').write_text("open('PWNED','w').write('bad')\n")
        (head / 'pip').mkdir()
        (head / 'pip/__main__.py').write_text("open('PWNED','w').write('bad')\n")
        self.git('-C', 'head', 'add', '.')
        self.git('-C', 'head', 'commit', '-m', 'PR content')
        self.sha = self.git('-C', 'head', 'rev-parse', 'HEAD').stdout.strip()
        self.git('-C', 'head', 'remote', 'add', 'origin', str(self.root / 'remote.git'))
        self.git('-C', 'head', 'push', 'origin', 'HEAD:refs/heads/feature')
        base = self.root / 'base/.github/scripts'
        base.mkdir(parents=True)
        shutil.copy(ROOT / '.github/scripts/autodoc.py', base / 'autodoc.py')

    def git(self, *args):
        return subprocess.run(['git', *args], cwd=self.root, env=self.env,
                              capture_output=True, text=True, check=True)

    def step(self, name, **extra):
        steps = WORKFLOW['jobs']['autodoc']['steps']
        script = next(step['run'] for step in steps if step.get('name') == name)
        env = self.env | extra
        return subprocess.run(['bash', '--noprofile', '--norc', '-eo', 'pipefail', '-c', script],
                              cwd=self.root, env=env, capture_output=True, text=True)

    def push(self):
        return self.step('Push documentation update', SERVER_URL=str(self.root),
                         REPOSITORY='remote', HEAD_REF='feature', HEAD_SHA=self.sha,
                         GH_TOKEN='not-a-real-token')

    def test_event_and_checkout_use_trusted_workflow_and_event_commit(self):
        self.assertIn('pull_request_target', WORKFLOW[True])
        job = WORKFLOW['jobs']['autodoc']
        self.assertIn('head.repo.full_name == github.repository', job['if'])
        head = next(s for s in job['steps'] if s.get('name') == 'Checkout pull request head')
        self.assertEqual(head['with']['ref'], '${{ github.event.pull_request.head.sha }}')
        self.assertFalse(head['with']['persist-credentials'])

    def test_hostile_content_is_data_and_push_updates_expected_head(self):
        result = self.step('Update documentation')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('changed=true', (self.root / 'output').read_text())
        self.assertFalse((self.root / 'PWNED').exists())
        self.assertFalse((self.root / 'head/PWNED').exists())
        self.assertIn('`hostile`', (self.root / 'head/README.md').read_text())
        result = self.push()
        self.assertEqual(result.returncode, 0, result.stderr)
        pushed = self.git('--git-dir', 'remote.git', 'show', 'feature:README.md').stdout
        self.assertIn('`hostile`', pushed)

    def test_moved_branch_is_not_overwritten(self):
        result = self.step('Update documentation')
        self.assertEqual(result.returncode, 0, result.stderr)
        # Move the remote to a different commit after the event was captured.
        self.git('-C', 'head', 'push', 'origin', 'HEAD:refs/heads/feature')
        result = self.push()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('branch changed', result.stdout)

    def test_symlinked_readme_is_rejected(self):
        readme = self.root / 'head/README.md'
        readme.unlink()
        readme.symlink_to(self.root / 'outside')
        (self.root / 'outside').write_text('untouched')
        result = self.step('Update documentation')
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual((self.root / 'outside').read_text(), 'untouched')

    def test_yaml_python_object_is_not_executed(self):
        workflow = self.root / 'head/.github/workflows/workflow.yaml'
        workflow.write_text('!!python/object/apply:os.system ["touch PWNED"]\n')
        result = self.step('Update documentation')
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse((self.root / 'PWNED').exists())
        self.assertEqual(self.git('-C', 'head', 'rev-parse', 'HEAD').stdout.strip(), self.sha)


if __name__ == '__main__':
    unittest.main()
