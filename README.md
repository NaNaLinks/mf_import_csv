# MF CSVインポート

Money Forwardの手入力口座へ、CSVの取引データをブラウザ操作で登録するための支援ツールです。

## 1. 概要

このアプリは、CSVファイルを検証し、SeleniumまたはPlaywrightでMoney Forwardの手入力口座ページを開いて、取引を1件ずつ登録します。

推奨する流れは次の通りです。

1. `--setup` でログイン情報とブラウザ設定を登録する。
2. 必要に応じて `--generate-account-aliases` で手入力口座の一覧から `account_aliases.json` を作る。
3. `--show-config` で設定状態を確認する。
4. `--validate-only` または `--dry-run` でCSVを確認する。
5. 問題がなければCSVを指定してインポートする。

実登録を行う通常実行ではMoney Forwardへログインし、登録ボタンを押します。事前確認には、Money Forwardへ接続しない `--validate-only` または `--dry-run` を使ってください。

## 2. セットアップ手順

### 2.1 リポジトリを取得する

```sh
git clone https://github.com/NaNaLinks/mf_import_csv.git
cd mf_import_csv
```

### 2.2 Python環境を用意する

Python 3系を使います。仮想環境を使う場合の例です。

```sh
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```

依存パッケージは次の通りです。

- `selenium`
- `python-dotenv`
- `playwright`

### 2.3 ブラウザ操作に必要な準備

Seleniumは既定のブラウザエンジンです。ローカルにインストールされたGoogle Chromeを使う運用が基本です。

Playwrightを使う場合は、Playwright用ブラウザをインストールします。

```sh
python -m playwright install chromium
```

画面のないUbuntu Serverなどでは、必要なOS依存パッケージも含めてインストールします。

```sh
python -m playwright install --with-deps chromium
```

### 2.4 設定ファイルを準備する

Macでは `.env` のような隠しファイルをGUIで見つけにくいため、通常は対話式セットアップを使ってください。

```sh
python mf_import_csv.py --setup
```

`--setup` はCSVファイルなしで実行できます。既に `.env` がある場合は上書きせずに終了します。パスワード入力は画面表示されません。

手動で作成する場合は、`.env.example` をコピーして `.env` を編集します。

```sh
cp .env.example .env
```

設定できる項目は次の通りです。

| 設定キー | 用途 | 補足 |
| --- | --- | --- |
| `MF_IMPORT_CSV_ACCOUNT_URL` | 既定のインポート先口座URL | `--account-id` または `--account` 指定時は省略できます。 |
| `MF_IMPORT_CSV_USER` | Money Forwardログインユーザー | 必須です。 |
| `MF_IMPORT_CSV_PASSWORD` | Money Forwardログインパスワード | 必須です。 |
| `MF_IMPORT_CSV_BROWSER_ENGINE` | ブラウザエンジン | `selenium` または `playwright`。未指定時は `selenium`。 |
| `MF_IMPORT_CSV_BROWSER_HEADLESS` | headless実行 | `true` / `false`。未指定時は `false`。 |
| `MF_IMPORT_CSV_BROWSER_CHANNEL` | Playwrightのブラウザチャンネル | `chromium`、`chrome`、`msedge` など。 |
| `MF_IMPORT_CSV_REUSE_LOGIN_SESSION` | Playwrightのログイン状態再利用 | 未指定時は `false`。 |
| `MF_IMPORT_CSV_BROWSER_PROFILE_DIR` | Playwrightのプロファイル保存先 | 未指定時は `.auth/moneyforward-playwright`。 |

設定状態は次のコマンドで確認できます。

```sh
python mf_import_csv.py --show-config
```

`--show-config` はパスワードを表示せず、インポート先口座URLも実値ではなく設定済みかどうかだけを表示します。

### 2.5 Git管理しないファイル

次のファイルやディレクトリには認証情報、実口座ID、ログイン済みブラウザ状態が含まれる可能性があります。Gitへ追加しないでください。

- `.env`
- `.auth/`
- `account_aliases.json`
- `logs/debug/`

