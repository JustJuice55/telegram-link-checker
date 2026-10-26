"""Offline directory acceptance: allowlists, request cap, and failure preservation."""
from copy import deepcopy
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from scripts import update_directory as updater
from telegram_link_checker import FetchResponse


STAMP = '2026-10-26T00:00:00Z'
README = ('# Static text owned by the maintainer\r\n\r\n'
          '<!-- DIRECTORY:START -->\r\nold directory\r\n<!-- DIRECTORY:END -->\r\n\r\nfooter\r\n')
COMMUNITY = '<div class="tgme_page_extra">1 234 subscribers</div>'
CONTACT = '<div class="tgme_page_description">If you have Telegram, you can contact @example right away.</div>'


def row(country, topic, username=None, title='A public community'):
    return {'username': username or 'group_' + country, 'title': title,
            'members_count': 999, 'country': country, 'categories': [topic],
            'is_private': False, 'description': 'DO NOT COPY phone=+12345678900',
            'invite_hash': 'DO NOT COPY PRIVATE INVITE', 'avatar_url': 'https://evil.test/tracker',
            'id': 'private-extra-should-not-be-exported'}


def api_fixture(url, **kwargs):
    index = updater.API_URLS.index(url)
    country, topic, _ = updater.COHORTS[index]
    return {'items': [row(country, topic)], 'total': 9999}


