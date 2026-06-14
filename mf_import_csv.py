import argparse
import csv
import os
import sys
import time
from dataclasses import dataclass
from datetime import datetime
from typing import List

REQUIRED_COLUMN_COUNT = 10
SKIP_MARKERS = {"#", "0", "計算対象"}


@dataclass
class CsvEntry:
    line_number: int
    row: List[str]
    amount: int

    @property
    def entry_type(self) -> str:
        return "収入" if self.amount > 0 else "支出"

    @property
    def display_amount(self) -> int:
        return abs(self.amount)


@dataclass
class CsvValidationResult:
    entries: List[CsvEntry]
    skipped: int
    errors: List[str]
    warnings: List[str]


def parse_args():
    parser = argparse.ArgumentParser(
        description="MoneyForwardへCSVデータを登録します。"
    )
    parser.add_argument("input_file", help="読み込むCSVファイル")
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


def validate_csv(input_file):
    entries = []
    errors = []
    warnings = []
    skipped = 0

    if not os.path.exists(input_file):
        return CsvValidationResult(
            entries=[],
            skipped=0,
            errors=[f"CSV file does not exist: {input_file}"],
            warnings=[],
        )

    try:
        with open(input_file, mode="r", encoding="utf_8", newline="") as f:
            reader = csv.reader(f)
            for line_number, row in enumerate(reader, start=1):
                if not row:
                    skipped += 1
                    continue

                marker = row[0].strip()
                if marker in SKIP_MARKERS:
                    skipped += 1
                    continue

                if len(row) < REQUIRED_COLUMN_COUNT:
                    errors.append(
                        f"[{line_number}] column count is {len(row)}; "
                        f"expected at least {REQUIRED_COLUMN_COUNT}"
                    )
                    continue

                date_value = row[1].strip()
                try:
                    datetime.strptime(date_value, "%Y/%m/%d")
                except ValueError:
                    errors.append(
                        f"[{line_number}] invalid date format: {date_value} "
                        "(expected YYYY/MM/DD)"
                    )

                amount_value = row[3].strip()
                try:
                    amount = int(amount_value)
                except ValueError:
                    errors.append(
                        f"[{line_number}] invalid amount: {amount_value}"
                    )
                    continue

                if amount == 0:
                    errors.append(f"[{line_number}] amount must not be 0")
                    continue

                entries.append(CsvEntry(line_number=line_number, row=row, amount=amount))
    except csv.Error as exc:
        errors.append(f"CSV read error: {exc}")
    except UnicodeDecodeError as exc:
        errors.append(f"CSV encoding error: {exc}")
    except OSError as exc:
        errors.append(f"CSV read error: {exc}")

    return CsvValidationResult(
        entries=entries,
        skipped=skipped,
        errors=errors,
        warnings=warnings,
    )


def print_validation_result(result):
    if result.errors:
        print("CSV validation failed.", file=sys.stderr)
        for error in result.errors:
            print(f"ERROR: {error}", file=sys.stderr)
    else:
        print("CSV validation succeeded.")

    for warning in result.warnings:
        print(f"WARNING: {warning}", file=sys.stderr)


def print_dry_run(result):
    print("Dry-run mode: MoneyForwardへの登録は行いません。")
    for entry in result.entries:
        row = entry.row
        print(
            f"[{entry.line_number}] {entry.entry_type} {row[1]} {entry.amount} "
            f"内容: {row[2]} 大項目: {row[5]} 中項目: {row[6]}"
        )
    print("Summary:")
    print(f"- target: {len(result.entries)}")
    print(f"- skipped: {result.skipped}")
    print(f"- errors: {len(result.errors)}")
    print(f"- warnings: {len(result.warnings)}")


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


def import_selenium():
    from selenium import webdriver
    from selenium.common.exceptions import TimeoutException
    from selenium.webdriver.common.by import By
    from selenium.webdriver.common.keys import Keys
    from selenium.webdriver.support import expected_conditions as EC
    from selenium.webdriver.support.ui import WebDriverWait

    return webdriver, Keys, By, WebDriverWait, EC, TimeoutException


