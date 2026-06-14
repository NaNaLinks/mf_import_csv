import sys


DEFAULT_BROWSER_ENGINE = "selenium"
SUPPORTED_BROWSER_ENGINES = {"playwright", "selenium"}


def get_browser_engine(env):
    engine = env.get("MF_IMPORT_CSV_BROWSER_ENGINE", DEFAULT_BROWSER_ENGINE)
    normalized = engine.strip().lower()

    if normalized not in SUPPORTED_BROWSER_ENGINES:
        print(
            "Unsupported browser engine: "
            + engine
            + " (supported: "
            + ", ".join(sorted(SUPPORTED_BROWSER_ENGINES))
            + ")",
            file=sys.stderr,
        )
        sys.exit(1)

    return normalized


def run_import(input_file, entries, env):
    engine = get_browser_engine(env)

    if engine == "selenium":
        from moneyforward_importer import run_import as run_selenium_import

        run_selenium_import(input_file, entries, env)
        return

    if engine == "playwright":
        from moneyforward_importer_playwright import run_import as run_playwright_import

        run_playwright_import(input_file, entries, env)
        return

    raise AssertionError("unreachable browser engine: " + engine)
