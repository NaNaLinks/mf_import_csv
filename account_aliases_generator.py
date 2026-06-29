import json
import os
import re
import unicodedata
from datetime import datetime, timezone
from urllib.parse import urlparse


DEFAULT_ACCOUNT_ALIASES_FILE = "account_aliases.json"
ACCOUNT_ALIASES_FORMAT_VERSION = 1
MANUAL_ACCOUNT_PATH_RE = re.compile(
    r"^/accounts/show_manual/([A-Za-z0-9_-]+)(?:[/?#].*)?$"
)
VALID_ALIAS_RE = re.compile(r"^[0-9A-Za-z_\u3040-\u30ff\u3400-\u9fff]+$")
JAPANESE_ALIAS_WORDS = {
    "アカウント": "account",
    "口座": "account",
    "ギフト": "gift",
    "カード": "card",
    "ポイント": "point",
    "現金": "cash",
    "財布": "wallet",
}


def _extract_account_id(href):
    if not href:
        return None

    parsed = urlparse(href)
    path = parsed.path if parsed.scheme or parsed.netloc else href.split("?", 1)[0].split("#", 1)[0]
    match = MANUAL_ACCOUNT_PATH_RE.match(path)
    if match is None:
        return None

    return match.group(1)


def _normalize_account_name(text):
    if text is None:
        return ""

    lines = [line.strip() for line in text.splitlines()]
    return next((line for line in lines if line), "")


def _utc_timestamp():
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _sort_accounts(accounts):
    return sorted(
        accounts,
        key=lambda item: (item.get("alias", ""), item.get("account_name", "")),
    )


def _ensure_string(value, field_name):
    if not isinstance(value, str):
        raise ValueError(field_name + " must be a string.")
    return value.strip()


def validate_alias(alias):
    alias = _ensure_string(alias, "alias")
    if not alias:
        raise ValueError("alias must not be empty.")
    if alias.startswith("_") or alias.endswith("_"):
        raise ValueError("alias must not start or end with underscore.")
    if "__" in alias:
        raise ValueError("alias must not contain consecutive underscores.")
    if VALID_ALIAS_RE.match(alias) is None:
        raise ValueError(
            "alias can contain letters, numbers, underscores, and Japanese characters only."
        )
    return alias


def _translated_name_for_alias(account_name):
    normalized = unicodedata.normalize("NFKC", account_name)
    for source, replacement in JAPANESE_ALIAS_WORDS.items():
        normalized = normalized.replace(source, "_" + replacement + "_")
    return normalized


def generate_alias_candidate(account_name):
    text = _translated_name_for_alias(account_name)
    text = text.lower()
    parts = []
    current = []
    for char in text:
        category = unicodedata.category(char)
        if char.isascii() and char.isalnum():
            current.append(char)
        elif char == "_":
            if current:
                parts.append("".join(current))
                current = []
        elif not char.isascii() and (
            "\u3040" <= char <= "\u30ff" or "\u3400" <= char <= "\u9fff"
        ):
            if not any(part.isascii() for part in parts + current):
                current.append(char)
            elif current and not "".join(current).isascii():
                parts.append("".join(current))
                current = []
        elif category.startswith("Z") or category.startswith("P"):
            if current:
                parts.append("".join(current))
                current = []
        elif category.startswith("S") or category.startswith("C") or category.startswith("M"):
            if current:
                parts.append("".join(current))
                current = []
        else:
            if current:
                parts.append("".join(current))
                current = []

    if current:
        parts.append("".join(current))

    ascii_parts = [part for part in parts if part.isascii()]
    selected_parts = ascii_parts or parts
    alias = "_".join(part for part in selected_parts if part)
    alias = re.sub(r"_+", "_", alias).strip("_")
    if not alias:
        alias = "account"
    return validate_alias(alias)


def _dedupe_alias(base_alias, used_aliases):
    alias = base_alias
    suffix = 2
    while alias in used_aliases:
        alias = base_alias + "_" + str(suffix)
        suffix += 1
    used_aliases.add(alias)
    return alias