### 2.6 初回実行前の確認

初回実行前に次を確認してください。

- `.env` が作成済みで、`--show-config` で必要項目が設定済みになっている。
- インポート先が `.env` の `MF_IMPORT_CSV_ACCOUNT_URL`、`--account-id`、`--account` のどれで決まるか把握している。
- CSVが後述のフォーマットに合っている。
- 実登録前に `--validate-only` または `--dry-run` が成功している。
- Playwrightでログイン状態を再利用する場合、`.auth/` を共有したりGitへ追加したりしない。

## 3. 使い方（推奨）

### 3.1 ユーザーアカウントの登録手順

対話式セットアップを実行します。

```sh
python mf_import_csv.py --setup
```

入力する主な内容は、Money Forwardログインユーザー、パスワード、既定のインポート先口座URL、ブラウザエンジン、headless設定です。

登録後は設定状態を確認します。

```sh
python mf_import_csv.py --show-config
```

`MF_IMPORT_CSV_PASSWORD` は `設定済み（非表示）` と表示されます。`MF_IMPORT_CSV_ACCOUNT_URL` は実URLを表示せず、設定済みかどうかだけを表示します。

### 3.2 口座の取得

インポート先口座は、次のいずれかで指定します。

| 指定方法 | 優先度 | 説明 |
| --- | --- | --- |
| `--account` | 高 | `account_aliases.json` のエイリアスから手入力口座IDを引きます。 |
| `--account-id` | 中 | 手入力口座IDを直接指定します。 |
| `MF_IMPORT_CSV_ACCOUNT_URL` | 低 | `.env` の既定URLを使います。 |

手入力口座のエイリアスファイルは、Money Forwardの口座一覧から生成できます。

```sh
python mf_import_csv.py --generate-account-aliases
```

このコマンドはMoney Forwardへログインし、`https://moneyforward.com/accounts` にある `/accounts/show_manual/<口座ID>` のリンクから手入力口座だけを抽出して `account_aliases.json` を作成します。口座IDは数字だけでなく英数字、`_`、`-` を含む不透明IDとして扱います。自動連携口座は対象にしません。

手入力口座リンクが見つからないなど、口座エイリアス生成に失敗した場合は、調査用ファイルを `logs/debug/generate-account-aliases_YYYYMMDD_HHMMSS/` に保存します。保存先はエラー時のログに表示されます。保存内容には現在URL、ページタイトル、スクリーンショット、HTML、リンク一覧、手入力口座候補一覧、エラー内容、実行モード情報が含まれるため、必要な確認が終わったら共有や保管範囲に注意してください。

既に `account_aliases.json` がある場合は上書きしません。別ファイルへ出力する場合は `--output` を使います。

```sh
python mf_import_csv.py --generate-account-aliases --output account_aliases.new.json
```

既存ファイルを上書きする場合だけ、明示的に `--force` を付けます。

```sh
python mf_import_csv.py --generate-account-aliases --force
```

エイリアスを使う場合は、次のように実行します。

```sh
python mf_import_csv.py data.csv --account cash
```

手入力口座IDを直接指定する場合は、次のように実行します。

```sh
python mf_import_csv.py data.csv --account-id 123456
```

`--account` と `--account-id` は同時に指定できません。

### 3.3 インポート手順

まずCSV検証だけを実行します。Money Forwardへの接続、ログイン、ブラウザ起動、登録処理は行いません。

```sh
python mf_import_csv.py data.csv --validate-only
```

次にdry-runで登録予定内容を確認します。dry-runもMoney Forwardへ接続しません。

```sh
python mf_import_csv.py data.csv --dry-run
```

問題がなければインポートを実行します。

```sh
python mf_import_csv.py data.csv --account cash
```

通常実行では、CSV検証に成功した後、Money Forwardへログインしてインポート先口座ページを開きます。各取引について「手入力」フォームを開き、日付、金額、カテゴリ、内容を入力して保存します。

実行前に、次を確認してください。

