import time
from pathlib import Path

from account_aliases_generator import extract_manual_account_aliases


ACCOUNTS_URL = "https://moneyforward.com/accounts"


def import_playwright():
    from playwright.sync_api import TimeoutError, sync_playwright

    return sync_playwright, TimeoutError


def _build_launch_options(env):
    channel = env.get("MF_IMPORT_CSV_BROWSER_CHANNEL", "")
    headless = env.get("MF_IMPORT_CSV_BROWSER_HEADLESS", False)
    launch_options = {"headless": headless}

    if channel and channel != "chromium":
        launch_options["channel"] = channel

    return launch_options


def _launch_page(playwright, env):
    launch_options = _build_launch_options(env)

    if env.get("MF_IMPORT_CSV_REUSE_LOGIN_SESSION", False):
        profile_dir = Path(
            env.get(
                "MF_IMPORT_CSV_BROWSER_PROFILE_DIR",
                ".auth/moneyforward-playwright",
            )
        ).expanduser()
        profile_dir.mkdir(parents=True, exist_ok=True)
        context = playwright.chromium.launch_persistent_context(
            str(profile_dir),
            **launch_options,
        )
        page = context.pages[0] if context.pages else context.new_page()
        return page, context.close

    browser = playwright.chromium.launch(**launch_options)
    page = browser.new_page()
    return page, browser.close


def _wait_visible(locator, timeout, PlaywrightTimeoutError):
    try:
        locator.wait_for(state="visible", timeout=timeout)
        return True
    except PlaywrightTimeoutError:
        return False


def _is_import_page_ready(page, PlaywrightTimeoutError, timeout=3000):
    return _wait_visible(page.locator(".cf-new-btn"), timeout, PlaywrightTimeoutError)


def _is_accounts_page_ready(page, PlaywrightTimeoutError, timeout=3000):
    if _wait_visible(
        page.locator('a[href*="/accounts/show_manual/"]').first,
        timeout,
        PlaywrightTimeoutError,
    ):
        return True

    return "/accounts" in page.url and not _is_login_form_visible(
        page,
        PlaywrightTimeoutError,
        timeout=500,
    )


def _is_login_form_visible(page, PlaywrightTimeoutError, timeout=3000):
    return _wait_visible(
        page.locator('[id="mfid_user[email]"]'),
        timeout,
        PlaywrightTimeoutError,
    )


def _is_auth_challenge_visible(page, PlaywrightTimeoutError, timeout=1000):
    return _wait_visible(
        page.locator('[name="otp_attempt"]'),
        timeout,
        PlaywrightTimeoutError,
    ) or _wait_visible(
        page.locator('[name="email_otp"]'),
        timeout,
        PlaywrightTimeoutError,
    )


def _submit_login(page, user, password):
    # アカウント入力
    elem = page.locator('[id="mfid_user[email]"]')
    elem.fill("")
    elem.press_sequentially(user)
    elem.press("Enter")

    # パスワード入力
    elem = page.locator('[id="mfid_user[password]"]')
    elem.fill("")
    elem.press_sequentially(password)
    elem.press("Enter")


def _handle_auth_challenges(page, PlaywrightTimeoutError):
    # ここでOTP入力画面が出る場合があるので対応
    optauth = False
    otp_elem = page.locator('[name="otp_attempt"]')
    if _wait_visible(otp_elem, 2000, PlaywrightTimeoutError):
        otp_code = input("２段階認証コードを入力してください: ")
        otp_elem.fill("")
        otp_elem.press_sequentially(otp_code)
        otp_elem.press("Enter")
        print("２段階認証コードを送信しました。")
        optauth = True
    else:
        # OTPフォームが出てこなければそのまま先へ
        print("２段階認証コード入力画面が表示されませんでした。")

    # 2段階認証無効時は追加認証画面が出てくる場合がある
    if optauth is False:
        otp_elem = page.locator('[name="email_otp"]')
        if _wait_visible(otp_elem, 2000, PlaywrightTimeoutError):
            otp_code = input("追加認証コードを入力してください: ")
            otp_elem.fill("")
            otp_elem.press_sequentially(otp_code)
            otp_elem.press("Enter")
            print("追加認証コードを送信しました。")
        else:
            # OTPフォームが出てこなければそのまま先へ
            print("追加認証コード入力画面は表示されませんでした。")


def _ensure_logged_in(
    page,
    user,
    password,
    PlaywrightTimeoutError,
    is_ready,
    ready_message,
    failure_message,
):
    if is_ready(page, PlaywrightTimeoutError):
        print(ready_message)
        return

    if _is_login_form_visible(page, PlaywrightTimeoutError):
        _submit_login(page, user, password)
        _handle_auth_challenges(page, PlaywrightTimeoutError)
    elif _is_auth_challenge_visible(page, PlaywrightTimeoutError):
        _handle_auth_challenges(page, PlaywrightTimeoutError)
    else:
        raise RuntimeError(
            "ログイン状態を判定できませんでした。ログインフォーム、追加認証フォーム、"
            "目的ページのいずれも確認できません。"
        )

    if not is_ready(page, PlaywrightTimeoutError, timeout=15000):
        raise RuntimeError(failure_message)


