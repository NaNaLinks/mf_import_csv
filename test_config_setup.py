import io
import os
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

from config_setup import run_setup, run_show_config, write_env_file


class ConfigSetupTest(unittest.TestCase):
    def test_write_env_file_does_not_overwrite_existing_file(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            env_path = Path(temp_dir) / ".env"
            env_path.write_text("MF_IMPORT_CSV_USER=\"old\"\n", encoding="utf_8")

            with self.assertRaisesRegex(ValueError, "already exists"):
                write_env_file({"MF_IMPORT_CSV_USER": "new"}, str(env_path))

            self.assertEqual(
                env_path.read_text(encoding="utf_8"),
                "MF_IMPORT_CSV_USER=\"old\"\n",
            )

    def test_run_setup_writes_values_without_echoing_password(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            env_path = Path(temp_dir) / ".env"
            answers = iter(
                [
                    "user@example.com",
                    "https://moneyforward.com/accounts/show_manual/123456",
                    "playwright",
                    "n",
                    "chromium",
                    "y",
                    ".auth/moneyforward-playwright",
                ]
            )

            output = io.StringIO()
            with redirect_stdout(output):
                run_setup(
                    env_file=str(env_path),
                    input_func=lambda _prompt: next(answers),
                    password_func=lambda _prompt: "dummy-hidden-value",
                )

            written = env_path.read_text(encoding="utf_8")
            self.assertIn('MF_IMPORT_CSV_USER="user@example.com"', written)
            self.assertIn('MF_IMPORT_CSV_PASSWORD="dummy-hidden-value"', written)
            self.assertIn('MF_IMPORT_CSV_BROWSER_ENGINE="playwright"', written)
            self.assertIn('MF_IMPORT_CSV_REUSE_LOGIN_SESSION="true"', written)
            self.assertNotIn("dummy-hidden-value", output.getvalue())

    def test_run_setup_does_not_prompt_when_env_file_exists(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            env_path = Path(temp_dir) / ".env"
            env_path.write_text("MF_IMPORT_CSV_USER=\"old\"\n", encoding="utf_8")

            def fail_input(_prompt):
                raise AssertionError("setup should not prompt when .env exists")

            with self.assertRaisesRegex(ValueError, "already exists"):
                run_setup(
                    env_file=str(env_path),
                    input_func=fail_input,
                    password_func=fail_input,
                )

    def test_show_config_masks_secret_and_account_url_values(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            current_dir = os.getcwd()
            try:
                os.chdir(temp_dir)
                Path(".env").write_text(
                    "\n".join(
                        [
                            'MF_IMPORT_CSV_ACCOUNT_URL="https://example.invalid/account"',
                            'MF_IMPORT_CSV_USER="user@example.com"',
                            'MF_IMPORT_CSV_PASSWORD="dummy-hidden-value"',
                            'MF_IMPORT_CSV_BROWSER_ENGINE="playwright"',
                        ]
                    )
                    + "\n",
                    encoding="utf_8",
                )

                output = io.StringIO()
                with redirect_stdout(output):
                    run_show_config()
            finally:
                os.chdir(current_dir)

            displayed = output.getvalue()
            self.assertIn("MF_IMPORT_CSV_ACCOUNT_URL: 設定済み", displayed)
            self.assertIn("MF_IMPORT_CSV_USER: user@example.com", displayed)
            self.assertIn("MF_IMPORT_CSV_PASSWORD: 設定済み（非表示）", displayed)
            self.assertNotIn("dummy-hidden-value", displayed)
            self.assertNotIn("example.invalid", displayed)

    def test_show_config_reports_missing_file_as_unset(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            current_dir = os.getcwd()
            try:
                os.chdir(temp_dir)
                output = io.StringIO()
                with redirect_stdout(output):
                    run_show_config()
            finally:
                os.chdir(current_dir)

            self.assertIn("MF_IMPORT_CSV_PASSWORD: 未設定", output.getvalue())
            self.assertIn("設定ファイル: .env", output.getvalue())


if __name__ == "__main__":
    unittest.main()