- dry-runの対象件数、支出/収入、日付、金額、カテゴリが想定通りである。
- `--account`、`--account-id`、`.env` のどれでインポート先口座が決まるか確認済みである。
- カテゴリ名がMoney Forward画面上の大項目・中項目と一致している。
- 2段階認証や追加認証が表示された場合に、ブラウザ上で対応できる状態である。

## 4. インポートCSVのフォーマット

CSVはUTF-8で読み込みます。データ行には少なくとも10列が必要です。

| 列番号 | 列名 | 必須 | 使われ方 |
| --- | --- | --- | --- |
| 0 | 計算対象 | 必須 | `#`、`0`、`計算対象` の行はスキップします。それ以外を登録対象にします。 |
| 1 | 日付 | 必須 | `YYYY/MM/DD` 形式として検証し、Money Forwardの日時欄へ入力します。 |
| 2 | 内容 | 必須 | Money Forwardの内容欄へ入力します。 |
| 3 | 金額（円） | 必須 | 整数として検証します。正の値は収入、負の値は支出です。0はエラーです。 |
| 4 | 保有金融機関 | 任意 | 現在の登録処理では入力に使いません。 |
| 5 | 大項目 | 任意 | `未分類` 以外の場合、Money Forwardの大項目として選択します。 |
| 6 | 中項目 | 任意 | `未分類` 以外の場合、Money Forwardの中項目として選択します。先頭が `'` の場合は外して選択します。 |
| 7 | メモ | 任意 | 内容欄に `内容（メモ）` の形で連結します。空なら内容だけを使います。 |
| 8 | 振替 | 任意 | 現在の登録処理では入力に使いません。 |
| 9 | ID | 任意 | 現在の登録処理では入力に使いません。 |

Money Forwardへの登録項目との対応は次の通りです。

| Money Forward側の項目 | CSVまたは設定からの入力 |
| --- | --- |
| 登録先口座 | `--account`、`--account-id`、または `MF_IMPORT_CSV_ACCOUNT_URL` で決定します。 |
| 支出/収入 | `金額（円）` が正なら収入、負なら支出です。 |
| 日付 | CSVの `日付`。 |
| 金額 | CSVの `金額（円）` の絶対値。 |
| 大項目 | CSVの `大項目`。`未分類` の場合は選択しません。 |
| 中項目 | CSVの `中項目`。`未分類` の場合は選択しません。 |
| 内容 | CSVの `内容` と `メモ`。最大50文字に切り詰めます。 |

サンプルCSVです。

```csv
計算対象,日付,内容,金額（円）,保有金融機関,大項目,中項目,メモ,振替,ID
1,2026/06/01,コンビニ,-580,現金,食費,食料品,昼食,,sample-001
1,2026/06/02,売上,12000,現金,収入,事業収入,イベント,,sample-002
0,2026/06/03,対象外,-1000,現金,未分類,未分類,,,sample-003
```

この例では、1行目はヘッダーとしてスキップされ、`計算対象` が `1` の2件だけが登録対象です。`計算対象` が `0` の行はスキップされます。

dry-runでは、登録対象ごとに次のような情報が表示されます。

```text
[2] 支出 2026/06/01 -580 内容: コンビニ 大項目: 食費 中項目: 食料品
[3] 収入 2026/06/02 12000 内容: 売上 大項目: 収入 中項目: 事業収入
Summary:
- target: 2
- skipped: 2
- errors: 0
- warnings: 0
```

CSV検証では次を確認します。

- CSVファイルが存在すること。
- CSVがUTF-8で読み込めること。
- 各データ行に10列以上あること。
- 日付が `YYYY/MM/DD` 形式として妥当であること。
- 金額が整数であること。
- 金額が `0` ではないこと。

検証エラーがある場合、通常実行でもMoney Forwardへ接続せずに終了します。

## 5. コマンド一覧

