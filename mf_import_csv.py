import argparse
import os
import sys

from account_aliases_generator import (
    DEFAULT_ACCOUNT_ALIASES_FILE,
    alias_to_account_id_map,
    load_account_aliases_data,
    normalize_account_aliases_data,
    set_account_alias,
    validate_alias,
    write_account_aliases,
)
from config import load_required_env
from config_setup import run_setup, run_show_config
from csv_validation import print_dry_run, print_validation_result, validate_csv
from browser_engine import generate_account_aliases, run_import


ACCOUNT_ALIASES_FILE = DEFAULT_ACCOUNT_ALIASES_FILE


def build_account_url(account_id, option_name="--account-id"):
    account_id = account_id.strip()
    if not account_id:
        raise ValueError(option_name + " must not be empty.")

    return "https://moneyforward.com/accounts/show_manual/" + account_id


def load_account_aliases(path=ACCOUNT_ALIASES_FILE):
    if not os.path.exists(path):
        raise ValueError(
            "--account was specified, but " + path + " does not exist. "
            "Create it from account_aliases.example.json."
        )

    return alias_to_account_id_map(load_account_aliases_data(path))


def resolve_account_alias(alias, path=ACCOUNT_ALIASES_FILE):
    alias = alias.strip()
    if not alias:
        raise ValueError("--account must not be empty.")

    aliases = load_account_aliases(path)
    if alias not in aliases:
        available_aliases = ", ".join(sorted(aliases.keys()))
        raise ValueError(
            "Account alias '"
            + alias
            + "' was not found in "
            + path
            + ". Available aliases: "
            + available_aliases
        )

    return aliases[alias]


def run_set_account_alias(account_id, alias, path=ACCOUNT_ALIASES_FILE):
    account = set_account_alias(account_id, alias, path)
    print("Updated account alias.")
    print(account["account_name"] + " -> " + account["alias"])


def run_edit_account_aliases(path=ACCOUNT_ALIASES_FILE, input_func=input):
    data = load_account_aliases_data(path)
    accounts = data["accounts"]
    if not accounts:
        raise ValueError(path + " does not contain any accounts.")

    print("手入力口座一覧")
    print("")
    for index, account in enumerate(accounts, start=1):
        print(
            str(index)
            + ". "
            + account["account_name"].ljust(30)
            + " alias: "
            + account["alias"]
        )

    selected = input_func("変更する口座番号を選択してください: ").strip()
    try:
        selected_index = int(selected)
    except ValueError as exc:
        raise ValueError("口座番号は数字で入力してください。") from exc
    if selected_index < 1 or selected_index > len(accounts):
        raise ValueError("口座番号が範囲外です。")

    account = accounts[selected_index - 1]
    print("現在のエイリアス: " + account["alias"])
    new_alias = input_func("新しいエイリアスを入力してください: ").strip()
    validate_alias(new_alias)
    updated = set_account_alias(account["account_id"], new_alias, path)

    print("")
    print("更新しました。")
    print(updated["account_name"] + " -> " + updated["alias"])


def parse_args():
    parser = argparse.ArgumentParser(
        description="MoneyForwardへCSVデータを登録します。"
    )
    parser.add_argument("input_file", nargs="?", help="読み込むCSVファイル")
    mode_group = parser.add_mutually_exclusive_group()
    mode_group.add_argument(
        "--setup",
        action="store_true",
        help=".envを対話形式で作成します。CSVファイルは不要です。",
    )
    mode_group.add_argument(
        "--show-config",
        action="store_true",
        help=".envの設定状態を安全に表示します。CSVファイルは不要です。",
    )
    mode_group.add_argument(
        "--generate-account-aliases",
        action="store_true",
        help=(
            "MoneyForwardの手入力口座一覧からaccount_aliases.jsonを生成します。"
            "CSVファイルは不要です。"
        ),
    )
    mode_group.add_argument(
        "--set-account-alias-id",
        nargs=2,
        metavar=("ACCOUNT_ID", "ALIAS"),
        help="account_aliases.jsonの手入力口座IDに対応するエイリアスを変更します。",
    )
    mode_group.add_argument(
        "--edit-account-aliases",
        action="store_true",
        help="account_aliases.jsonのエイリアスを対話形式で変更します。",
    )
    account_group = parser.add_mutually_exclusive_group()
    account_group.add_argument(
        "--account-id",
        help=(
            "手入力口座IDを指定します。指定時は"
            "MF_IMPORT_CSV_ACCOUNT_URLより優先されます。"
        ),
    )
    account_group.add_argument(
        "--account",
        help=(
            "account_aliases.jsonに定義した口座エイリアスを指定します。"
            "指定時はMF_IMPORT_CSV_ACCOUNT_URLより優先されます。"
        ),
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="CSVを検証し、登録予定内容だけを表示します。MoneyForwardへは登録しません。",
    )
    parser.add_argument(
        "--validate-only",
        action="store_true",
        help="CSV検証だけを行います。MoneyForwardへは接続しません。",
    )
    parser.add_argument(
        "--output",
        default=ACCOUNT_ALIASES_FILE,
        help="口座エイリアスファイルのパスです。未指定時はaccount_aliases.jsonです。",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="--generate-account-aliasesで既存の出力先を上書きします。",
    )
    return parser.parse_args()