def _ensure_logged_in_for_import(page, user, password, PlaywrightTimeoutError):
    _ensure_logged_in(
        page,
        user,
        password,
        PlaywrightTimeoutError,
        _is_import_page_ready,
        "ログイン済みセッションを利用して登録ページへ進みます。",
        "ログイン後に登録ページを確認できませんでした。認証状態または画面表示を確認してください。",
    )


def _ensure_logged_in_for_accounts(page, user, password, PlaywrightTimeoutError):
    _ensure_logged_in(
        page,
        user,
        password,
        PlaywrightTimeoutError,
        _is_accounts_page_ready,
        "ログイン済みセッションを利用して口座一覧ページへ進みます。",
        "ログイン後に口座一覧ページを確認できませんでした。認証状態または画面表示を確認してください。",
    )


def _click_exact_text_in_locator(locator, text):
    target = text.strip()
    count = locator.count()

    for index in range(count):
        item = locator.nth(index)
        if (item.text_content() or "").strip() == target:
            item.click()
            return

    raise RuntimeError(f"クリック対象が見つかりません: {target}")


def _click_large_category(page, text):
    _click_exact_text_in_locator(page.locator("a.l_c_name"), text)


def _click_middle_category(page, text):
    _click_exact_text_in_locator(page.locator("a.m_c_name"), text)


def _collect_manual_account_links(page):
    link_items = []
    links = page.locator('a[href*="/accounts/show_manual/"]')

    for index in range(links.count()):
        link = links.nth(index)
        container = link.locator(
            "xpath=ancestor::*[self::li or self::tr or self::div][1]"
        )
        container_text = ""
        if container.count() > 0:
            container_text = container.first.text_content() or ""

        link_items.append(
            {
                "href": link.get_attribute("href") or "",
                "text": link.text_content() or "",
                "container_text": container_text,
            }
        )

    return link_items


def generate_account_aliases(env):
    sync_playwright, PlaywrightTimeoutError = import_playwright()

    user = env["MF_IMPORT_CSV_USER"]
    password = env["MF_IMPORT_CSV_PASSWORD"]

    with sync_playwright() as playwright:
        page, close_browser = _launch_page(playwright, env)

        try:
            page.goto(ACCOUNTS_URL)
            _ensure_logged_in_for_accounts(page, user, password, PlaywrightTimeoutError)
            try:
                page.wait_for_load_state("networkidle", timeout=10000)
            except PlaywrightTimeoutError:
                pass
            return extract_manual_account_aliases(_collect_manual_account_links(page))
        finally:
            close_browser()


def run_import(input_file, entries, env):
    sync_playwright, PlaywrightTimeoutError = import_playwright()

    url = env["MF_IMPORT_CSV_ACCOUNT_URL"]
    user = env["MF_IMPORT_CSV_USER"]
    password = env["MF_IMPORT_CSV_PASSWORD"]

    print("Start :" + input_file)
    with sync_playwright() as playwright:
        page, close_browser = _launch_page(playwright, env)

        try:
            page.goto(url)
            _ensure_logged_in_for_import(page, user, password, PlaywrightTimeoutError)

            for entry in entries:
                row = entry.row
                n = entry.line_number
                print("Start line[" + str(n) + "]")

                # 「手入力」ボタンクリック
                page.locator(".cf-new-btn").click()

                # 金額入力
                if entry.amount > 0:
                    # "金額（円）" > 0 ならば収入
                    print("[" + str(n) + "] " + "Plus! :")
                    print(row)
                    amount = entry.amount

                    # click Plus
                    page.locator(".plus-payment").click()
                else:
                    # "金額（円）" < 0 ならば支出
                    print("[" + str(n) + "] " + "Minus! :")
                    print(row)
                    amount = entry.amount * -1

                # 日付（YYYY/MM/DD）
                elem = page.locator("#updated-at")
                elem.fill("")
                time.sleep(0.5)
                elem.press_sequentially(row[1])
                elem.click()
                elem.click()
                time.sleep(0.5)

                # 金額
                elem = page.locator("#appendedPrependedInput")
                elem.fill("")
                elem.press_sequentially(str(amount))

                # 大項目
                if row[5] != "未分類":
                    page.locator("#js-large-category-selected").click()
                    _click_large_category(page, row[5])

                # 中項目
                if row[6] != "未分類":
                    sub_category = row[6]
                    if sub_category[0] == "'":
                        sub_category = sub_category[1:]

                    print("sub_category:" + sub_category)
                    page.locator("#js-middle-category-selected").click()
                    _click_middle_category(page, sub_category)

                # 内容
                if row[7] == "":
                    content = row[2]
                else:
                    content = row[2] + "（" + row[7] + "）"

                content = content[0:50]
                elem = page.locator("#js-content-field")
                elem.fill("")
                elem.press_sequentially(content)

                # 「保存」ボタンクリック
                time.sleep(1)
                elem = page.locator("#submit-button")

                # （以下、テストコード）Closeボタン「×」をクリックして保存しない
                # time.sleep(3)
                # elem = page.locator(".close")

                elem.click()
                time.sleep(5)
        finally:
            print("End :" + input_file)
            close_browser()
