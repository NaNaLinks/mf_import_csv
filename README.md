# マネーフォワード CSVインポート支援ツール

## 概要

このツールは、CSVファイルの取引データをマネーフォワードの手入力口座へ登録するためのPythonスクリプトです。

ブラウザ操作には **Selenium** または **Playwright** を使用できます。CSVの事前検証、dry-run、`.env` の対話作成、設定確認、手入力口座のエイリアス指定にも対応しています。

## 主な機能

- CSVファイルを読み込み、取引データをマネーフォワードへ登録
- 登録前のCSV検証
- `--dry-run` による登録予定内容の確認
- `--validate-only` によるCSV検証のみの実行
- Selenium / Playwright のブラウザエンジン切替
- `.env` によるログイン情報・ブラウザ設定の管理
- `--setup` による `.env` の対話作成
- `--show-config` による安全な設定確認
- 手入力口座URL、口座ID、口座エイリアスによるインポート先指定
- MoneyForwardの手入力口座一覧から `account_aliases.json` を生成
- Playwrightによるログイン済みブラウザ状態の再利用
- Windows / Mac / Ubuntu Server 向けのブラウザ設定

## 必要な環境

- Python 3.x
- Google Chrome または Playwright用Chromium
- Web版マネーフォワードからエクスポートしたCSVファイル

利用するブラウザエンジンに応じて、次のライブラリも使用します。

- Selenium 4.6 以降
- Playwright

## インストール

必要なPythonライブラリをインストールします。

```sh
pip install -r requirements.txt
```

Playwrightを使う場合は、ブラウザもインストールしてください。

```sh
python -m playwright install chromium
```

Ubuntu Serverなど、ブラウザ依存関係もまとめて入れたい場合は次のコマンドを使います。

```sh
python -m playwright install --with-deps chromium
```

## 最初の使い方

まずは設定ファイルを作成し、CSVを検証してから通常実行する流れをおすすめします。

### 1. `.env` を作成する

`.env.example` をコピーして `.env` を作成します。

```sh
cp .env.example .env
```

MacやLinuxでは、`.` で始まる `.env` や `.env.example` はGUI上で隠しファイルとして扱われることがあります。

ファイルを直接探して編集しづらい場合は、対話形式で `.env` を作成できます。

```sh
python mf_import_csv.py --setup
```

`--setup` はCSVファイルなしで実行できます。既に `.env` が存在する場合は、デフォルトでは上書きせずに終了します。

### 2. 設定状態を確認する

現在の設定状態は、次のコマンドで確認できます。

```sh
python mf_import_csv.py --show-config
```

`--show-config` もCSVファイルなしで実行できます。パスワードは表示されません。インポート先口座URLも実値ではなく、設定済みかどうかだけを表示します。

### 3. CSVを検証する

通常実行の前に、まずCSVの内容を確認します。

```sh
python mf_import_csv.py data.csv --validate-only
```

または、登録予定内容も確認する場合は `--dry-run` を使います。

```sh
python mf_import_csv.py data.csv --dry-run
```

どちらもMoneyForwardへのログイン、ブラウザ起動、登録処理は行いません。

### 4. 通常実行する

CSV検証で問題がなければ、通常実行します。

```sh
python mf_import_csv.py data.csv
```

通常実行では、CSV検証後にマネーフォワードへログインし、指定した手入力口座へ登録処理を行います。

## `.env` 設定

`.env` には、ログイン情報、インポート先、ブラウザ設定を記載します。

```env
MF_IMPORT_CSV_ACCOUNT_URL="<インポート先の口座URL>"
MF_IMPORT_CSV_USER="<自分のアカウント>"
MF_IMPORT_CSV_PASSWORD="<自分のパスワード>"
MF_IMPORT_CSV_BROWSER_ENGINE="selenium"
MF_IMPORT_CSV_BROWSER_HEADLESS="false"
MF_IMPORT_CSV_BROWSER_CHANNEL="chromium"
MF_IMPORT_CSV_REUSE_LOGIN_SESSION="true"
MF_IMPORT_CSV_BROWSER_PROFILE_DIR=".auth/moneyforward-playwright"
```

### 設定項目

| 項目 | 内容 |
| --- | --- |
| `MF_IMPORT_CSV_ACCOUNT_URL` | インポート先の手入力口座URL。`--account-id` または `--account` 指定時は省略できます。 |
| `MF_IMPORT_CSV_USER` | MoneyForwardログインユーザー |
| `MF_IMPORT_CSV_PASSWORD` | MoneyForwardログインパスワード |
| `MF_IMPORT_CSV_BROWSER_ENGINE` | `selenium` または `playwright`。未指定時は `selenium` を使います。 |
| `MF_IMPORT_CSV_BROWSER_HEADLESS` | 画面なしで実行する場合は `true`、画面を表示する場合は `false`。 |
| `MF_IMPORT_CSV_BROWSER_CHANNEL` | Playwrightで使うブラウザ。`chromium`、`chrome`、`msedge` など。 |
| `MF_IMPORT_CSV_REUSE_LOGIN_SESSION` | Playwrightでログイン済みブラウザ状態を再利用する場合は `true`。 |
| `MF_IMPORT_CSV_BROWSER_PROFILE_DIR` | Playwrightのログイン状態保存先。未指定時の想定は `.auth/moneyforward-playwright`。 |