class DirectoryTests(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.addCleanup(self.folder.cleanup)
        self.root = Path(self.folder.name)
        (self.root / 'README.md').write_bytes(README.encode())
        (self.root / 'data').mkdir()
        (self.root / 'reports').mkdir()
        (self.root / 'data/communities.json').write_bytes(b'{"old": "snapshot"}\n')
        (self.root / 'reports/directory-checks.json').write_bytes(b'{"old": "audit"}\n')

    def snapshot(self):
        return {name: (self.root / name).read_bytes() for name in ('README.md', 'data/communities.json', 'reports/directory-checks.json')}

    def refresh(self, api=api_fixture, preview=None):
        return updater.update_directory(self.root, api_fetcher=api,
                                        preview_fetcher=preview or (lambda *a, **k: FetchResponse(COMMUNITY)),
                                        checked_at=STAMP, interval=0)

    def test_exactly_three_fixed_requests_and_allowlisted_export(self):
        calls = []
        def api(url, **kwargs):
            calls.append((url, kwargs['timeout']))
            return api_fixture(url)
        data, audit = self.refresh(api)
        self.assertEqual(calls, [(url, 10) for url in updater.API_URLS])
        self.assertEqual(len(data['communities']), 3)
        self.assertEqual(audit['distinct_previews'], 3)
        self.assertEqual(data['communities'][0]['members_count'], 1234)
        serialized = json.dumps(data)
        for private in ('DO NOT COPY', 'description', 'invite_hash', 'avatar_url', 'private-extra-should-not-be-exported'):
            self.assertNotIn(private, serialized)
        self.assertEqual(data['communities'][0]['checked_at'], STAMP)
        self.assertEqual(data['sources'], list(updater.API_URLS))

    def test_community_only_contact_and_bot_are_audited(self):
        def preview(url, **kwargs):
            if url.endswith('_ru'):
                return FetchResponse(CONTACT)
            if url.endswith('_tr'):
                return FetchResponse('<a class="tgme_action_button_new">Start Bot</a>')
            return FetchResponse(COMMUNITY)
        data, audit = self.refresh(preview=preview)
        self.assertEqual(len(data['communities']), 1)
        self.assertEqual(data['communities'][0]['country'], 'uz')
        self.assertEqual({item['status'] for item in audit['checks']}, {'contact_only', 'bot_preview', 'community_preview'})

    def test_duplicate_previews_are_fetched_once_across_cohorts(self):
        calls = []
        def api(url, **kwargs):
            index = updater.API_URLS.index(url)
            country, topic, _ = updater.COHORTS[index]
            return {'items': [row(country, topic, 'same_name'), row(country, topic, 'same_name')]}
        def preview(url, **kwargs):
            calls.append(url)
            return FetchResponse(COMMUNITY)
        data, audit = self.refresh(api, preview)
        self.assertEqual(calls, ['https://t.me/same_name'])
        self.assertEqual(audit['candidate_count'], 6)
        self.assertEqual(len(data['communities']), 3)

    def test_api_failure_preserves_all_previous_output_bytes(self):
        before = self.snapshot()
        def unavailable(url, **kwargs):
            if url == updater.API_URLS[1]:
                raise OSError('network unavailable')
            return api_fixture(url)
        with self.assertRaises(updater.UpdateError):
            self.refresh(unavailable)
        self.assertEqual(self.snapshot(), before)

    def test_inconclusive_preserves_data_readme_and_records_attempt_in_audit(self):
        before = self.snapshot()
        def preview(url, **kwargs):
            if url.endswith('_tr'):
                raise TimeoutError('request failed')
            return FetchResponse(COMMUNITY)
        with self.assertRaises(updater.UpdateError):
            self.refresh(preview=preview)
        after = self.snapshot()
        self.assertEqual(after['README.md'], before['README.md'])
        self.assertEqual(after['data/communities.json'], before['data/communities.json'])
        audit = json.loads(after['reports/directory-checks.json'])
        self.assertEqual(audit['update_status'], 'aborted')
        self.assertEqual(audit['checked_at'], STAMP)
        self.assertEqual([item['status'] for item in audit['checks']].count('inconclusive'), 1)

    def test_http_failure_preserves_published_data_and_readme(self):
        before = self.snapshot()
        with self.assertRaises(updater.UpdateError):
            self.refresh(preview=lambda *a, **k: FetchResponse(COMMUNITY, 503))
        self.assertEqual((self.root / 'data/communities.json').read_bytes(), before['data/communities.json'])
        self.assertEqual((self.root / 'README.md').read_bytes(), before['README.md'])

    def test_malformed_schema_and_private_or_unsafe_username_preserve_outputs(self):
        bad_rows = [None, {'items': {}}, {'items': [dict(row('ru', 'jobs'), username='../oops')]},
                    {'items': [dict(row('ru', 'jobs'), username='https://evil.test/x')]},
                    {'items': [dict(row('ru', 'jobs'), members_count=True)]},
                    {'items': [dict(row('ru', 'jobs'), is_private=True)]},
                    {'items': [dict(row('ru', 'jobs'), country='uz')]},
                    {'items': [dict(row('ru', 'jobs'), categories=['dating'])]},
                    {'items': [row('ru', 'jobs')] * 13}]
        before = self.snapshot()
        for payload in bad_rows:
            with self.subTest(payload=payload), self.assertRaises(updater.UpdateError):
                self.refresh(lambda *a, **k: deepcopy(payload))
            self.assertEqual(self.snapshot(), before)

    def test_titles_escaped_and_links_constructed_with_attribution(self):
        title = '<img src=x onerror=alert(1)> | [fake](https://evil.test)'
        def api(url, **kwargs):
            payload = api_fixture(url)
            payload['items'][0]['title'] = title
            return payload
        data, _ = self.refresh(api)
        readme = (self.root / 'README.md').read_text()
        self.assertNotIn('<img', readme)
        self.assertIn('&lt;img', readme)
        self.assertIn('\\|', readme)
        self.assertIn('\\[fake\\]', readme)
        self.assertIn('https://t.me/group_ru', readme)
        self.assertIn('https://tgden.com/en/chat/group_ru?utm_source=github&utm_medium=open_data&utm_campaign=telegram_community_map', readme)
        self.assertEqual(data['communities'][0]['title'], title)
        encoded = (self.root / 'README.md').read_bytes()
        self.assertTrue(encoded.startswith(README.split(updater.START)[0].encode()))
        self.assertTrue(encoded.endswith(README.split(updater.END)[1].encode()))

    def test_missing_markers_fail_before_requests(self):
        (self.root / 'README.md').write_text('No markers')
        before = self.snapshot()
        calls = []
        with self.assertRaises(updater.UpdateError):
            self.refresh(lambda *a, **k: calls.append(a))
        self.assertEqual(calls, [])
        self.assertEqual(self.snapshot(), before)

    def test_mid_replace_io_failure_rolls_back_all_outputs(self):
        before = self.snapshot()
        real_replace = os.replace
        calls = []
        def fail_once(source, target):
            calls.append((source, target))
            if len(calls) == 2:
                raise OSError('simulated I/O error')
            return real_replace(source, target)
        with patch.object(updater.os, 'replace', side_effect=fail_once), self.assertRaises(OSError):
            self.refresh()
        self.assertEqual(self.snapshot(), before)
        self.assertEqual(list(self.root.rglob('.directory-*')), [])

    def test_fixed_api_fetcher_rejects_redirects_and_arbitrary_sources(self):
        with self.assertRaises(updater.UpdateError):
            updater.fetch_api('https://evil.test/api')
        with self.assertRaises(updater.UpdateError):
            updater._NoRedirects().redirect_request(None, None, 302, 'Found', {}, 'https://evil.test/x')


if __name__ == '__main__':
    unittest.main()
