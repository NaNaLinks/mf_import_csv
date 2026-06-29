import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from account_aliases_generator import load_account_aliases_data, write_account_aliases
from mf_import_csv import (
    resolve_account_alias,
    run_edit_account_aliases,
    run_set_account_alias,
)


class MfImportCsvAliasesTest(unittest.TestCase):
    def _write_aliases(self, path):
        write_account_aliases(
            {
                "version": 1,
                "accounts": [
                    {
                        "account_name": "Appleアカウント",
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
            str(path),
        )

    def test_resolve_account_alias_reads_new_format(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            output_path = Path(temp_dir) / "account_aliases.json"
            self._write_aliases(output_path)

            self.assertEqual(
                resolve_account_alias("apple_account", str(output_path)), "111111"
            )

    def test_run_set_account_alias_updates_by_account_id(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            output_path = Path(temp_dir) / "account_aliases.json"
            self._write_aliases(output_path)

            with patch("builtins.print"):
                run_set_account_alias("111111", "apple", str(output_path))

            data = load_account_aliases_data(str(output_path))
            account = next(
                item for item in data["accounts"] if item["account_id"] == "111111"
            )
            self.assertEqual(account["alias"], "apple")
            self.assertEqual(account["alias_source"], "manual")

    def test_run_edit_account_aliases_updates_selected_account(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            output_path = Path(temp_dir) / "account_aliases.json"
            self._write_aliases(output_path)
            answers = iter(["1", "apple"])

            with patch("builtins.print"):
                run_edit_account_aliases(
                    str(output_path), input_func=lambda _: next(answers)
                )

            data = load_account_aliases_data(str(output_path))
            account = next(
                item for item in data["accounts"] if item["account_id"] == "111111"
            )
            self.assertEqual(account["alias"], "apple")


if __name__ == "__main__":
    unittest.main()
