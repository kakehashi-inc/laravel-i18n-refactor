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
  directory              探索対象ディレクトリ

オプション:
  -n, --name PATTERN    ファイル名パターン (デフォルト: "**/*.php")
  -o, --output FILE     出力JSONファイルパス (デフォルト: 標準出力)
  -h, --help           ヘルプメッセージを表示
```

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
            "length": 25
          }
        ]
      }
    ]
  }
]
```

### フィールドの説明

- `text`: 抽出された文字列内容（改行・タブ・スペース・エスケープシーケンスを保持）
- `occurrences`: 出現箇所の配列
- `file`: ファイルパス（探索ディレクトリからの相対パス）
- `positions`: 同一ファイル内の出現位置配列
- `line`: 行番号（1始まり）
- `column`: カラム番号（0始まり）
- `length`: 文字列の長さ（文字数）

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
