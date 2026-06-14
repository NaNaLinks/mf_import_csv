# マネーフォワードにCSVデータを自動で取り込むスクリプト

## 概要

このスクリプトは、**Selenium** または **Playwright** を使用してCSVデータをマネーフォワードに自動で取り込むPythonスクリプトです。

## 機能

- Chromeブラウザを起動
- マネーフォワードにログインして登録する口座のページを開く
- CSVファイルを読み込み、各取引データを入力
- 入力内容を保存（テストモードでは保存せずに閉じる）
- CSV検証
- dry-runによる登録予定内容の確認
- validate-onlyによるCSV検証のみの実行
- Selenium / Playwright のブラウザエンジン切替

## 必要な環境

- **Python** 3.x
- **Selenium** 4.6 以降（Selenium Managerを使用）
- **Playwright**（Playwright engineを使う場合）
- **Google Chrome** 最新版
- **適切なCSVファイル**（Web版マネーフォワードのCSVエクスポート機能で取得してください）

## インストール

以下のコマンドを実行して必要なライブラリをインストールしてください。

```sh
pip install -r requirements.txt
```

Playwright engineを使う場合は、Playwright用ブラウザもインストールしてください。

```sh
python -m playwright install chromium
```

## ファイル構成

- `mf_import_csv.py`: CLI入口と実行制御
- `csv_validation.py`: CSV検証とdry-run表示
- `config.py`: `.env` 読み込みと必須環境変数チェック
- `browser_engine.py`: ブラウザエンジン選択
- `moneyforward_importer.py`: Seleniumを使ったマネーフォワード画面操作
- `moneyforward_importer_playwright.py`: Playwrightを使ったマネーフォワード画面操作

## 実行方法

1. `.env.example` をコピーして `.env` を作成してください。
   ```sh
   cp .env.example .env
   ```
2. `.env` に、マネーフォワードのユーザー名、パスワード、インポート先の口座URLを指定してください。
   - `MF_IMPORT_CSV_ACCOUNT_URL`: インポート先の口座URL
   - `MF_IMPORT_CSV_USER`: MoneyForwardログインユーザー
   - `MF_IMPORT_CSV_PASSWORD`: MoneyForwardログインパスワード
   - `MF_IMPORT_CSV_BROWSER_ENGINE`: `selenium` または `playwright`（未指定時は `selenium`）
   - `MF_IMPORT_CSV_BROWSER_HEADLESS`: `true` または `false`（未指定時は `false`）
   - `MF_IMPORT_CSV_BROWSER_CHANNEL`: `chrome`、`chromium`、`msedge` など
   - 例:
   ```env
   MF_IMPORT_CSV_ACCOUNT_URL="<インポート先の口座URL>"
   MF_IMPORT_CSV_USER="<自分のアカウント>"
   MF_IMPORT_CSV_PASSWORD="<自分のパスワード>"
   MF_IMPORT_CSV_BROWSER_ENGINE="selenium"
   MF_IMPORT_CSV_BROWSER_HEADLESS="false"
   MF_IMPORT_CSV_BROWSER_CHANNEL="chrome"
   ```
   - `.env` はGit管理対象にしないでください。
   - 認証情報やURLの実値は、コード、README、レポート、Git管理対象ファイルに含めないでください。
3. CSVファイルをスクリプトと同じフォルダに配置する。
    - Web版マネーフォワードのCSVエクスポート機能で取得できるCSVと同じフォーマットです。

```
[0] "計算対象", 
[1] "日付", 
[2] "内容", 
[3] "金額（円）", 
[4] "保有金融機関", 
[5] "大項目", 
[6] "中項目", 
[7] "メモ", 
[8] "振替", 
[9] "ID"
```

4. スクリプトを実行

```sh
python mf_import_csv.py data.csv
```

- `data.csv` はインポートするCSVファイルのパスです。
- 通常実行ではCSV検証後にマネーフォワードへログインし、登録処理を行います。

## ブラウザエンジン設定

### Seleniumを使う

Seleniumは既定のブラウザエンジンです。未指定の場合もSeleniumを使います。

```env
MF_IMPORT_CSV_BROWSER_ENGINE="selenium"
MF_IMPORT_CSV_BROWSER_HEADLESS="false"
MF_IMPORT_CSV_BROWSER_CHANNEL="chrome"
```

### Playwrightを使う

Playwrightを使う場合は、依存関係のインストール後にPlaywright用ブラウザをインストールしてください。

```sh
python -m playwright install chromium
```

```env
MF_IMPORT_CSV_BROWSER_ENGINE="playwright"
MF_IMPORT_CSV_BROWSER_HEADLESS="false"
MF_IMPORT_CSV_BROWSER_CHANNEL="chrome"
```

`MF_IMPORT_CSV_BROWSER_CHANNEL` は、Playwrightでは `chrome`、`chromium`、`msedge` などを指定できます。`chromium` を指定した場合はPlaywright同梱のChromiumを使います。

## 実行環境別メモ

### Windows / Mac

通常のブラウザ画面を見ながら操作する場合は、以下のようにheadlessを無効にします。

```env
MF_IMPORT_CSV_BROWSER_HEADLESS="false"
```

SeleniumではローカルにインストールされたGoogle Chromeを使う運用が基本です。Playwrightでは `python -m playwright install chromium` で同梱Chromiumを入れるか、`MF_IMPORT_CSV_BROWSER_CHANNEL="chrome"` で通常のChromeを使います。

### Ubuntu Server

画面のないサーバーではheadless実行を使います。

```env
MF_IMPORT_CSV_BROWSER_HEADLESS="true"
```

Playwrightを使う場合は、サーバー上でブラウザと依存関係をインストールします。

```sh
python -m playwright install --with-deps chromium
```

Seleniumを使う場合は、サーバーにGoogle ChromeまたはChromiumと、Selenium Managerが利用できる実行環境を用意してください。サーバー運用では、通常実行前に必ず `--validate-only` または `--dry-run` でCSV内容を確認してください。

## 事前確認

通常実行前に、`--dry-run` または `--validate-only` でCSVを確認することを推奨します。

### dry-run

```sh
python mf_import_csv.py data.csv --dry-run
```

`--dry-run` はCSV検証を行い、登録予定の内容と件数を表示します。マネーフォワードへのログイン、ブラウザ起動、登録処理は行いません。

### validate-only

```sh
python mf_import_csv.py data.csv --validate-only
```

`--validate-only` はCSV検証のみを行います。マネーフォワードへのログイン、ブラウザ起動、登録処理は行いません。

### CSV検証内容

以下を確認します。

- CSVファイルが存在すること
- CSVが読み込めること
- 各データ行に必要な列数があること
- 日付列が `YYYY/MM/DD` 形式として妥当であること
- 金額列が整数として扱えること
- 金額が `0` ではないこと

ヘッダー行、コメント行、計算対象が `0` の行はスキップします。検証エラーがある場合、通常実行でもマネーフォワードへ接続せずに終了します。

## 注意点

- `time.sleep` を適宜調整することで、環境に合わせて動作を安定させられます。
- マネーフォワードのUI変更により、要素のIDやクラスが変わる可能性があります。
- 本スクリプトの使用は自己責任でお願いします。本スクリプトを使用したことによるいかなる損害についても、作者は責任を負いません。
- 本スクリプトは個人による開発であり、マネーフォワードとは一切関係ありません。
- 自動化ツールの利用は、マネーフォワードの利用規約に違反しないように注意してください。

## ライセンス

このプロジェクトはMITライセンスのもとで公開されています。

## 作者

このスクリプトはnanosnsによって開発・管理されています。
