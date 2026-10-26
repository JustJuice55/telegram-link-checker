"""Action boundary tests: only regular files inside the caller workspace."""
import contextlib
import io
import os
from pathlib import Path
import tempfile
import unittest

from scripts import action_check
from telegram_link_checker import FetchResponse


class ActionInputTests(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.addCleanup(self.folder.cleanup)
        self.root = Path(self.folder.name).resolve()
        self.workspace = self.root / 'workspace'
        self.workspace.mkdir()
        self.outside = self.root / 'outside.md'
        self.outside.write_text('[outside](https://t.me/username)')
        (self.workspace / 'README.md').write_text('[group](https://t.me/username)')

    def test_paths_with_shell_syntax_and_unicode_remain_literal_files(self):
        filename = '资料 $(do not run) `literal` ; notes\n.md'
        target = self.workspace / filename
        target.write_text('[group](https://t.me/username)')
        self.assertEqual(action_check.workspace_file(str(self.workspace), filename), target)
        self.assertEqual(action_check.workspace_file(str(self.workspace), str(target)), target)
        nested = self.workspace / 'nested'
        nested.mkdir()
        self.assertEqual(action_check.workspace_file(str(self.workspace), 'nested/../README.md'), self.workspace / 'README.md')

    def test_parent_absolute_and_symlink_escapes_are_rejected(self):
        (self.workspace / 'escape.md').symlink_to(self.outside)
        (self.workspace / 'escape-dir').symlink_to(self.root, target_is_directory=True)
        for value in ('../outside.md', str(self.outside), 'escape.md', 'escape-dir/outside.md'):
            with self.subTest(value=value), self.assertRaises(ValueError):
                action_check.workspace_file(str(self.workspace), value)

    def test_missing_directory_and_special_files_are_rejected(self):
        values = ['missing.md', '.']
        if hasattr(os, 'mkfifo'):
            os.mkfifo(self.workspace / 'pipe.md')
            values.append('pipe.md')
        for value in values:
            with self.subTest(value=value), self.assertRaises(ValueError):
                action_check.workspace_file(str(self.workspace), value)
        for workspace in (None, '', str(self.outside)):
            with self.subTest(workspace=workspace), self.assertRaises(ValueError):
                action_check.workspace_file(workspace, 'README.md')

    def test_internal_symlink_works_after_resolution(self):
        (self.workspace / 'inside.md').symlink_to(self.workspace / 'README.md')
        self.assertEqual(action_check.workspace_file(str(self.workspace), 'inside.md'), self.workspace / 'README.md')

    def test_action_invalid_input_fails_before_any_preview_request(self):
        calls = []
        with contextlib.redirect_stderr(io.StringIO()):
            code = action_check.main(['--json', str(self.root / 'result.json'), '--markdown', str(self.root / 'result.md')],
                                     environ={'GITHUB_WORKSPACE': str(self.workspace), 'CHECKER_INPUT_FILE': '../outside.md'},
                                     fetcher=lambda *a, **k: calls.append(a))
        self.assertEqual(code, 2)
        self.assertEqual(calls, [])
        self.assertFalse((self.root / 'result.json').exists())

    def test_action_valid_file_writes_reports_and_obeys_policy(self):
        contact = '<div class="tgme_page_description">If you have Telegram, you can contact @username right away.</div>'
        code = action_check.main(['--json', str(self.root / 'result.json'), '--markdown', str(self.root / 'result.md')],
                                 environ={'GITHUB_WORKSPACE': str(self.workspace), 'CHECKER_INPUT_FILE': 'README.md', 'CHECKER_FAIL_CONTACT': 'true'},
                                 fetcher=lambda *a, **k: FetchResponse(contact))
        self.assertEqual(code, 1)
        self.assertTrue((self.root / 'result.json').is_file())
        self.assertIn('contact_only', (self.root / 'result.md').read_text())


if __name__ == '__main__':
    unittest.main()
