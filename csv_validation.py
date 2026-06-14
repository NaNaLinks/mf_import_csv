import csv
import os
import sys
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
                    errors.append(f"[{line_number}] invalid amount: {amount_value}")
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
