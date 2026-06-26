import argparse
import json
import os
import sys

from account_aliases_generator import (
    DEFAULT_ACCOUNT_ALIASES_FILE,
    write_account_aliases,
)
from config import load_required_env
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

    try:
        with open(path, mode="r", encoding="utf_8") as f:
            aliases = json.load(f)
    except json.JSONDecodeError as exc:
        raise ValueError(path + " is not valid JSON: " + str(exc)) from exc
    except OSError as exc:
        raise ValueError("Could not read " + path + ": " + str(exc)) from exc

    if not isinstance(aliases, dict):
        raise ValueError(path + " must contain a JSON object of alias to account ID.")

    normalized_aliases = {}
    for alias, account_id in aliases.items():
        if not isinstance(alias, str) or not isinstance(account_id, str):
            raise ValueError(path + " aliases and account IDs must be strings.")

        stripped_alias = alias.strip()
        stripped_account_id = account_id.strip()
        if not stripped_alias:
            raise ValueError(path + " contains an empty alias.")
        if not stripped_account_id:
            raise ValueError(
                path + " alias '" + stripped_alias + "' has an empty account ID."
            )

        normalized_aliases[stripped_alias] = stripped_account_id

    return normalized_aliases


def resolve_account_alias(alias, path=ACCOUNT_ALIASES_FILE):
    alias = alias.strip()
    if not alias:
        raise ValueError("--account must not be empty.")

    aliases = load_account_aliases(path)
    if alias not in aliases:
        raise ValueError(
            "Account alias '" + alias + "' was not found in " + path + "."
        )

    return aliases[alias]


def parse_args():
    parser = argparse.ArgumentParser(
        description="MoneyForwardへCSVデータを登録します。"
    )
    parser.add_argument("input_file", nargs="?", help="読み込むCSVファイル")
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
        "--generate-account-aliases",
        action="store_true",
        help=(
            "MoneyForwardの手入力口座一覧からaccount_aliases.jsonを生成します。"
            "CSVファイルは不要です。"
        ),
    )
    parser.add_argument(
        "--output",
        default=ACCOUNT_ALIASES_FILE,
        help="--generate-account-aliasesの出力先です。未指定時はaccount_aliases.jsonです。",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="--generate-account-aliasesで既存の出力先を上書きします。",
    )
    return parser.parse_args()


def main():
    args = parse_args()
    if args.dry_run and args.validate_only:
        print("--dry-run and --validate-only cannot be used together.", file=sys.stderr)
        return 1
    if args.generate_account_aliases and (
        args.input_file is not None
        or args.account_id is not None
        or args.account is not None
        or args.dry_run
        or args.validate_only
    ):
        print(
            "--generate-account-aliases cannot be combined with CSV import options.",
            file=sys.stderr,
        )
        return 1
    if not args.generate_account_aliases and (
        args.output != ACCOUNT_ALIASES_FILE or args.force
    ):
        print(
            "--output and --force can only be used with --generate-account-aliases.",
            file=sys.stderr,
        )
        return 1
    if not args.generate_account_aliases and args.input_file is None:
        print(
            "input_file is required unless --generate-account-aliases is used.",
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

        print("Generated " + args.output + " with " + str(len(aliases)) + " accounts.")
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
