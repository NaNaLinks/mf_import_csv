import os
import sys


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

    return required_env_vars
