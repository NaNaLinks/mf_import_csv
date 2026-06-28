import json
import tempfile
import unittest
from pathlib import Path


from account_aliases_generator import (
    describe_manual_account_link_candidates,
    extract_manual_account_aliases,
    write_account_aliases,
)


class AccountAliasesGeneratorTest(unittest.TestCase):
    def test_extract_manual_account_aliases_from_manual_account_links(self):
        aliases = extract_manual_account_aliases(
            [
                {
                    "href": "/accounts/show_manual/123456",
                    "text": "財布",
                    "container_text": "財布\n編集",
                },
                {
                    "href": "https://moneyforward.com/accounts/show_manual/234567",
                    "text": "事業用現金",
                    "container_text": "",
                },
                {
                    "href": "https://moneyforward.com/accounts/show/999999",
                    "text": "自動連携口座",
                    "container_text": "",
                },
            ]
        )

        self.assertEqual(
            aliases,
            {
                "事業用現金": "234567",
                "財布": "123456",
            },
        )

    def test_extract_manual_account_aliases_accepts_query_string(self):
        aliases = extract_manual_account_aliases(
            [
                {
                    "href": "/accounts/show_manual/234567?tab=history",
                    "text": "事業用現金",
                    "container_text": "",
                },
            ]
        )

        self.assertEqual(aliases, {"事業用現金": "234567"})

    def test_extract_manual_account_aliases_accepts_opaque_account_id(self):
        aliases = extract_manual_account_aliases(
            [
                {
                    "href": "/accounts/show_manual/AGAae-NFSCeRVSfebWilZNpNI-NFwiDqkNg_TKMOU",
                    "text": "財布",
                    "container_text": "",
                },
            ]
        )

        self.assertEqual(
            aliases,
            {"財布": "AGAae-NFSCeRVSfebWilZNpNI-NFwiDqkNg_TKMOU"},
        )

    def test_extract_manual_account_aliases_uses_container_text_when_link_text_is_empty(self):
        aliases = extract_manual_account_aliases(
            [
                {
                    "href": "/accounts/show_manual/345678",
                    "text": "",
                    "container_text": "\nPayPay手入力\n残高\n",
                }
            ]
        )

        self.assertEqual(aliases, {"PayPay手入力": "345678"})

    def test_extract_manual_account_aliases_rejects_duplicate_names(self):
        with self.assertRaisesRegex(ValueError, "同じ口座名"):
            extract_manual_account_aliases(
                [
                    {
                        "href": "/accounts/show_manual/123456",
                        "text": "財布",
                        "container_text": "",
                    },
                    {
                        "href": "/accounts/show_manual/234567",
                        "text": "財布",
                        "container_text": "",
                    },
                ]
            )

    def test_describe_manual_account_link_candidates_reports_status(self):
        candidates = describe_manual_account_link_candidates(
            [
                {
                    "href": "/accounts/show_manual/opaque_123-ABC",
                    "text": "財布",
                    "container_text": "",
                },
                {
                    "href": "/accounts/show/999999",
                    "text": "自動連携口座",
                    "container_text": "",
                },
            ]
        )

        self.assertEqual(candidates[0]["status"], "accepted")
        self.assertEqual(candidates[0]["account_id"], "opaque_123-ABC")
        self.assertEqual(candidates[0]["account_name"], "財布")
        self.assertEqual(candidates[1]["status"], "rejected")
        self.assertEqual(candidates[1]["reason"], "manual_account_href_not_matched")

    def test_write_account_aliases_does_not_overwrite_by_default(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            output_path = Path(temp_dir) / "account_aliases.json"
            output_path.write_text('{"old": "111111"}\n', encoding="utf_8")

            with self.assertRaisesRegex(ValueError, "already exists"):
                write_account_aliases({"new": "222222"}, str(output_path))

            self.assertEqual(
                json.loads(output_path.read_text(encoding="utf_8")),
                {"old": "111111"},
            )

    def test_write_account_aliases_can_overwrite_with_force(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            output_path = Path(temp_dir) / "account_aliases.json"
            output_path.write_text('{"old": "111111"}\n', encoding="utf_8")

            write_account_aliases({"new": "222222"}, str(output_path), force=True)

            self.assertEqual(
                json.loads(output_path.read_text(encoding="utf_8")),
                {"new": "222222"},
            )


if __name__ == "__main__":
    unittest.main()