## CSVファイル形式

Web版マネーフォワードのCSVエクスポート機能で取得できるCSVと同じ形式を想定しています。

```text
[0] "計算対象"
[1] "日付"
[2] "内容"
[3] "金額（円）"
[4] "保有金融機関"
[5] "大項目"
[6] "中項目"
[7] "メモ"
[8] "振替"
[9] "ID"
```

CSV検証では、以下を確認します。

- CSVファイルが存在すること
- CSVが読み込めること
- 各データ行に必要な列数があること
- 日付列が `YYYY/MM/DD` 形式として妥当であること
- 金額列が整数として扱えること
- 金額が `0` ではないこと

ヘッダー行、コメント行、計算対象が `0` の行はスキップします。検証エラーがある場合、通常実行でもマネーフォワードへ接続せずに終了します。

## 実行モード

### 通常インポート

```sh
python mf_import_csv.py data.csv
```

CSVを検証し、問題がなければMoneyForwardへ登録します。

### dry-run

```sh
python mf_import_csv.py data.csv --dry-run
```

CSVを検証し、登録予定の内容と件数を表示します。MoneyForwardへの登録は行いません。

### validate-only

```sh
python mf_import_csv.py data.csv --validate-only
```

CSV検証のみを行います。MoneyForwardへのログイン、ブラウザ起動、登録処理は行いません。

### setup

```sh
python mf_import_csv.py --setup
```

`.env` を対話形式で作成します。CSVファイルは不要です。

`--setup` はCSVインポート用のオプションとは同時に指定できません。

### show-config

```sh
python mf_import_csv.py --show-config
```

`.env` の設定状態を安全に表示します。CSVファイルは不要です。

`--show-config` はCSVインポート用のオプションとは同時に指定できません。

### generate-account-aliases

```sh
python mf_import_csv.py --generate-account-aliases
```

MoneyForwardの手入力口座一覧から、`account_aliases.json` を生成します。CSVファイルは不要です。

このモードではMoneyForwardへログインし、`https://moneyforward.com/accounts` のリンクから `/accounts/show_manual/<口座ID>` を含む手入力口座だけを抽出します。自動連携口座は対象にしません。

既存の `account_aliases.json` がある場合、デフォルトでは上書きせずに終了します。

別ファイルへ出力する場合は `--output` を指定します。

```sh
python mf_import_csv.py --generate-account-aliases --output account_aliases.new.json
```

既存ファイルを上書きする場合だけ、明示的に `--force` を指定してください。

```sh
python mf_import_csv.py --generate-account-aliases --force
```

`--generate-account-aliases` はCSVインポート用のオプションとは同時に指定できません。`--output` と `--force` は `--generate-account-aliases` 専用です。

## インポート先口座の指定方法

インポート先の指定方法は3つあります。

優先順位は次の通りです。

1. `--account`
2. `--account-id`
3. `.env` の `MF_IMPORT_CSV_ACCOUNT_URL`

ただし、`--account` と `--account-id` は同時に指定できません。

### `.env` のURLで指定する

`.env` に直接、手入力口座URLを設定します。

```env
MF_IMPORT_CSV_ACCOUNT_URL="https://moneyforward.com/accounts/show_manual/<口座ID>"
```

通常実行時は、このURLを使ってインポート先を開きます。

### 口座IDで指定する

手入力口座IDをCLIで指定できます。

```sh
python mf_import_csv.py data.csv --account-id 123456
```

`--account-id` は、次の形式のURLに変換されます。

```text
https://moneyforward.com/accounts/show_manual/123456
```

この指定は `.env` の `MF_IMPORT_CSV_ACCOUNT_URL` より優先されます。

### 口座エイリアスで指定する

口座IDを直接入力したくない場合は、`account_aliases.json` にエイリアスを定義できます。

まずサンプルファイルをコピーします。

```sh
cp account_aliases.example.json account_aliases.json
```

`account_aliases.json` には、口座エイリアスと手入力口座IDの対応をJSONで定義します。

以下はダミー値の例です。実口座IDをREADME、レポート、PR本文、Git管理対象ファイルへ書かないでください。

```json
{
  "cash": "123456",
  "paypay": "234567",
  "private-cash": "345678"
}
```

作成後、次のように実行できます。

```sh
python mf_import_csv.py data.csv --account cash
```

`--account` は `account_aliases.json` から口座IDを取得し、`https://moneyforward.com/accounts/show_manual/<口座ID>` の形式に変換します。

## ブラウザエンジン設定

### Seleniumを使う

Seleniumは既定のブラウザエンジンです。未指定の場合もSeleniumを使います。