def main():
    args = parse_args()
    if (args.setup or args.show_config) and (
        args.input_file is not None
        or args.account_id is not None
        or args.account is not None
        or args.dry_run
        or args.validate_only
        or args.output != ACCOUNT_ALIASES_FILE
        or args.force
    ):
        print(
            "--setup and --show-config cannot be combined with CSV import options.",
            file=sys.stderr,
        )
        return 1
    if args.dry_run and args.validate_only:
        print("--dry-run and --validate-only cannot be used together.", file=sys.stderr)
        return 1
    account_alias_maintenance_mode = (
        args.generate_account_aliases
        or args.set_account_alias_id is not None
        or args.edit_account_aliases
    )
    if account_alias_maintenance_mode and (
        args.input_file is not None
        or args.account_id is not None
        or args.account is not None
        or args.dry_run
        or args.validate_only
    ):
        print(
            "Account alias maintenance options cannot be combined with CSV import options.",
            file=sys.stderr,
        )
        return 1
    if not account_alias_maintenance_mode and (
        args.output != ACCOUNT_ALIASES_FILE or args.force
    ):
        print(
            "--output and --force can only be used with account alias maintenance options.",
            file=sys.stderr,
        )
        return 1
    if args.force and not args.generate_account_aliases:
        print("--force can only be used with --generate-account-aliases.", file=sys.stderr)
        return 1
    if args.setup:
        try:
            run_setup()
        except ValueError as exc:
            print(str(exc), file=sys.stderr)
            return 1
        return 0

    if args.show_config:
        run_show_config()
        return 0

    if not account_alias_maintenance_mode and args.input_file is None:
        print(
            "input_file is required unless --setup, --show-config, or "
            "an account alias maintenance option is used.",
            file=sys.stderr,
        )
        return 1

    if args.generate_account_aliases:
        try:
            env = load_required_env(require_account_url=False)
            aliases = generate_account_aliases(env)
            write_account_aliases(aliases, args.output, force=args.force)
        except (RuntimeError, ValueError) as exc:
            print(str(exc), file=sys.stderr)
            return 1

        account_count = len(normalize_account_aliases_data(aliases)["accounts"])
        print("Generated " + args.output + " with " + str(account_count) + " accounts.")
        return 0

    if args.set_account_alias_id is not None:
        try:
            account_id, alias = args.set_account_alias_id
            run_set_account_alias(account_id, alias, args.output)
        except ValueError as exc:
            print(str(exc), file=sys.stderr)
            return 1
        return 0

    if args.edit_account_aliases:
        try:
            run_edit_account_aliases(args.output)
        except ValueError as exc:
            print(str(exc), file=sys.stderr)
            return 1
        return 0

    account_url = None
    try:
        if args.account_id is not None:
            account_url = build_account_url(args.account_id)
        elif args.account is not None:
            account_id = resolve_account_alias(args.account)
            account_url = build_account_url(account_id, "--account")
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 1

    result = validate_csv(args.input_file)
    print_validation_result(result)

    if args.dry_run:
        print_dry_run(result)

    if result.errors:
        return 1

    if args.validate_only:
        print("Validate-only mode: MoneyForwardへの接続は行いません。")
        return 0

    if args.dry_run:
        return 0

    env = load_required_env(require_account_url=account_url is None)
    if account_url is not None:
        env["MF_IMPORT_CSV_ACCOUNT_URL"] = account_url

    run_import(args.input_file, result.entries, env)
    return 0


if __name__ == "__main__":
    sys.exit(main())
