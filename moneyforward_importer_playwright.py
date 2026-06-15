import time


def import_playwright():
    from playwright.sync_api import TimeoutError, sync_playwright

    return sync_playwright, TimeoutError


def _launch_browser(playwright, env):
    channel = env.get("MF_IMPORT_CSV_BROWSER_CHANNEL", "")
    headless = env.get("MF_IMPORT_CSV_BROWSER_HEADLESS", False)
    launch_options = {"headless": headless}

    if channel and channel != "chromium":
        launch_options["channel"] = channel

    return playwright.chromium.launch(**launch_options)


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


def run_import(input_file, entries, env):
    sync_playwright, PlaywrightTimeoutError = import_playwright()

    url = env["MF_IMPORT_CSV_ACCOUNT_URL"]
    user = env["MF_IMPORT_CSV_USER"]
    password = env["MF_IMPORT_CSV_PASSWORD"]

    print("Start :" + input_file)
    with sync_playwright() as playwright:
        browser = _launch_browser(playwright, env)
        page = browser.new_page()

        try:
            page.goto(url)

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

            # ここでOTP入力画面が出る場合があるので対応
            optauth = False
            try:
                otp_elem = page.locator('[name="otp_attempt"]')
                otp_elem.wait_for(state="visible", timeout=2000)
                otp_code = input("２段階認証コードを入力してください: ")
                otp_elem.fill("")
                otp_elem.press_sequentially(otp_code)
                otp_elem.press("Enter")
                print("２段階認証コードを送信しました。")
                optauth = True
            except PlaywrightTimeoutError:
                # OTPフォームが出てこなければそのまま先へ
                print("２段階認証コード入力画面が表示されませんでした。")

            # 2段階認証無効時は追加認証画面が出てくる場合がある
            if optauth is False:
                try:
                    otp_elem = page.locator('[name="email_otp"]')
                    otp_elem.wait_for(state="visible", timeout=2000)
                    otp_code = input("追加認証コードを入力してください: ")
                    otp_elem.fill("")
                    otp_elem.press_sequentially(otp_code)
                    otp_elem.press("Enter")
                    print("追加認証コードを送信しました。")
                except PlaywrightTimeoutError:
                    # OTPフォームが出てこなければそのまま先へ
                    print("追加認証コード入力画面は表示されませんでした。")

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
            browser.close()
