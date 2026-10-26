"""Consumer URL and no-empty-publication contracts; protected acceptance."""
from pathlib import Path
import tempfile
import unittest

from scripts.update_directory import COHORTS, UpdateError, update_directory, validate_cohort
from telegram_link_checker import normalize_telegram_link


class DirectoryConsumerContract(unittest.TestCase):
    def test_card_url_matches_the_public_tgden_chat_route(self):
        payload = {"items": [{"username": "example_group", "title": "Example group",
                              "members_count": 100, "country": "ru", "categories": ["jobs"],
                              "is_private": False}]}
        rows = validate_cohort(payload, "ru", "jobs", "https://tgden.com/api/v1/chats")
        self.assertEqual(rows[0]["tgden_url"],
                         "https://tgden.com/en/chat/example_group?utm_source=github&utm_medium=open_data&utm_campaign=telegram_community_map")

    def test_short_official_usernames_are_supported(self):
        for name in ("gif", "wiki", "vid"):
            with self.subTest(name=name):
                self.assertEqual(normalize_telegram_link("https://t.me/" + name), "https://t.me/" + name)

    def test_an_empty_cohort_does_not_replace_the_existing_directory(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            readme = b"Intro\n<!-- DIRECTORY:START -->\nlast useful directory\n<!-- DIRECTORY:END -->\n"
            (root / "README.md").write_bytes(readme)
            (root / "data").mkdir()
            (root / "data" / "communities.json").write_bytes(b'{"old":"data"}\n')
            with self.assertRaises(UpdateError):
                update_directory(root, api_fetcher=lambda *a, **k: {"items": []}, interval=0)
            self.assertEqual((root / "README.md").read_bytes(), readme)
            self.assertEqual((root / "data" / "communities.json").read_bytes(), b'{"old":"data"}\n')


if __name__ == "__main__":
    unittest.main()
