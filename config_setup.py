import getpass
import json
import os
import shlex


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

SECRET_KEYS = {"MF_IMPORT_CSV_PASSWORD"}
MASKED_VALUE_KEYS = {"MF_IMPORT_CSV_ACCOUNT_URL"}


def _format_env_value(value):
    return json.dumps(value, ensure_ascii=False)


def _prompt_text(prompt, default="", input_func=input):
    suffix = ""
    if default:
        suffix = " [" + default + "]"
    value = input_func(prompt + suffix + ": ").strip()
    if value:
        return value
    return default


def _prompt_choice(prompt, choices, default, input_func=input):
    choices_text = "/".join(choices)
    while True:
        value = _prompt_text(prompt + " [" + choices_text + "]", default, input_func)
        if value in choices:
            return value
        print("次のいずれかを入力してください: " + choices_text)


def _prompt_bool(prompt, default=False, input_func=input):
    default_hint = "Y/n" if default else "y/N"
    while True:
        value = input_func(prompt + " [" + default_hint + "]: ").strip().lower()
        if not value:
            return "true" if default else "false"
        if value in {"y", "yes"}:
            return "true"
        if value in {"n", "no"}:
            return "false"
        print("y または n を入力してください。")


def collect_setup_values(input_func=input, password_func=getpass.getpass):
    values = {
        "MF_IMPORT_CSV_USER": _prompt_text(
            "MoneyForwardログインユーザーを入力してください",
            input_func=input_func,
        ),
        "MF_IMPORT_CSV_PASSWORD": password_func(
            "MoneyForwardパスワードを入力してください: "
        ).strip(),
        "MF_IMPORT_CSV_ACCOUNT_URL": _prompt_text(
            "インポート先口座URLを入力してください",
            input_func=input_func,
        ),
        "MF_IMPORT_CSV_BROWSER_ENGINE": _prompt_choice(
            "ブラウザエンジンを選択してください",
            ["selenium", "playwright"],
            "selenium",
            input_func=input_func,
        ),
        "MF_IMPORT_CSV_BROWSER_HEADLESS": _prompt_bool(
            "headlessで実行しますか？",
            default=False,
            input_func=input_func,
        ),
        "MF_IMPORT_CSV_BROWSER_CHANNEL": _prompt_text(
            "ブラウザチャンネルを入力してください",
            default="chromium",
            input_func=input_func,
        ),
        "MF_IMPORT_CSV_REUSE_LOGIN_SESSION": _prompt_bool(
            "ログインセッションを再利用しますか？",
            default=False,
            input_func=input_func,
        ),
        "MF_IMPORT_CSV_BROWSER_PROFILE_DIR": _prompt_text(
            "ブラウザプロファイル保存先を入力してください",
            default=".auth/moneyforward-playwright",
            input_func=input_func,
        ),
    }

    return values


def write_env_file(values, env_file=ENV_FILE):
    if os.path.exists(env_file):
        raise ValueError(
            env_file
            + " already exists. Existing settings were not overwritten. "
            "Edit it manually if you need to change settings."
        )

    lines = []
    for key in CONFIG_KEYS:
        lines.append(key + "=" + _format_env_value(values.get(key, "")))

    with open(env_file, mode="w", encoding="utf_8") as f:
        f.write("\n".join(lines) + "\n")


def run_setup(env_file=ENV_FILE, input_func=input, password_func=getpass.getpass):
    if os.path.exists(env_file):
        raise ValueError(
            env_file
            + " already exists. Existing settings were not overwritten. "
            "Edit it manually if you need to change settings."
        )

    values = collect_setup_values(
        input_func=input_func,
        password_func=password_func,
    )
    write_env_file(values, env_file=env_file)
    print("設定ファイルを作成しました: " + env_file)


def _load_env_values(env_file=ENV_FILE):
    if not os.path.exists(env_file):
        return {}

    try:
        from dotenv import dotenv_values
    except ModuleNotFoundError:
        return _load_env_values_without_dotenv(env_file)

    return {key: value for key, value in dotenv_values(env_file).items() if value}


def _load_env_values_without_dotenv(env_file):
    values = {}
    with open(env_file, mode="r", encoding="utf_8") as f:
        for line in f:
            stripped = line.strip()
            if not stripped or stripped.startswith("#") or "=" not in stripped:
                continue

            key, value = stripped.split("=", 1)
            key = key.strip()
            if key not in CONFIG_KEYS:
                continue

            value = value.strip()
            try:
                parsed = shlex.split(value, posix=True)
            except ValueError:
                values[key] = value
                continue
            values[key] = parsed[0] if parsed else ""

    return values


def _display_value(key, value):
    if not value:
        return "未設定"
    if key in SECRET_KEYS:
        return "設定済み（非表示）"
    if key in MASKED_VALUE_KEYS:
        return "設定済み"
    return value


def run_show_config(env_file=ENV_FILE):
    values = _load_env_values(env_file)

    print("現在の設定:")
    print("")
    for key in CONFIG_KEYS:
        print(key + ": " + _display_value(key, values.get(key, "")))
    print("")
    print("設定ファイル: " + env_file)
