#!/usr/bin/env python3
"""Validate workspace-local Action inputs before running the preview checker."""
from __future__ import annotations

import argparse
import os
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
import telegram_link_checker as checker  # noqa: E402


def workspace_file(workspace, input_file):
    """Resolve a regular file inside the caller's workspace, following symlinks.

    Relative paths are rooted at GITHUB_WORKSPACE; absolute paths inside that
    workspace also work. Escaping parent paths, outside symlink targets, missing
    paths, directories, and special files are rejected before any check starts.
    No shell parsing or environment-variable expansion is performed.
    """
    if not isinstance(workspace, str) or not workspace:
        raise ValueError("GITHUB_WORKSPACE must identify the caller workspace.")
    if not isinstance(input_file, str) or not input_file:
        raise ValueError("The file input must identify a workspace-local file.")
    try:
        root = Path(workspace).resolve(strict=True)
        if not root.is_dir():
            raise ValueError("GITHUB_WORKSPACE must identify a directory.")
        candidate = (root / input_file).resolve(strict=True)
        try:
            candidate.relative_to(root)
        except ValueError as exc:
            raise ValueError("The file input resolves outside GITHUB_WORKSPACE.") from exc
        if not candidate.is_file():
            raise ValueError("The file input must resolve to a regular file.")
        return candidate
    except (OSError, RuntimeError) as exc:
        raise ValueError("The file input cannot be resolved to a workspace-local regular file.") from exc


def main(argv=None, *, fetcher=None, environ=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--json', required=True, dest='json_path')
    parser.add_argument('--markdown', required=True)
    args = parser.parse_args(argv)
    environ = os.environ if environ is None else environ
    try:
        path = workspace_file(environ.get('GITHUB_WORKSPACE'), environ.get('CHECKER_INPUT_FILE'))
        policy = environ.get('CHECKER_FAIL_CONTACT', 'false')
        if policy not in ('true', 'false'):
            raise ValueError('fail-on-contact must be true or false.')
    except ValueError as exc:
        print('Action input error: ' + str(exc), file=sys.stderr)
        return 2
    checker_args = ['--file', str(path), '--json', args.json_path, '--markdown', args.markdown]
    if policy == 'true':
        checker_args.append('--fail-on-contact')
    return checker.main(checker_args, fetcher=fetcher)


if __name__ == '__main__':
    raise SystemExit(main())