| コマンド | 用途 | 実行例 |
| --- | --- | --- |
| `--setup` | `.env` を対話形式で作成します。 | `python mf_import_csv.py --setup` |
| `--show-config` | 現在の設定状態を安全に表示します。 | `python mf_import_csv.py --show-config` |
| `--generate-account-aliases` | Money Forwardの手入力口座一覧から `account_aliases.json` を生成します。 | `python mf_import_csv.py --generate-account-aliases` |
| `--generate-account-aliases --output` | 口座エイリアスを指定ファイルへ出力します。 | `python mf_import_csv.py --generate-account-aliases --output account_aliases.new.json` |
| `--generate-account-aliases --force` | 既存の出力先を上書きして口座エイリアスを生成します。 | `python mf_import_csv.py --generate-account-aliases --force` |
| `--validate-only` | CSV検証だけを行います。Money Forwardへ接続しません。 | `python mf_import_csv.py data.csv --validate-only` |
| `--dry-run` | CSVを検証し、登録予定内容だけを表示します。Money Forwardへ接続しません。 | `python mf_import_csv.py data.csv --dry-run` |
| `--account-id` | 手入力口座IDを直接指定してインポートします。 | `python mf_import_csv.py data.csv --account-id 123456` |
| `--account` | `account_aliases.json` のエイリアスで口座を指定してインポートします。 | `python mf_import_csv.py data.csv --account cash` |
| 通常インポート | `.env` の `MF_IMPORT_CSV_ACCOUNT_URL` を使ってインポートします。 | `python mf_import_csv.py data.csv` |

補足:

- `--setup`、`--show-config`、`--generate-account-aliases` は相互排他です。
- `--dry-run` と `--validate-only` は同時に使えません。
- `--output` と `--force` は `--generate-account-aliases` と一緒に使う場合だけ有効です。
- `--account` と `--account-id` は同時に使えません。

## 6. よくある注意点

### `.env` が見つからない

`.env` は隠しファイルです。MacのFinderなどで見えない場合は、`--setup` を使うか、ターミナルで確認してください。

```sh
ls -la
```

`.env` がない状態で通常インポートや口座取得を実行すると、必要な環境変数が不足して終了します。

### `.env` を作り直したい

`--setup` は既存の `.env` を上書きしません。変更したい場合は、既存の `.env` を手動で編集するか、バックアップしてから作り直してください。

### ログインに失敗する

`--show-config` で `MF_IMPORT_CSV_USER` と `MF_IMPORT_CSV_PASSWORD` が設定済みか確認してください。2段階認証や追加認証が表示された場合は、画面の案内に従ってコードを入力します。

Playwrightで `MF_IMPORT_CSV_REUSE_LOGIN_SESSION="true"` を使う場合、初回ログイン後のブラウザ状態は `MF_IMPORT_CSV_BROWSER_PROFILE_DIR` に保存されます。サービス側が再確認を求めた場合は、再度認証が必要です。

### 口座IDが分からない

手入力口座を使う場合は、`--generate-account-aliases` で `account_aliases.json` を生成し、口座名からエイリアス指定するのが基本です。生成されるJSONには実口座IDが含まれるため、Gitへ追加しないでください。

### CSV形式エラーが出る

`--validate-only` でエラー内容を確認してください。よくある原因は、列数不足、日付形式の誤り、金額が整数ではない、金額が0になっている、UTF-8以外の文字コードになっている、などです。

### カテゴリが選択できない

CSVの `大項目` と `中項目` はMoney Forward画面上のリンクテキストと一致している必要があります。`未分類` の場合はカテゴリ選択をスキップします。

### Money Forward画面が変わった

このツールはMoney Forwardの画面要素を使って操作します。Money Forward側のUI変更により、ボタン、入力欄、カテゴリ選択が見つからなくなる可能性があります。

### 実行前に安全確認したい

通常インポートの前に、必ず次のどちらかを実行してください。

```sh
python mf_import_csv.py data.csv --validate-only
python mf_import_csv.py data.csv --dry-run
```

どちらもMoney Forwardへの接続や登録処理は行いません。

## ライセンス

このプロジェクトはMITライセンスのもとで公開されています。

## 作者

このスクリプトはnanosnsによって開発・管理されています。