```env
MF_IMPORT_CSV_BROWSER_ENGINE="selenium"
MF_IMPORT_CSV_BROWSER_HEADLESS="false"
MF_IMPORT_CSV_BROWSER_CHANNEL="chromium"
```

現時点では、Selenium実装における `MF_IMPORT_CSV_BROWSER_CHANNEL` は主に将来拡張・説明用です。SeleniumではローカルにインストールされたGoogle Chromeを使う運用が基本です。

### Playwrightを使う

Playwrightを使う場合は、依存関係のインストール後にPlaywright用ブラウザをインストールしてください。

```sh
python -m playwright install chromium
```

```env
MF_IMPORT_CSV_BROWSER_ENGINE="playwright"
MF_IMPORT_CSV_BROWSER_HEADLESS="false"
MF_IMPORT_CSV_BROWSER_CHANNEL="chromium"
MF_IMPORT_CSV_REUSE_LOGIN_SESSION="true"
MF_IMPORT_CSV_BROWSER_PROFILE_DIR=".auth/moneyforward-playwright"
```

`MF_IMPORT_CSV_BROWSER_CHANNEL` は、Playwrightでは特に意味があります。`chromium` はPlaywright同梱Chromiumを使う想定です。

ローカルにGoogle Chromeがインストール済みの場合は `chrome`、Microsoft Edgeがインストール済みの場合は `msedge` を指定できます。

`MF_IMPORT_CSV_REUSE_LOGIN_SESSION="true"` を指定すると、Playwrightは `MF_IMPORT_CSV_BROWSER_PROFILE_DIR` の専用ブラウザプロファイルを使います。

初回実行時にログインや追加認証を済ませると、2回目以降はサービス側が承認済みと判断する限り、そのログイン状態を再利用します。サービス側が再確認を要求した場合は、従来どおり画面に従って認証コードを入力してください。

保存先の `.auth/` にはログイン済みブラウザ状態が含まれます。中身を共有したり、Gitへ追加したりしないでください。

## 環境別のおすすめ設定

### Windows / Mac

通常のブラウザ画面を見ながら操作する場合は、headlessを無効にします。

```env
MF_IMPORT_CSV_BROWSER_HEADLESS="false"
```

SeleniumではローカルにインストールされたGoogle Chromeを使う運用が基本です。

Playwrightでは、`python -m playwright install chromium` で同梱Chromiumを入れ、`MF_IMPORT_CSV_BROWSER_CHANNEL="chromium"` を使う構成を基本例にします。

ローカルのChromeを使いたい場合は、`MF_IMPORT_CSV_BROWSER_CHANNEL="chrome"` を指定します。

### Ubuntu Server

画面のないサーバーではheadless実行を使います。

```env
MF_IMPORT_CSV_BROWSER_ENGINE="playwright"
MF_IMPORT_CSV_BROWSER_HEADLESS="true"
MF_IMPORT_CSV_BROWSER_CHANNEL="chromium"
```

Ubuntu Serverでは、Playwright + 同梱Chromium + headlessを推奨例とします。サーバー上でブラウザと依存関係をインストールします。

```sh
python -m playwright install --with-deps chromium
```

Seleniumを使う場合は、サーバーにGoogle ChromeまたはChromiumと、Selenium Managerが利用できる実行環境を用意してください。

サーバー運用では、通常実行前に必ず `--validate-only` または `--dry-run` でCSV内容を確認してください。

## ファイル構成

| ファイル | 内容 |
| --- | --- |
| `mf_import_csv.py` | CLI入口と実行制御 |
| `csv_validation.py` | CSV検証とdry-run表示 |
| `config.py` | `.env` 読み込みと必須環境変数チェック |
| `config_setup.py` | `.env` の対話作成と設定確認 |
| `browser_engine.py` | ブラウザエンジン選択 |
| `moneyforward_importer.py` | Seleniumを使ったマネーフォワード画面操作 |
| `moneyforward_importer_playwright.py` | Playwrightを使ったマネーフォワード画面操作 |
| `account_aliases_generator.py` | 手入力口座リンクの抽出とエイリアス設定生成 |
| `account_aliases.example.json` | 口座エイリアス設定のサンプル |
| `.env.example` | 環境変数設定のサンプル |

## 管理してはいけないファイル・情報

以下はGit管理対象にしないでください。

- `.env`
- `account_aliases.json`
- `.auth/`
- 実口座IDを含むファイル
- ログイン情報を含むファイル

認証情報、口座URL、実口座IDの実値は、コード、README、レポート、PR本文、Git管理対象ファイルに含めないでください。

## 注意点

- マネーフォワードのUI変更により、要素のIDやクラスが変わる可能性があります。
- 自動化ツールの利用は、マネーフォワードの利用規約に違反しないように注意してください。
- 本スクリプトの使用は自己責任でお願いします。本スクリプトを使用したことによるいかなる損害についても、作者は責任を負いません。
- 本スクリプトは個人による開発であり、マネーフォワードとは一切関係ありません。

## ライセンス

このプロジェクトはMITライセンスのもとで公開されています。

## 作者

このスクリプトはnanosnsによって開発・管理されています。