def _record_from_alias_mapping(alias, account_id):
    alias = validate_alias(alias)
    account_id = _ensure_string(account_id, "account_id")
    if not account_id:
        raise ValueError("account_id must not be empty.")
    return {
        "account_name": alias,
        "account_id": account_id,
        "alias": alias,
        "alias_source": "legacy",
    }


def _record_from_account_data(item):
    if not isinstance(item, dict):
        raise ValueError("account entries must be JSON objects.")

    account_name = _ensure_string(item.get("account_name", ""), "account_name")
    account_id = _ensure_string(item.get("account_id", ""), "account_id")
    alias = validate_alias(item.get("alias", ""))
    if not account_name:
        raise ValueError("account_name must not be empty.")
    if not account_id:
        raise ValueError("account_id must not be empty.")

    record = {
        "account_name": account_name,
        "account_id": account_id,
        "alias": alias,
        "alias_source": item.get("alias_source", "auto"),
    }
    if item.get("updated_at"):
        record["updated_at"] = _ensure_string(item.get("updated_at"), "updated_at")
    return record


def normalize_account_aliases_data(data):
    if not isinstance(data, dict):
        raise ValueError("account aliases file must contain a JSON object.")

    if "accounts" in data:
        accounts = [_record_from_account_data(item) for item in data.get("accounts", [])]
    else:
        accounts = [
            _record_from_alias_mapping(alias, account_id)
            for alias, account_id in data.items()
        ]

    seen_aliases = {}
    seen_ids = {}
    for account in accounts:
        alias = account["alias"]
        account_id = account["account_id"]
        if alias in seen_aliases and seen_aliases[alias] != account_id:
            raise ValueError("duplicate alias found: " + alias)
        if account_id in seen_ids and seen_ids[account_id] != alias:
            raise ValueError("duplicate account_id found: " + account_id)
        seen_aliases[alias] = account_id
        seen_ids[account_id] = alias

    return {"version": ACCOUNT_ALIASES_FORMAT_VERSION, "accounts": _sort_accounts(accounts)}


def load_account_aliases_data(path=DEFAULT_ACCOUNT_ALIASES_FILE):
    if not os.path.exists(path):
        raise ValueError(path + " does not exist.")

    try:
        with open(path, mode="r", encoding="utf_8") as f:
            data = json.load(f)
    except json.JSONDecodeError as exc:
        raise ValueError(path + " is not valid JSON: " + str(exc)) from exc
    except OSError as exc:
        raise ValueError("Could not read " + path + ": " + str(exc)) from exc

    return normalize_account_aliases_data(data)


def alias_to_account_id_map(data):
    normalized = normalize_account_aliases_data(data)
    return {
        account["alias"]: account["account_id"]
        for account in normalized["accounts"]
    }


def format_account_aliases(accounts):
    return {
        "version": ACCOUNT_ALIASES_FORMAT_VERSION,
        "accounts": _sort_accounts(accounts),
    }


def _merge_existing_accounts(generated_accounts, existing_accounts):
    existing_by_id = {item["account_id"]: item for item in existing_accounts}
    used_aliases = {
        item["alias"]
        for item in existing_accounts
        if item.get("alias_source") in ("manual", "legacy")
    }
    merged = []

    for generated in generated_accounts:
        existing = existing_by_id.get(generated["account_id"])
        if existing and existing.get("alias_source") in ("manual", "legacy"):
            account = dict(generated)
            account["alias"] = existing["alias"]
            account["alias_source"] = "manual"
            if existing.get("updated_at"):
                account["updated_at"] = existing["updated_at"]
        else:
            account = dict(generated)
            account["alias"] = _dedupe_alias(account["alias"], used_aliases)
        merged.append(account)

    return merged


