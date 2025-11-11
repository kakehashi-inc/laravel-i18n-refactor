# Laravel i18n リファクタリングツール

LaravelプロジェクトのBladeテンプレートとPHPファイルからハードコードされた文字列を抽出し、国際化を支援するCLIツールです。

## 機能

- 🔍 Laravelプロジェクト内のハードコード文字列を自動検出
- 📝 BladeテンプレートとPHPファイルの両方に対応
- 🎯 翻訳済み文字列を除外するスマートフィルタリング
- 📊 複数ファイルの重複文字列を統合
- 📁 統合しやすい構造化されたJSON出力

## 使用方法

### 文字列抽出（extract）

#### コマンドラインオプション

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

  --exclude-dict FILE       除外する文字列を含むテキストファイルのパス（1行に1つ）

  -h, --help                ヘルプメッセージを表示

使用例:
  # Bladeテンプレートのみから抽出
  uvx laravel-i18n-refactor extract resources/views -n "**/*.blade.php" -o output.json

  # 複数のディレクトリを除外
  uvx laravel-i18n-refactor extract ~/sources/test-project -e Archive -e temp -o output.json
```

#### 出力形式

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

#### 除外辞書

特定の文字列を抽出から除外したい場合、--exclude-dictオプションで除外辞書を指定できます。

##### 構文

除外辞書はグロブパターンと正規表現の両方をサポートします：

| 構文 | 説明 | 例 |
|------|------|------|
| `word` | 完全一致（大文字小文字区別あり） | `label` は "label" を除外 |
| `*` | ワイルドカード（任意の文字列にマッチ） | `data-*` は "data-id", "data-name" を除外 |
| `[0-9]` | 文字クラス | `[0-9]*` は数字で始まる文字列を除外 |
| `regex:PATTERN` | 正規表現 | `regex:^\d+x\d+$` は "600x600", "1920x1080" を除外 |
| `!pattern` | 除外の否定（前のパターンで除外されたものを含める） | `!data-important` は "data-important" を含める |
| `# comment` | コメント行（無視される） | `# これはコメント` |

**注意**: 正規表現はPythonの正規表現パターンとして評価されます。無効な正規表現パターンは黙って無視されます。

### AI翻訳（translate）

このツールは様々なAIプロバイダーを使用して抽出された文字列を翻訳する機能をサポートしています。

#### 翻訳コマンド

```bash
laravel-i18n-refactor translate <プロバイダー> --model <モデル名> -i <入力ファイル> [オプション]
```

#### 利用可能なプロバイダー

| プロバイダー | コマンド | 説明 |
|----------|---------|-------------|
| OpenAI | `openai` |  |
| Anthropic | `anthropic` |  |
| Gemini | `gemini` |  |
| OpenAI互換 | `openai-compat` | OpenAI互換エンドポイント（LM Studio、LocalAIなど） |
| Anthropic互換 | `anthropic-compat` | Anthropic互換エンドポイント（MiniMax M2など） |
| Ollama | `ollama` |  |

#### 共通オプション（全プロバイダー）

| オプション | 説明 |
|--------|-------------|
| `-i, --input FILE` | 翻訳対象のJSONファイル（複数回指定可能） |
| `--lang CODE:DESCRIPTION` | 翻訳先言語（例: "ja:Japanese", "en:American English"） |
| `--list-models` | プロバイダーで利用可能なモデル一覧を表示 |
| `--dry-run` | API呼び出しなしで翻訳内容をプレビュー |

#### プロバイダー固有オプション

##### OpenAI

| オプション | 環境変数 | 説明 |
|--------|---------------------|-------------|
| `--model` | `OPENAI_MODEL` | モデル名（必須） |
| `--api-key` | `OPENAI_API_KEY` | OpenAI APIキー |
| `--organization` | `OPENAI_ORGANIZATION` | 組織ID |
| `--temperature` | `OPENAI_TEMPERATURE` | サンプリング温度 |
| `--max-tokens` | `OPENAI_MAX_TOKENS` | 最大トークン数 |
| `--batch-size` | `OPENAI_BATCH_SIZE` | バッチサイズ（デフォルト: 10） |

