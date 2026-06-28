import sys
from datetime import datetime
from pathlib import Path


DEBUG_LOG_ROOT = Path("logs") / "debug"


def _safe_text(value):
    if value is None:
        return ""
    return str(value)


def _write_text(path, content):
    path.write_text(_safe_text(content), encoding="utf_8")


def _format_links(link_items):
    if not link_items:
        return "(no links)\n"

    lines = []
    for index, item in enumerate(link_items, start=1):
        lines.append(f"[{index}]")
        lines.append("text: " + _safe_text(item.get("text", "")).strip())
        lines.append("href: " + _safe_text(item.get("href", "")).strip())
        container_text = _safe_text(item.get("container_text", "")).strip()
        if container_text:
            lines.append("container_text:")
            lines.append(container_text)
        lines.append("")

    return "\n".join(lines)


def _format_runtime_info(engine, env):
    return "\n".join(
        [
            "mode: generate-account-aliases",
            "browser_engine: " + engine,
            "command: " + " ".join(sys.argv),
            "headless: " + str(env.get("MF_IMPORT_CSV_BROWSER_HEADLESS", False)),
            "browser_channel: "
            + _safe_text(env.get("MF_IMPORT_CSV_BROWSER_CHANNEL", "")),
            "reuse_login_session: "
            + str(env.get("MF_IMPORT_CSV_REUSE_LOGIN_SESSION", False)),
            "",
        ]
    )


def safe_debug_value(label, getter):
    try:
        return getter()
    except Exception as exc:
        return f"<failed to get {label}: {exc.__class__.__name__}: {exc}>"


def create_debug_dir(name="generate-account-aliases"):
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    debug_dir = DEBUG_LOG_ROOT / f"{name}_{timestamp}"
    debug_dir.mkdir(parents=True, exist_ok=False)
    return debug_dir


def save_account_aliases_debug_info(
    *,
    engine,
    env,
    error,
    current_url,
    title,
    html,
    link_items,
    screenshot_func=None,
):
    debug_dir = create_debug_dir()

    _write_text(debug_dir / "current_url.txt", current_url)
    _write_text(debug_dir / "title.txt", title)
    _write_text(debug_dir / "page.html", html)
    _write_text(debug_dir / "links.txt", _format_links(link_items))
    _write_text(debug_dir / "runtime.txt", _format_runtime_info(engine, env))
    _write_text(
        debug_dir / "error.log",
        "error_type: "
        + error.__class__.__name__
        + "\n"
        + "error_message: "
        + str(error)
        + "\n",
    )

    if screenshot_func is not None:
        try:
            screenshot_func(str(debug_dir / "screenshot.png"))
        except Exception as exc:
            _write_text(
                debug_dir / "screenshot_error.txt",
                exc.__class__.__name__ + ": " + str(exc) + "\n",
            )

    return debug_dir
