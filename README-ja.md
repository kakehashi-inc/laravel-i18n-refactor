# Laravel i18n リファクタリングツール

LaravelプロジェクトのBladeテンプレートとPHPファイルからハードコードされた文字列を抽出し、国際化を支援するCLIツールです。

## 機能

- 🔍 Laravelプロジェクト内のハードコード文字列を自動検出
- 📝 BladeテンプレートとPHPファイルの両方に対応
- 🎯 翻訳済み文字列を除外するスマートフィルタリング
- 📊 複数ファイルの重複文字列を統合
- 📁 統合しやすい構造化されたJSON出力

## インストール

```bash
# uvxを使用（推奨 - インストール不要）
uvx laravel-i18n-refactor extract .

# またはuvでインストール
uv pip install laravel-i18n-refactor

# またはpipでインストール
pip install laravel-i18n-refactor
```

## 使用方法

### ハードコード文字列の抽出

```bash
# uvxを使用（インストール不要）
uvx laravel-i18n-refactor extract .

# Bladeテンプレートのみから抽出
uvx laravel-i18n-refactor extract resources/views -n "**/*.blade.php" -o strings.json

# 特定ディレクトリから抽出
uvx laravel-i18n-refactor extract app/Http/Controllers -n "*.php" -o output.json

# インストール済みの場合は直接コマンドを使用
laravel-i18n-refactor extract .
```

### コマンドラインオプション

```text
laravel-i18n-refactor extract <directory> [OPTIONS]

引数:
  directory                 探索対象ディレクトリ

オプション:
  -n, --name PATTERN        ファイル名パターン（デフォルト: "**/*.php"）
                            例: "**/*.blade.php", "*.php", "**/*_controller.php"

  -o, --output FILE         出力JSONファイルパス（デフォルト: 標準出力）
                            指定しない場合は標準出力に出力されます

  -e, --exclude DIR         除外するディレクトリ名（複数回指定可能、デフォルト: node_modules）
                            例: -e vendor -e storage -e tests

  --split-threshold NUM     出力ファイルの分割閾値（デフォルト: 100）
                            抽出された文字列がこの数を超えると自動的に複数ファイルに分割
                            0を指定すると分割を無効化

  --min-bytes NUM           抽出する文字列の最小バイト長（デフォルト: 2）
                            この値未満のバイト数の文字列は除外されます

  --include-hidden          隠しディレクトリ（.で始まるディレクトリ）を検索対象に含める
                            デフォルト: False（隠しディレクトリはスキップ）

  --context-lines NUM       出力に含めるコンテキスト行数（デフォルト: 5）
                            5の場合: 対象行の前2行 + 対象行 + 後2行
                            0を指定するとコンテキスト出力を無効化

  --enable-blade            .blade.phpファイルの処理を有効化（デフォルト: True）

  --disable-blade           .blade.phpファイルの処理を無効化

  --enable-php              通常の.phpファイルの処理を有効化（デフォルト: False）

  --disable-php             通常の.phpファイルの処理を無効化（これがデフォルト）

  -h, --help                ヘルプメッセージを表示

使用例:
  # 基本的な使用方法（Bladeファイルのみ、デフォルト設定）
  uvx laravel-i18n-refactor extract .

  # 複数のディレクトリを除外
  uvx laravel-i18n-refactor extract . -e node_modules -e storage -e bootstrap/cache

  # 特定のパターンから抽出、複数の除外指定
  uvx laravel-i18n-refactor extract . -n "**/*.blade.php" -e tests -e vendor

  # BladeファイルとPHPファイルの両方を処理
  uvx laravel-i18n-refactor extract . --enable-php -o output.json

  # 分割閾値を変更（200項目ごとに分割）
  uvx laravel-i18n-refactor extract . -o output.json --split-threshold 200

  # 分割を無効化（すべて1つのファイルに出力）
  uvx laravel-i18n-refactor extract . -o output.json --split-threshold 0

  # コンテキスト行数を変更（7行: 前3行 + 対象行 + 後3行）
  uvx laravel-i18n-refactor extract . -o output.json --context-lines 7

  # コンテキスト出力を無効化
  uvx laravel-i18n-refactor extract . -o output.json --context-lines 0

  # 最小バイト長を変更（3バイト未満を除外）
  uvx laravel-i18n-refactor extract . -o output.json --min-bytes 3

  # 隠しディレクトリも含めて検索
  uvx laravel-i18n-refactor extract . --include-hidden
```

### 自動除外機能

ツールはLaravelプロジェクト（`composer.json`を検出）を自動的に識別し、以下を除外します：

**ユーザー指定の除外:**
- `-e`/`--exclude`で指定されたディレクトリ（デフォルト: `node_modules`）