def run_import(input_file, entries, env):
    webdriver, Keys, By, WebDriverWait, EC, TimeoutException = import_selenium()

    url = env["MF_IMPORT_CSV_ACCOUNT_URL"]
    user = env["MF_IMPORT_CSV_USER"]
    password = env["MF_IMPORT_CSV_PASSWORD"]
    driver = None

    try:
        print("Start :" + input_file)

        # Chromeブラウザを立ち上げる
        options = webdriver.ChromeOptions()
        # Windowsでは NUL, mac/linuxでは /dev/null にログを捨てる
        options.add_argument("--log-level=3")
        options.add_experimental_option("excludeSwitches", ["enable-logging"])
        driver = webdriver.Chrome(options=options)
        driver.implicitly_wait(10)  # wait
        # マネーフォワードの銀行ページに遷移
        driver.get(url)

        # アカウント入力
        elem = driver.find_element(By.ID, "mfid_user[email]")
        elem.clear()
        elem.send_keys(user, Keys.ENTER)

        # パスワード入力
        elem = driver.find_element(By.ID, "mfid_user[password]")
        elem.clear()
        elem.send_keys(password, Keys.ENTER)

        # ここでOTP入力画面が出る場合があるので対応
        optauth = False
        try:
            otp_elem = WebDriverWait(driver, 2).until(
                EC.presence_of_element_located((By.NAME, "otp_attempt"))
            )
            otp_code = input("２段階認証コードを入力してください: ")
            otp_elem.clear()
            otp_elem.send_keys(otp_code, Keys.ENTER)
            print("２段階認証コードを送信しました。")
            optauth = True
        except TimeoutException:
            # OTPフォームが出てこなければそのまま先へ
            print("２段階認証コード入力画面が表示されませんでした。")

        # 2段階認証無効時は追加認証画面が出てくる場合がある
        if optauth is False:
            try:
                otp_elem = WebDriverWait(driver, 2).until(
                    EC.presence_of_element_located((By.NAME, "email_otp"))
                )
                otp_code = input("追加認証コードを入力してください: ")
                otp_elem.clear()
                otp_elem.send_keys(otp_code, Keys.ENTER)
                print("追加認証コードを送信しました。")
            except TimeoutException:
                # OTPフォームが出てこなければそのまま先へ
                print("追加認証コード入力画面は表示されませんでした。")

        for entry in entries:
            row = entry.row
            n = entry.line_number
            print("Start line[" + str(n) + "]")

            # 「手入力」ボタンクリック
            elem = driver.find_element(By.CLASS_NAME, "cf-new-btn")
            elem.click()

            # 金額入力
            if entry.amount > 0:
                # "金額（円）" > 0 ならば収入
                print("[" + str(n) + "] " + "Plus! :")
                print(row)
                amount = entry.amount

                # click Plus
                elem = driver.find_element(By.CLASS_NAME, "plus-payment")
                elem.click()
            else:
                # "金額（円）" < 0 ならば支出
                print("[" + str(n) + "] " + "Minus! :")
                print(row)
                amount = entry.amount * -1

            # 日付（YYYY/MM/DD）
            elem = driver.find_element(By.ID, "updated-at")
            elem.clear()
            time.sleep(0.5)
            elem.send_keys(row[1])
            elem.click()
            elem.click()
            time.sleep(0.5)

            # 金額
            elem = driver.find_element(By.ID, "appendedPrependedInput")
            elem.clear()
            elem.send_keys(amount)

            # 大項目
            if row[5] != "未分類":
                elem = driver.find_element(By.ID, "js-large-category-selected")
                elem.click()
                elem = driver.find_element(By.LINK_TEXT, row[5])
                elem.click()

            # 中項目
            if row[6] != "未分類":
                sub_category = row[6]
                if sub_category[0] == "'":
                    sub_category = sub_category[1:]

                print("sub_category:" + sub_category)
                elem = driver.find_element(By.ID, "js-middle-category-selected")
                elem.click()
                elem = driver.find_element(By.LINK_TEXT, sub_category)
                elem.click()

            # 内容
            if row[7] == "":
                content = row[2]
            else:
                content = row[2] + "（" + row[7] + "）"

            content = content[0:50]
            elem = driver.find_element(By.ID, "js-content-field")
            elem.clear()
            elem.send_keys(content)

            # 「保存」ボタンクリック
            time.sleep(1)
            elem = driver.find_element(By.ID, "submit-button")

            # （以下、テストコード）Closeボタン「×」をクリックして保存しない
            # time.sleep(3)
            # elem = driver.find_element(By.CLASS_NAME,"close")

            elem.click()
            time.sleep(5)

    finally:
        print("End :" + input_file)
        if driver is not None:
            driver.quit()


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

    env = load_required_env()
    run_import(args.input_file, result.entries, env)
    return 0


if __name__ == "__main__":
    sys.exit(main())
