import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from account_aliases_debug import save_account_aliases_debug_info, safe_debug_value


class AccountAliasesDebugTest(unittest.TestCase):
    def test_save_account_aliases_debug_info_writes_page_state(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            debug_root = Path(temp_dir) / "logs" / "debug"

            with patch("account_aliases_debug.DEBUG_LOG_ROOT", debug_root):
                debug_dir = save_account_aliases_debug_info(
                    engine="playwright",
                    env={
                        "MF_IMPORT_CSV_BROWSER_HEADLESS": True,
                        "MF_IMPORT_CSV_BROWSER_CHANNEL": "chromium",
                        "MF_IMPORT_CSV_REUSE_LOGIN_SESSION": True,
                    },
                    error=ValueError("手入力口座リンクが見つかりませんでした。"),
                    current_url="https://moneyforward.com/accounts",
                    title="口座",
                    html="<html></html>",
                    link_items=[
                        {
                            "href": "/accounts/show_manual/123456",
                            "text": "財布",
                            "container_text": "財布\n残高",
                        }
                    ],
                    alias_candidates=[
                        {
                            "index": 1,
                            "href": "/accounts/show_manual/123456",
                            "account_id": "123456",
                            "account_name": "財布",
                            "status": "accepted",
                            "reason": "",
                        }
                    ],
                    screenshot_func=lambda path: Path(path).write_bytes(b"png"),
                )

                self.assertTrue((debug_dir / "current_url.txt").exists())
                self.assertEqual(
                    (debug_dir / "current_url.txt").read_text(encoding="utf_8"),
                    "https://moneyforward.com/accounts",
                )
                self.assertEqual(
                    (debug_dir / "title.txt").read_text(encoding="utf_8"),
                    "口座",
                )
                self.assertEqual(
                    (debug_dir / "page.html").read_text(encoding="utf_8"),
                    "<html></html>",
                )
                self.assertIn(
                    "href: /accounts/show_manual/123456",
                    (debug_dir / "links.txt").read_text(encoding="utf_8"),
                )
                account_candidates = (debug_dir / "account_candidates.txt").read_text(
                    encoding="utf_8"
                )
                self.assertIn("candidate_count: 1", account_candidates)
                self.assertIn("accepted_count: 1", account_candidates)
                self.assertIn("財布 => 123456", account_candidates)
                self.assertIn(
                    "browser_engine: playwright",
                    (debug_dir / "runtime.txt").read_text(encoding="utf_8"),
                )
                self.assertIn(
                    "手入力口座リンクが見つかりませんでした。",
                    (debug_dir / "error.log").read_text(encoding="utf_8"),
                )
                self.assertEqual((debug_dir / "screenshot.png").read_bytes(), b"png")

    def test_safe_debug_value_returns_failure_text(self):
        value = safe_debug_value(
            "title",
            lambda: (_ for _ in ()).throw(RuntimeError("cannot read")),
        )

        self.assertIn("failed to get title", value)
        self.assertIn("RuntimeError", value)

    def test_save_debug_info_returns_none_when_directory_creation_fails(self):
        with patch(
            "account_aliases_debug.create_debug_dir",
            side_effect=OSError("cannot create"),
        ):
            debug_dir = save_account_aliases_debug_info(
                engine="playwright",
                env={},
                error=ValueError("original"),
                current_url="https://example.com",
                title="title",
                html="<html></html>",
                link_items=[],
            )

        self.assertIsNone(debug_dir)

    def test_debug_save_failure_does_not_replace_original_error(self):
        with self.assertRaisesRegex(ValueError, "original error"):
            try:
                raise ValueError("original error")
            except ValueError as exc:
                with patch(
                    "account_aliases_debug._write_text",
                    side_effect=OSError("cannot write"),
                ):
                    debug_dir = save_account_aliases_debug_info(
                        engine="selenium",
                        env={},
                        error=exc,
                        current_url="https://example.com",
                        title="title",
                        html="<html></html>",
                        link_items=[],
                    )
                self.assertIsNone(debug_dir)
                raise


if __name__ == "__main__":
    unittest.main()