**Laravelプロジェクト自動除外:**
- `vendor` - Composer依存関係
- `node_modules` - NPM依存関係
- `public` - 公開アセット（コンパイル済み/生成ファイル）
- `storage` - ストレージディレクトリ（ログ、キャッシュ、セッション）
- `bootstrap/cache` - ブートストラップキャッシュファイル

これらの自動除外により、依存関係や生成ファイルが処理されず、ソースコードに集中できます。

## 出力形式

以下の構造のJSONファイルを生成します：

```json
[
  {
    "text": "抽出された文字列内容",
    "occurrences": [
      {
        "file": "resources/views/example.blade.php",
        "positions": [
          {
            "line": 10,
            "column": 5,
            "length": 25,
            "context": [
              "    <div>",
              "        <h1>抽出された文字列内容</h1>",
              "    </div>"
            ]
          }
        ]
      }
    ]
  }
]
```

### 出力ファイルの自動分割

抽出された文字列が多い場合、出力ファイルは自動的に複数のファイルに分割されます：

- **デフォルト**: 100項目ごとに分割
- **分割例**: `output.json` → `output-01.json`, `output-02.json`, `output-03.json`, ...
- **カスタマイズ**: `--split-threshold` オプションで閾値を変更可能
- **分割無効化**: `--split-threshold 0` で分割を無効化し、すべて1つのファイルに出力

```bash
# デフォルト（100項目ごとに分割）
uvx laravel-i18n-refactor extract . -o output.json

# 閾値変更（200項目ごとに分割）
uvx laravel-i18n-refactor extract . -o output.json --split-threshold 200

# 分割無効化（すべて1つのファイル）
uvx laravel-i18n-refactor extract . -o output.json --split-threshold 0
```

**注意**: 標準出力（`-o`オプション未指定）の場合、分割は行われません。

### フィールドの説明

- `text`: 抽出された文字列内容（改行・タブ・スペース・エスケープシーケンスを保持）
- `occurrences`: 出現箇所の配列
- `file`: ファイルパス（探索ディレクトリからの相対パス）
- `positions`: 同一ファイル内の出現位置配列
- `line`: 行番号（1始まり）
- `column`: カラム番号（0始まり）
- `length`: 文字列の長さ（文字数）
- `context`: 該当行とその前後2行のコンテキスト（合計5行、ファイル境界では少なくなる場合あり）

## 抽出対象

### Bladeファイル (.blade.php)

**✅ 抽出対象:**

- HTMLタグ間のテキストノード
- HTML属性値
- `<script>`タグ内のJavaScript文字列リテラル

**❌ 除外対象:**

- 翻訳済み文字列（`{{ __() }}`、`@lang()`等）
- PHP変数（`{{ $variable }}`）
- Bladeディレクティブ（`@if`、`@foreach`等）
- コメント（HTMLおよびBlade）
- 空文字列または空白のみの文字列

### PHPファイル (.php)

**✅ 抽出対象:**

- バリデーションメッセージ
- 例外メッセージ
- レスポンスメッセージ
- ユーザー向けエラー・成功メッセージ

**❌ 除外対象:**

- 翻訳済み文字列（`__()`、`trans()`等）
- ログメッセージ（`Log::info()`、`logger()`等）
- コンソール出力（`echo`、`print`、`var_dump()`等）
- コマンド出力（`$this->info()`、`$this->error()`等）
- 配列キー
- コメント
- 空文字列または空白のみの文字列

### 例

**Blade抽出:**

```html
<!-- 抽出: "Welcome to Laravel" -->
<h1>Welcome to Laravel</h1>

<!-- 抽出: "Enter your name" -->
<input placeholder="Enter your name">

<!-- 除外: 翻訳済み -->
<p>{{ __('messages.welcome') }}</p>

<!-- 除外: 変数 -->
<p>{{ $userName }}</p>
```

**PHP抽出:**

```php
// 抽出: "This field is required"
'required' => 'This field is required',

// 抽出: "User not found"
throw new Exception('User not found');

// 除外: 翻訳済み
__('messages.welcome')

// 除外: ログメッセージ
Log::info('Processing started');

// 除外: 配列キー、ただし "John" は抽出
'name' => 'John',
```

## 開発

```bash
# リポジトリのクローン
git clone https://github.com/kakehashi-inc/laravel-i18n-refactor.git
cd laravel-i18n-refactor

# uvで依存関係をインストール
uv pip install -e ".[dev]"

# テスト実行
uv run pytest
```

## 必要要件

- Python 3.7以上
- beautifulsoup4 >= 4.12.0
- lxml >= 4.9.0

## ライセンス

MIT License - 詳細は[LICENSE](LICENSE)ファイルを参照してください

## コントリビューション

プルリクエストを歓迎します！お気軽にご提案ください。

## 関連ドキュメント

- [English README](README.md)
