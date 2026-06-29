import json
import tempfile
import unittest
from pathlib import Path


from account_aliases_generator import (
    alias_to_account_id_map,
    describe_manual_account_link_candidates,
    extract_manual_account_aliases,
    generate_alias_candidate,
    load_account_aliases_data,
    set_account_alias,
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

        self.assertEqual(alias_to_account_id_map(aliases), {"cash": "234567", "wallet": "123456"})
        self.assertEqual(aliases["accounts"][0]["account_name"], "事業用現金")
        self.assertEqual(aliases["accounts"][1]["account_name"], "財布")

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

        self.assertEqual(alias_to_account_id_map(aliases), {"cash": "234567"})

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
            alias_to_account_id_map(aliases),
            {"wallet": "AGAae-NFSCeRVSfebWilZNpNI-NFwiDqkNg_TKMOU"},
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

        self.assertEqual(alias_to_account_id_map(aliases), {"paypay": "345678"})

    def test_generate_alias_candidate_removes_emoji_and_maps_common_words(self):
        self.assertEqual(generate_alias_candidate("🍎Appleアカウント"), "apple_account")
        self.assertEqual(generate_alias_candidate("🐱NaNaLinks明細"), "nanalinks")
        self.assertEqual(generate_alias_candidate("🟡Amazonギフト"), "amazon_gift")

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
                alias_to_account_id_map(load_account_aliases_data(str(output_path))),
                {"new": "222222"},
            )

    def test_write_account_aliases_preserves_manual_alias_by_account_id(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            output_path = Path(temp_dir) / "account_aliases.json"
            output_path.write_text(
                json.dumps(
                    {
                        "version": 1,
                        "accounts": [
                            {
                                "account_name": "🍎Appleアカウント",
                                "account_id": "111111",
                                "alias": "apple",
                                "alias_source": "manual",
                            }
                        ],
                    },
                    ensure_ascii=False,
                ),
                encoding="utf_8",
            )

            generated = extract_manual_account_aliases(
                [
                    {
                        "href": "/accounts/show_manual/111111",
                        "text": "🍎Appleアカウント",
                        "container_text": "",
                    }
                ]
            )
            write_account_aliases(generated, str(output_path), force=True)

            data = load_account_aliases_data(str(output_path))
            self.assertEqual(data["accounts"][0]["alias"], "apple")
            self.assertEqual(data["accounts"][0]["alias_source"], "manual")

    def test_set_account_alias_marks_manual_and_rejects_duplicates(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            output_path = Path(temp_dir) / "account_aliases.json"
            write_account_aliases(
                {
                    "version": 1,
                    "accounts": [
                        {
                            "account_name": "🍎Appleアカウント",
                            "account_id": "111111",
                            "alias": "apple_account",
                            "alias_source": "auto",
                        },
                        {
                            "account_name": "PayPay",
                            "account_id": "222222",
                            "alias": "paypay",
                            "alias_source": "auto",
                        },
                    ],
                },
                str(output_path),
            )

            updated = set_account_alias("111111", "apple", str(output_path))
            self.assertEqual(updated["alias"], "apple")
            self.assertEqual(updated["alias_source"], "manual")

            with self.assertRaisesRegex(ValueError, "already used"):
                set_account_alias("111111", "paypay", str(output_path))


if __name__ == "__main__":
    unittest.main()
