"""Offline regression tests for request boundaries, evidence, and CLI behavior."""
import contextlib
from email.message import Message
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from urllib.error import HTTPError
from urllib.request import Request

import telegram_link_checker as checker


COMMUNITY = '<meta property="og:title" content="Tools &amp; Friends"><div class="tgme_page_extra"><b>12</b> 345 <span>members</span>, 20 online</div>'
CONTACT = '<div class="tgme_page_description">If you have Telegram, you can contact @username right away.</div>'
BOT = '<a class="tgme_action_button_new"><span>Start</span> Bot</a>'


class PreviewTests(unittest.TestCase):
    def test_nested_tags_entities_and_count(self):
        result = checker.classify_preview(COMMUNITY)
        self.assertEqual(result['status'], 'community_preview')
        self.assertEqual(result['title'], 'Tools & Friends')
        self.assertEqual(result['members_count'], 12345)

    def test_subscriber_evidence_and_unsupported_abbreviation(self):
        result = checker.classify_preview('<div class="tgme_page_extra">1,234 subscribers</div>')
        self.assertEqual(result['members_count'], 1234)
        self.assertEqual(checker.classify_preview('<div class="tgme_page_extra">1.2K members</div>')['status'], 'inconclusive')

    def test_script_and_description_do_not_prove_a_community(self):
        body = '<script><div class="tgme_page_extra">100 members</div></script><div class="tgme_page_description">500 subscribers</div>'
        self.assertEqual(checker.classify_preview(body)['status'], 'inconclusive')

    def test_bot_and_contact_observations_are_separate(self):
        self.assertEqual(checker.classify_preview(BOT)['status'], 'bot_preview')
        self.assertEqual(checker.classify_preview(CONTACT)['status'], 'contact_only')
        self.assertEqual(checker.classify_preview('<meta property="og:title" content="Telegram: Contact @username">')['status'], 'inconclusive')

    def test_challenge_and_oversize_are_inconclusive(self):
        self.assertEqual(checker.classify_preview(COMMUNITY + '<script src="/cdn-cgi/challenge-platform/test"></script>')['status'], 'inconclusive')
        self.assertEqual(checker.classify_preview(COMMUNITY + 'x' * checker.MAX_BODY_BYTES)['status'], 'inconclusive')


