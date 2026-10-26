"""Acceptance contract. Do not modify to fit the implementation."""
import unittest

from telegram_link_checker import classify_preview, extract_links, normalize_telegram_link


class PreviewContract(unittest.TestCase):
    def test_public_community_requires_preview_evidence_not_http_200(self):
        body = '''<html><head><meta property="og:title" content="Python &amp; Friends"></head>
        <div class="tgme_page_extra">12 034 members, 120 online</div></html>'''
        result = classify_preview(body, 200)
        self.assertEqual(result["status"], "community_preview")
        self.assertEqual(result["title"], "Python & Friends")

    def test_generic_contact_is_reviewable_and_never_called_dead(self):
        body = '''<meta property="og:title" content="Telegram: Contact @code_news">
        <div class="tgme_page_description">If you have <b>Telegram</b>, you can contact
        <a href="tg://resolve?domain=code_news">@code_news</a> right away.</div>'''
        result = classify_preview(body, 200)
        self.assertEqual(result["status"], "contact_only")
        self.assertNotIn("dead", result["evidence"].lower())
        self.assertNotIn("deleted", result["evidence"].lower())

    def test_members_in_description_do_not_prove_a_community(self):
        body = '''<meta property="og:title" content="Telegram: Contact @example">
        <div class="tgme_page_description">If you have Telegram, you can contact @example.
        Our community used to have 15000 members.</div>'''
        self.assertEqual(classify_preview(body, 200)["status"], "contact_only")

    def test_error_or_challenge_is_inconclusive_even_with_old_preview_html(self):
        body = '<meta property="og:title" content="A chat"><div class="tgme_page_extra">100 members</div>'
        self.assertEqual(classify_preview(body, 503)["status"], "inconclusive")
        self.assertEqual(classify_preview('<title>Just a moment...</title>', 200)["status"], "inconclusive")

    def test_official_bot_is_separate_from_group_and_contact(self):
        body = '''<meta property="og:title" content="BotFather">
        <div class="tgme_page_extra">@BotFather</div>
        <a class="tgme_action_button_new" href="tg://resolve?domain=BotFather">Start Bot</a>'''
        self.assertEqual(classify_preview(body, 200)["status"], "bot_preview")


class InputContract(unittest.TestCase):
    def test_canonical_public_usernames_and_deduplicated_markdown(self):
        self.assertEqual(normalize_telegram_link("https://telegram.me/Python_ru?x=1"), "https://t.me/python_ru")
        self.assertEqual(normalize_telegram_link("@Python_ru"), "https://t.me/python_ru")
        self.assertEqual(normalize_telegram_link("https://t.me/s/Python_ru"), "https://t.me/python_ru")
        links = extract_links('[one](https://t.me/Python_ru) [two](https://telegram.me/python_ru)')
        self.assertEqual(links, ["https://t.me/python_ru"])

    def test_other_hosts_credentials_ports_and_invites_are_not_fetched(self):
        for value in ("https://t.me.evil.test/groupname", "https://t.me@127.0.0.1/groupname",
                      "http://127.0.0.1/", "https://t.me:8443/groupname",
                      "https://t.me/+privatehash", "https://t.me/joinchat/privatehash",
                      "https://t.me/share/url?url=https://example.org", "https://t.me/goodname/../../x"):
            with self.subTest(value=value):
                self.assertIsNone(normalize_telegram_link(value))


if __name__ == "__main__":
    unittest.main()
