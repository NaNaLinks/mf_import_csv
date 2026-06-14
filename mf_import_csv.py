import sys
import os
import csv
import time
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

url = required_env_vars["MF_IMPORT_CSV_ACCOUNT_URL"]
user = required_env_vars["MF_IMPORT_CSV_USER"]
password = required_env_vars["MF_IMPORT_CSV_PASSWORD"]

from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException


if len(sys.argv) != 2:
    print("No input_file!")
    print("usage: python mf_import_csv.py data_file.csv")
    sys.exit()
input_file = str(sys.argv[1])

try:
    print("Start :" + input_file)

    # Chromeブラウザを立ち上げる
    options = webdriver.ChromeOptions()
    # Windowsでは NUL, mac/linuxでは /dev/null にログを捨てる
    options.add_argument("--log-level=3")  
    options.add_experimental_option('excludeSwitches', ['enable-logging'])
    driver = webdriver.Chrome(options=options)
    driver.implicitly_wait(10)   #wait
    # マネーフォワードの銀行ページに遷移
    driver.get(url)

    # アカウント入力
    elem = driver.find_element(By.ID, "mfid_user[email]")
    # driver.save_screenshot("test.png")
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
    if optauth == False:
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

    # open data file
    # ◆CSVファイルフォーマット
    # [0]"計算対象",
    # [1]"日付",
    # [2]"内容",
    # [3]"金額（円）",
    # [4]"保有金融機関",
    # [5]"大項目",
    # [6]"中項目",
    # [7]"メモ",
    # [8]"振替",
    # [9]"ID"

    f = open(input_file, mode='r', encoding='utf_8')

    reader = csv.reader(f)
    n = 0
    for row in reader:
        n+=1
        print("Stert line[" + str(n) + "]")

        #日付が「#」の場合、コメント行として次へ飛ばす
        print("[0]" + row[0])
        if row[0] == '#' or row[0] == '0' or row[0] == '計算対象':
            print("[" + str(n) + "] Skip comment line!")
            continue

        #「手入力」ボタンクリック
        elem = driver.find_element(By.CLASS_NAME,"cf-new-btn")
        elem.click()
        
        # 金額入力
        plus_minus_flg = None
        if int(row[3]) > 0:
            # "金額（円）" > 0 ならば収入
            print("[" + str(n) + "] " + "Plus! :")
            print(row)
            amount = int(row[3])
            plus_minus_flg = 'p'

            #click Plus
            elem = driver.find_element(By.CLASS_NAME,"plus-payment")
            elem.click()

        elif int(row[3]) < 0:
            # "金額（円）" < 0 ならば支出
            print("[" + str(n) + "] " + "Minus! :")
            print(row)
            amount = int(row[3]) * -1
            plus_minus_flg = 'm'

        else:
            print ("Error row num = " + str(n) + "\n")

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
            content = row[2] + "（" + row[7] +"）"

        content
        content = content[0:50]
        elem = driver.find_element(By.ID, "js-content-field")
        elem.clear()
        elem.send_keys(content)

        #「保存」ボタンクリック
        time.sleep(1)
        elem = driver.find_element(By.ID, "submit-button")

        # （以下、テストコード）Closeボタン「×」をクリックして保存しない
        # time.sleep(3)
        # elem = driver.find_element(By.CLASS_NAME,"close")

        elem.click()        
        time.sleep(5)
    f.close()

finally:
    print("End :" + input_file)
    driver.quit()