def set_account_alias(account_id, alias, path=DEFAULT_ACCOUNT_ALIASES_FILE):
    data = load_account_aliases_data(path)
    account_id = _ensure_string(account_id, "account_id")
    alias = validate_alias(alias)
    if not account_id:
        raise ValueError("account_id must not be empty.")

    accounts = data["accounts"]
    target = None
    for account in accounts:
        if account["account_id"] == account_id:
            target = account
        elif account["alias"] == alias:
            raise ValueError("alias '" + alias + "' is already used by another account.")

    if target is None:
        raise ValueError("account_id was not found in " + path + ".")

    target["alias"] = alias
    target["alias_source"] = "manual"
    target["updated_at"] = _utc_timestamp()
    write_account_aliases_data(data, path)
    return target


def write_account_aliases_data(data, output_path=DEFAULT_ACCOUNT_ALIASES_FILE):
    normalized = normalize_account_aliases_data(data)
    try:
        with open(output_path, mode="w", encoding="utf_8") as f:
            json.dump(normalized, f, ensure_ascii=False, indent=2)
            f.write("\n")
    except OSError as exc:
        raise ValueError("Could not write " + output_path + ": " + str(exc)) from exc


def describe_manual_account_link_candidates(link_items):
    candidates = []
    aliases = {}
    seen_ids = set()

    for index, item in enumerate(link_items, start=1):
        href = item.get("href", "")
        account_id = _extract_account_id(href)
        account_name = _normalize_account_name(item.get("text", ""))
        if not account_name:
            account_name = _normalize_account_name(item.get("container_text", ""))

        status = "accepted"
        reason = ""
        if account_id is None:
            status = "rejected"
            reason = "manual_account_href_not_matched"
        elif account_id in seen_ids:
            status = "rejected"
            reason = "duplicate_account_id"
        elif not account_name:
            status = "rejected"
            reason = "account_name_empty"
        elif account_name in aliases and aliases[account_name] != account_id:
            status = "rejected"
            reason = "duplicate_account_name"

        if status == "accepted":
            aliases[account_name] = account_id
            seen_ids.add(account_id)

        candidates.append(
            {
                "index": index,
                "href": href,
                "text": item.get("text", ""),
                "container_text": item.get("container_text", ""),
                "account_id": account_id or "",
                "account_name": account_name,
                "status": status,
                "reason": reason,
            }
        )

    return candidates


def extract_manual_account_aliases(link_items):
    aliases = {}
    seen_ids = set()
    used_aliases = set()

    for item in link_items:
        account_id = _extract_account_id(item.get("href", ""))
        if account_id is None or account_id in seen_ids:
            continue

        account_name = _normalize_account_name(item.get("text", ""))
        if not account_name:
            account_name = _normalize_account_name(item.get("container_text", ""))
        if not account_name:
            raise ValueError("手入力口座名を取得できないリンクがありました。")

        if account_name in aliases and aliases[account_name]["account_id"] != account_id:
            raise ValueError("同じ口座名の手入力口座が複数見つかりました: " + account_name)

        alias = _dedupe_alias(generate_alias_candidate(account_name), used_aliases)
        aliases[account_name] = {
            "account_name": account_name,
            "account_id": account_id,
            "alias": alias,
            "alias_source": "auto",
        }
        seen_ids.add(account_id)

    if not aliases:
        raise ValueError("手入力口座リンクが見つかりませんでした。")

    return format_account_aliases(aliases.values())


def write_account_aliases(aliases, output_path=DEFAULT_ACCOUNT_ALIASES_FILE, force=False):
    if os.path.exists(output_path) and not force:
        raise ValueError(
            output_path
            + " already exists. Use --force to overwrite or --output to choose another path."
        )
    data = normalize_account_aliases_data(aliases)

    if os.path.exists(output_path) and force:
        existing_data = load_account_aliases_data(output_path)
        data = format_account_aliases(
            _merge_existing_accounts(data["accounts"], existing_data["accounts"])
        )

    try:
        with open(output_path, mode="w", encoding="utf_8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
            f.write("\n")
    except OSError as exc:
        raise ValueError("Could not write " + output_path + ": " + str(exc)) from exc
