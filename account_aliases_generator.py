import json
import os
import re
from urllib.parse import urlparse


DEFAULT_ACCOUNT_ALIASES_FILE = "account_aliases.json"
MANUAL_ACCOUNT_PATH_RE = re.compile(
    r"^/accounts/show_manual/([A-Za-z0-9_-]+)(?:[/?#].*)?$"
)


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

    for item in link_items:
        account_id = _extract_account_id(item.get("href", ""))
        if account_id is None or account_id in seen_ids:
            continue

        account_name = _normalize_account_name(item.get("text", ""))
        if not account_name:
            account_name = _normalize_account_name(item.get("container_text", ""))
        if not account_name:
            raise ValueError("手入力口座名を取得できないリンクがありました。")

        if account_name in aliases and aliases[account_name] != account_id:
            raise ValueError("同じ口座名の手入力口座が複数見つかりました: " + account_name)

        aliases[account_name] = account_id
        seen_ids.add(account_id)

    if not aliases:
        raise ValueError("手入力口座リンクが見つかりませんでした。")

    return dict(sorted(aliases.items()))


def write_account_aliases(aliases, output_path=DEFAULT_ACCOUNT_ALIASES_FILE, force=False):
    if os.path.exists(output_path) and not force:
        raise ValueError(
            output_path + " already exists. Use --force to overwrite or --output to choose another path."
        )

    try:
        with open(output_path, mode="w", encoding="utf_8") as f:
            json.dump(aliases, f, ensure_ascii=False, indent=2)
            f.write("\n")
    except OSError as exc:
        raise ValueError("Could not write " + output_path + ": " + str(exc)) from exc