class InputAndRequestTests(unittest.TestCase):
    def test_additional_unsafe_paths(self):
        for value in ('https://t.me//username', 'https://t.me/s/username/123',
                      'https://t.me/%75sername', 'https://t.me/username//',
                      'https://t.me:443/username', 'https://t.me/username/123',
                      'http://t.me/username', '@xy', 'https://t.me/addstickers'):
            with self.subTest(value=value):
                self.assertIsNone(checker.normalize_telegram_link(value))

    def test_markdown_preserves_first_occurrence_and_ignores_handles(self):
        text = '[one](https://t.me/username). https://telegram.me/USERNAME @person https://evil.test/a'
        self.assertEqual(checker.extract_links(text), ['https://t.me/username'])

    def test_redirects_rejected_before_opening(self):
        handler = checker._TelegramRedirects()
        request = Request('https://t.me/username')
        for target in ('https://evil.test/username', 'http://t.me/username',
                       'https://t.me/+private', 'https://t.me/share/url',
                       'https://t.me:443/username', 'https://t.me@127.0.0.1/username'):
            with self.subTest(target=target), self.assertRaises(checker.UnsafeRedirect):
                handler.redirect_request(request, None, 302, 'Found', {}, target)
        redirected = handler.redirect_request(request, None, 302, 'Found', {}, 'https://telegram.me/Other_name?x=1')
        self.assertEqual(redirected.full_url, 'https://t.me/other_name')
        request.telegram_redirect_count = checker.MAX_REDIRECTS
        with self.assertRaises(checker.UnsafeRedirect):
            handler.redirect_request(request, None, 302, 'Found', {}, '/other_name')

    def test_redirects_share_global_request_limiter(self):
        class Counter:
            count = 0
            def wait(self):
                self.count += 1
        counter = Counter()
        handler = checker._TelegramRedirects(counter)
        handler.redirect_request(Request('https://t.me/username'), None, 302, 'Found', {}, '/other_name')
        self.assertEqual(counter.count, 1)

    def test_network_failure_is_inconclusive_and_does_not_leak_exception(self):
        def unavailable(url, **kwargs):
            raise OSError('secret-token=abc and bad remote markup')
        result = checker.check_links(['@username'], fetcher=unavailable, interval=0)[0]
        self.assertEqual(result['status'], 'inconclusive')
        self.assertNotIn('secret', result['evidence'])
        self.assertNotIn('dead', result['evidence'])
        self.assertNotIn('deleted', result['evidence'])

    def test_final_url_is_checked_for_injected_fetcher(self):
        result = checker.check_links(['@username'], fetcher=lambda *a, **k: checker.FetchResponse(COMMUNITY, 200, 'https://evil.test/x'), interval=0)[0]
        self.assertEqual(result['status'], 'inconclusive')

    def test_deduplicate_and_preflight_bound_before_any_fetch(self):
        fetched = []
        def fetch(url, **kwargs):
            fetched.append(url)
            return checker.FetchResponse(COMMUNITY)
        results = checker.check_links(['@username', 'https://telegram.me/USERNAME'], fetcher=fetch, interval=0)
        self.assertEqual(len(results), 1)
        self.assertEqual(fetched, ['https://t.me/username'])
        fetched.clear()
        with self.assertRaises(ValueError):
            checker.check_links(['@username', 'https://evil.test/x'], fetcher=fetch, interval=0)
        self.assertEqual(fetched, [])
        with self.assertRaises(ValueError):
            checker.check_links(['@group' + str(index) for index in range(201)], fetcher=fetch, interval=0)
        self.assertEqual(fetched, [])

    def test_fetch_uses_signed_identity_and_bounded_read(self):
        class Response(io.BytesIO):
            status = 200
            headers = Message()
            headers['Content-Type'] = 'text/html; charset=utf-8'
            def geturl(self):
                return 'https://t.me/username'
        requests = []
        class Opener:
            def open(self, request, timeout):
                requests.append((request, timeout))
                return Response(COMMUNITY.encode())
        with patch.object(checker, 'build_opener', return_value=Opener()):
            result = checker.fetch_preview('@username')
        self.assertEqual(result.status_code, 200)
        self.assertIn('https://github.com/JustJuice55/telegram-link-checker', requests[0][0].get_header('User-agent'))
        self.assertEqual(requests[0][1], 10)

    def test_http_failure_does_not_read_stale_body(self):
        class Opener:
            def open(self, *args, **kwargs):
                raise HTTPError('https://t.me/username', 503, 'Unavailable', {}, io.BytesIO(COMMUNITY.encode()))
        with patch.object(checker, 'build_opener', return_value=Opener()):
            response = checker.fetch_preview('@username')
        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.body, '')


class CliTests(unittest.TestCase):
    def run_cli(self, body, args):
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            return checker.main(args, fetcher=lambda *a, **k: checker.FetchResponse(body))

    def test_exit_codes_for_contact_policy_and_inconclusive(self):
        self.assertEqual(self.run_cli(COMMUNITY, ['@username']), 0)
        self.assertEqual(self.run_cli(CONTACT, ['@username']), 0)
        self.assertEqual(self.run_cli(CONTACT, ['@username', '--fail-on-contact']), 1)
        self.assertEqual(self.run_cli('', ['@username', '--fail-on-contact']), 3)
        self.assertEqual(self.run_cli(COMMUNITY, ['https://evil.test/username']), 2)
        self.assertEqual(checker.exit_code([{'status': 'contact_only'}, {'status': 'inconclusive'}], True), 3)

    def test_file_input_json_and_markdown_reports(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder)
            (path / 'links.md').write_text('[group](https://t.me/username)', encoding='utf-8')
            code = self.run_cli(COMMUNITY, ['--file', str(path / 'links.md'), '--json', str(path / 'result.json'), '--markdown', str(path / 'result.md')])
            self.assertEqual(code, 0)
            report = json.loads((path / 'result.json').read_text())
            self.assertEqual(report['results'][0]['status'], 'community_preview')
            self.assertIn('community_preview', (path / 'result.md').read_text())

    def test_remote_text_cannot_inject_report_html_links_or_tables(self):
        escaped = checker.markdown_text('<img src=x onerror=alert(1)> | [x](https://evil.test)\n## title')
        self.assertNotIn('<img', escaped)
        self.assertIn('\\|', escaped)
        self.assertIn('\\[x\\]', escaped)
        self.assertNotIn('\n', escaped)


if __name__ == '__main__':
    unittest.main()
