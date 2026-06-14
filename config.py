import os
import sys


def _parse_bool(value, default=False):
    if value is None or value == "":
        return default

    normalized = value.strip().lower()
    if normalized in {"1", "true", "yes", "on"}:
        return True
    if normalized in {"0", "false", "no", "off"}:
        return False

    print(
        "Invalid boolean environment variable value: " + value,
        file=sys.stderr,
    )
    sys.exit(1)


def load_required_env():
    from dotenv import load_dotenv

    load_dotenv()
    required_env_vars = {
        "MF_IMPORT_CSV_ACCOUNT_URL": os.getenv("MF_IMPORT_CSV_ACCOUNT_URL"),
        "MF_IMPORT_CSV_USER": os.getenv("MF_IMPORT_CSV_USER"),
        "MF_IMPORT_CSV_PASSWORD": os.getenv("MF_IMPORT_CSV_PASSWORD"),
    }

    missing_env_vars = [name for name, value in required_env_vars.items() if not value]
    if missing_env_vars:
        print(
            "Missing required environment variables: " + ", ".join(missing_env_vars),
            file=sys.stderr,
        )
        sys.exit(1)

    required_env_vars.update(
        {
            "MF_IMPORT_CSV_BROWSER_ENGINE": os.getenv(
                "MF_IMPORT_CSV_BROWSER_ENGINE", "selenium"
            ).strip()
            or "selenium",
            "MF_IMPORT_CSV_BROWSER_HEADLESS": _parse_bool(
                os.getenv("MF_IMPORT_CSV_BROWSER_HEADLESS"),
                default=False,
            ),
            "MF_IMPORT_CSV_BROWSER_CHANNEL": os.getenv(
                "MF_IMPORT_CSV_BROWSER_CHANNEL", ""
            ).strip(),
        }
    )

    return required_env_vars
