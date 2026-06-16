import argparse
import sys

from config import load_required_env
from csv_validation import print_dry_run, print_validation_result, validate_csv
from browser_engine import run_import


def build_account_url(account_id):
    account_id = account_id.strip()
    if not account_id:
        raise ValueError("--account-id must not be empty.")

    return "https://moneyforward.com/accounts/show_manual/" + account_id


def parse_args():
    parser = argparse.ArgumentParser(
        description="MoneyForwardへCSVデータを登録します。"
    )
    parser.add_argument("input_file", help="読み込むCSVファイル")
    parser.add_argument(
        "--account-id",
        help=(
            "手入力口座IDを指定します。指定時は"
            "MF_IMPORT_CSV_ACCOUNT_URLより優先されます。"
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
    return parser.parse_args()


def main():
    args = parse_args()
    if args.dry_run and args.validate_only:
        print("--dry-run and --validate-only cannot be used together.", file=sys.stderr)
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

    env = load_required_env(require_account_url=args.account_id is None)
    if args.account_id is not None:
        try:
            env["MF_IMPORT_CSV_ACCOUNT_URL"] = build_account_url(args.account_id)
        except ValueError as exc:
            print(str(exc), file=sys.stderr)
            return 1

    run_import(args.input_file, result.entries, env)
    return 0


if __name__ == "__main__":
    sys.exit(main())
