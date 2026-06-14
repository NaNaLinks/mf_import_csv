import time


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
        if env.get("MF_IMPORT_CSV_BROWSER_HEADLESS", False):
            options.add_argument("--headless=new")
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
