import os
import sys


ENV_FILE = ".env"
CONFIG_KEYS = [
    "MF_IMPORT_CSV_ACCOUNT_URL",
    "MF_IMPORT_CSV_USER",
    "MF_IMPORT_CSV_PASSWORD",
    "MF_IMPORT_CSV_BROWSER_ENGINE",
    "MF_IMPORT_CSV_BROWSER_HEADLESS",
    "MF_IMPORT_CSV_BROWSER_CHANNEL",
    "MF_IMPORT_CSV_REUSE_LOGIN_SESSION",
    "MF_IMPORT_CSV_BROWSER_PROFILE_DIR",
]
SENSITIVE_CONFIG_KEYS = {
    "MF_IMPORT_CSV_ACCOUNT_URL",
    "MF_IMPORT_CSV_USER",
    "MF_IMPORT_CSV_PASSWORD",
}


def _env_quote(value):
    escaped = value.replace("\\", "\\\\").replace('"', '\\"')
    return '"' + escaped + '"'


def _prompt_required(prompt, input_func=input):
    while True:
        value = input_func(prompt).strip()
        if value:
            return value
        print("値を入力してください。")


def _prompt_optional(prompt, default, input_func=input):
    suffix = " [" + default + "]: " if default else ": "
    value = input_func(prompt + suffix).strip()
    return value if value else default


def _prompt_bool(prompt, default=False, input_func=input):
    suffix = " [Y/n]: " if default else " [y/N]: "
    while True:
        value = input_func(prompt + suffix).strip().lower()
        if not value:
            return "true" if default else "false"
        if value in {"y", "yes"}:
            return "true"
        if value in {"n", "no"}:
            return "false"
        print("y または n を入力してください。")


def _prompt_browser_engine(input_func=input):
    while True:
        value = _prompt_optional(
            "ブラウザエンジンを選択してください [selenium/playwright]",
            "selenium",
            input_func,
        ).lower()
        if value in {"selenium", "playwright"}:
            return value
        print("selenium または playwright を入力してください。")


def write_setup_env(env_path=ENV_FILE, input_func=input, password_func=None):
    if password_func is None:
        from getpass import getpass

        password_func = getpass

    if os.path.exists(env_path):
        print(env_path + " は既に存在するため、上書きしません。")
        print("内容を変更する場合は、既存ファイルを手動で編集してください。")
        return 1

    values = {
        "MF_IMPORT_CSV_ACCOUNT_URL": _prompt_required(
            "インポート先口座URLを入力してください: ",
            input_func,
        ),
        "MF_IMPORT_CSV_USER": _prompt_required(
            "MoneyForwardログインユーザーを入力してください: ",
            input_func,
        ),
        "MF_IMPORT_CSV_PASSWORD": _prompt_required(
            "MoneyForwardパスワードを入力してください: ",
            password_func,
        ),
        "MF_IMPORT_CSV_BROWSER_ENGINE": _prompt_browser_engine(input_func),
        "MF_IMPORT_CSV_BROWSER_HEADLESS": _prompt_bool(
            "headlessで実行しますか？",
            default=False,
            input_func=input_func,
        ),
        "MF_IMPORT_CSV_BROWSER_CHANNEL": _prompt_optional(
            "ブラウザチャンネルを入力してください",
            "chromium",
            input_func,
        ),
        "MF_IMPORT_CSV_REUSE_LOGIN_SESSION": _prompt_bool(
            "ログインセッションを再利用しますか？",
            default=False,
            input_func=input_func,
        ),
        "MF_IMPORT_CSV_BROWSER_PROFILE_DIR": _prompt_optional(
            "ログイン状態保存先ディレクトリを入力してください",
            ".auth/moneyforward-playwright",
            input_func,
        ),
    }

    try:
        with open(env_path, mode="x", encoding="utf_8") as f:
            for key in CONFIG_KEYS:
                f.write(key + "=" + _env_quote(values[key]) + "\n")
    except FileExistsError:
        print(env_path + " は既に存在するため、上書きしません。")
        return 1
    except OSError as exc:
        print(env_path + " を作成できませんでした: " + str(exc), file=sys.stderr)
        return 1

    print(env_path + " を作成しました。")
    print("認証情報を含むため、Gitに追加しないでください。")
    return 0


def _format_config_value(key, value):
    if not value:
        return "未設定"
    if key == "MF_IMPORT_CSV_PASSWORD":
        return "設定済み（非表示）"
    if key in SENSITIVE_CONFIG_KEYS:
        return "設定済み"
    return value


def _parse_env_value(value):
    value = value.strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {'"', "'"}:
        value = value[1:-1]
    return value.replace('\\"', '"').replace("\\\\", "\\")


def _read_env_file(env_path):
    values = {}
    try:
        with open(env_path, mode="r", encoding="utf_8") as f:
            for line in f:
                stripped = line.strip()
                if not stripped or stripped.startswith("#") or "=" not in stripped:
                    continue
                key, value = stripped.split("=", 1)
                values[key.strip()] = _parse_env_value(value)
    except OSError:
        return {}
    return values


def show_config(env_path=ENV_FILE):
    values = _read_env_file(env_path) if os.path.exists(env_path) else {}

    print("現在の設定:")
    print("")
    for key in CONFIG_KEYS:
        print(key + ": " + _format_config_value(key, values.get(key)))
    print("")
    print("設定ファイル: " + env_path)
    if not os.path.exists(env_path):
        print("設定ファイルはまだ作成されていません。")
    return 0


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


def load_required_env(require_account_url=True):
    from dotenv import load_dotenv

    load_dotenv()
    required_env_vars = {
        "MF_IMPORT_CSV_USER": os.getenv("MF_IMPORT_CSV_USER"),
        "MF_IMPORT_CSV_PASSWORD": os.getenv("MF_IMPORT_CSV_PASSWORD"),
    }
    account_url = os.getenv("MF_IMPORT_CSV_ACCOUNT_URL")
    if require_account_url:
        required_env_vars["MF_IMPORT_CSV_ACCOUNT_URL"] = account_url

    missing_env_vars = [name for name, value in required_env_vars.items() if not value]
    if missing_env_vars:
        print(
            "Missing required environment variables: " + ", ".join(missing_env_vars),
            file=sys.stderr,
        )
        sys.exit(1)

    required_env_vars.update(
        {
            "MF_IMPORT_CSV_ACCOUNT_URL": account_url,
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
            "MF_IMPORT_CSV_REUSE_LOGIN_SESSION": _parse_bool(
                os.getenv("MF_IMPORT_CSV_REUSE_LOGIN_SESSION"),
                default=False,
            ),
            "MF_IMPORT_CSV_BROWSER_PROFILE_DIR": os.getenv(
                "MF_IMPORT_CSV_BROWSER_PROFILE_DIR",
                ".auth/moneyforward-playwright",
            ).strip()
            or ".auth/moneyforward-playwright",
        }
    )

    return required_env_vars