#### Anthropic (Claude)

| オプション | 環境変数 | 説明 |
|--------|---------------------|-------------|
| `--model` | `ANTHROPIC_MODEL` | モデル名（必須） |
| `--api-key` | `ANTHROPIC_API_KEY` | Anthropic APIキー |
| `--temperature` | `ANTHROPIC_TEMPERATURE` | サンプリング温度 |
| `--max-tokens` | `ANTHROPIC_MAX_TOKENS` | 最大トークン数（デフォルト: 4096） |

#### Google Gemini

| オプション | 環境変数 | 説明 |
|--------|---------------------|-------------|
| `--model` | `GEMINI_MODEL` | モデル名（必須） |
| `--api-key` | `GEMINI_API_KEY` または `GOOGLE_API_KEY` | Google APIキー |
| `--temperature` | `GEMINI_TEMPERATURE` | サンプリング温度 |
| `--max-tokens` | `GEMINI_MAX_TOKENS` | 最大出力トークン数 |
| `--top-p` | `GEMINI_TOP_P` | Nucleusサンプリング |
| `--top-k` | `GEMINI_TOP_K` | Top-kサンプリング |

#### OpenAI互換

| オプション | 環境変数 | 説明 |
|--------|---------------------|-------------|
| `--model` | `OPENAI_COMPAT_MODEL` | モデル名（必須） |
| `--api-base` | `OPENAI_COMPAT_API_BASE` | APIベースURL（必須） |
| `--api-key` | `OPENAI_COMPAT_API_KEY` | APIキー（必要な場合） |
| `--temperature` | `OPENAI_COMPAT_TEMPERATURE` | サンプリング温度 |
| `--max-tokens` | `OPENAI_COMPAT_MAX_TOKENS` | 最大トークン数 |

参考値:

api-base: <http://localhost:1234/v1>

##### Anthropic互換

| オプション | 環境変数 | 説明 |
|--------|---------------------|-------------|
| `--model` | `ANTHROPIC_COMPAT_MODEL` | モデル名（必須） |
| `--api-base` | `ANTHROPIC_COMPAT_API_BASE` | APIベースURL（必須） |
| `--api-key` | `ANTHROPIC_COMPAT_API_KEY` | APIキー（必須） |
| `--temperature` | `ANTHROPIC_COMPAT_TEMPERATURE` | サンプリング温度 |
| `--max-tokens` | `ANTHROPIC_COMPAT_MAX_TOKENS` | 最大トークン数（デフォルト: 4096） |

##### Ollama

| オプション | 環境変数 | 説明 |
|--------|---------------------|-------------|
| `--model` | `OLLAMA_MODEL` | モデル名（必須） |
| `--api-base` | `OLLAMA_HOST` | OllamaサーバーURL（デフォルト: http://localhost:11434） |
| `--temperature` | `OLLAMA_TEMPERATURE` | サンプリング温度 |
| `--max-tokens` | `OLLAMA_MAX_TOKENS` | 最大トークン数 |
| `--num-ctx` | `OLLAMA_NUM_CTX` | コンテキストウィンドウサイズ |
| `--top-p` | `OLLAMA_TOP_P` | Nucleusサンプリング |
| `--top-k` | `OLLAMA_TOP_K` | Top-kサンプリング |
| `--repeat-penalty` | `OLLAMA_REPEAT_PENALTY` | 繰り返しペナルティ |

## 開発

### 開発環境セットアップ

```bash
# リポジトリのクローン
git clone https://github.com/kakehashi-inc/laravel-i18n-refactor.git
cd laravel-i18n-refactor

python -m venv venv

# 仮想環境を有効化
# Windows:
.\venv\Scripts\Activate.ps1
# Linux/macOS:
source venv/bin/activate

# 開発モードでインストール
pip install -e ".[dev]"
```

## ライセンス

MIT License - 詳細は[LICENSE](LICENSE)ファイルを参照してください

## コントリビューション

プルリクエストを歓迎します！お気軽にご提案ください。

## 関連ドキュメント

- [English README](README.md)
