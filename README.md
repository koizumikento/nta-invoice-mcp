# nta-invoice-mcp

国税庁のインボイス公表情報を、MCP・CLI・Pythonから照会できます。取引日時点の登録状況を最大10件まとめて確認でき、登録番号ごとの公表履歴も取得できます。

[MCP登録](#mcpクライアントに登録する) · [CLI](#cliで使う) · [Pythonライブラリ](#pythonライブラリとして使う)

## 利用前に

[uv](https://docs.astral.sh/uv/) と Git が必要です。Python 3.12以上に対応しています。[国税庁への届出](https://www.invoice-kohyo.nta.go.jp/web-api/index.html)で発行されたインボイスWeb-API用のアプリケーションIDが必要です。下の例の `YOUR_NTA_INVOICE_APP_ID` を手元の設定で差し替えてください。

## MCPクライアントに登録する

公開GitHubリポジトリから `uvx` で起動します。初回は依存関係の準備に時間がかかることがあります。

### Codex

```sh
codex mcp add nta-invoice-mcp --env "NTA_INVOICE_APP_ID=YOUR_NTA_INVOICE_APP_ID" -- uvx --python 3.12 --from git+https://github.com/koizumikento/nta-invoice-mcp.git@main nta-invoice-mcp
codex mcp list
```

新しいセッションで `/mcp` を開くと、接続を確認できます。デスクトップ版では設定の「MCP servers」で、下のJSON例と同じコマンド・引数・環境変数を指定できます。[Codexの公式設定ガイド](https://learn.chatgpt.com/docs/extend/mcp?surface=cli)

### Claude Desktop / Cursor

- Claude Desktop（Windows） `%APPDATA%/Claude/claude_desktop_config.json`
- Claude Desktop（macOS） `~/Library/Application Support/Claude/claude_desktop_config.json`
- Cursor `.cursor/mcp.json`（プロジェクト内）

設定ファイルの `mcpServers` に項目を追加して、クライアントを再起動してください。`uvx` が見つからない場合は、実行ファイルの絶対パスを指定します。

```json
{
  "mcpServers": {
    "nta-invoice-mcp": {
      "command": "uvx",
      "args": ["--python", "3.12", "--from", "git+https://github.com/koizumikento/nta-invoice-mcp.git@main", "nta-invoice-mcp"],
      "env": {"NTA_INVOICE_APP_ID": "YOUR_NTA_INVOICE_APP_ID"}
    }
  }
}
```

登録後の質問例

> この取引先のインボイス登録番号について、2024年4月1日時点の公表上の登録状況と出典を確認して。

> この取引先の登録履歴から、取消日や失効日が公表されているか確認して。

## MCPツール

| ツール | 用途 | 引数 |
| --- | --- | --- |
| `lookup_invoice_registration` | 1件の登録状況を指定日で確認する | `registration_number`, `day` |
| `lookup_invoice_registrations` | 最大10件の登録状況を同じ日付で確認する | `registration_numbers`（配列）, `day` |
| `get_invoice_registration_history` | 1件の公表履歴を取得する | `registration_number` |

登録番号は `T` と13桁の数字、日付は `YYYY-MM-DD` です。指定日照会の `status` は `registered`（登録あり）、`not_registered`（登録期間外）、`no_record`（指定条件の公表情報なし）、`unknown`（公表情報はあるが登録日がなく判定不可）のいずれかです。一括照会では、公表情報が見つからなかった番号も含めて入力順に返します。

履歴は古い順に返します。各行に名称・登録日・取消日・失効日・更新日があり、`process_code` で新規（`"01"`）、公表内容の変更（`"02"`）、失効（`"03"`）、取消（`"04"`）を確認できます。`latest` が `"1"` の行は最新、`"0"` は過去の履歴です。各ツールはデータの最終更新日と出典も返します。

## CLIで使う

CLIやPythonを実行するシェルで環境変数を設定します。

```powershell
$env:NTA_INVOICE_APP_ID = "YOUR_NTA_INVOICE_APP_ID"
```

macOSやLinuxのシェルでは `export NTA_INVOICE_APP_ID="YOUR_NTA_INVOICE_APP_ID"` を使います。

結果は標準出力にUTF-8のJSONで返ります。下の番号は形式例です。実際に照会したい登録番号に差し替えてください。

```sh
uvx --python 3.12 --from git+https://github.com/koizumikento/nta-invoice-mcp.git@main nta-invoice-mcp lookup-invoice-registration --registration-number T0000000000000 --day 2024-04-01
uvx --python 3.12 --from git+https://github.com/koizumikento/nta-invoice-mcp.git@main nta-invoice-mcp lookup-invoice-registrations --registration-numbers T0000000000000 T0000000000001 --day 2024-04-01
uvx --python 3.12 --from git+https://github.com/koizumikento/nta-invoice-mcp.git@main nta-invoice-mcp get-invoice-registration-history --registration-number T0000000000000
```

## Pythonライブラリとして使う

自分のPythonプロジェクト（`pyproject.toml` があるディレクトリ）で依存関係に追加します。[CLIで使う](#cliで使う)と同様に、実行するシェルで `NTA_INVOICE_APP_ID` を設定してください。

```sh
uv add "git+https://github.com/koizumikento/nta-invoice-mcp.git@main"
```

次のコードを `example.py` に保存し、同じディレクトリで `uv run python example.py` を実行します。

```python
import asyncio

from nta_invoice_mcp import (
    get_invoice_registration_history,
    lookup_invoice_registration,
    lookup_invoice_registrations,
)

number = "T0000000000000"
day = "2024-04-01"
print(asyncio.run(lookup_invoice_registration(number, day)))
print(asyncio.run(lookup_invoice_registrations([number, "T0000000000001"], day)))
print(asyncio.run(get_invoice_registration_history(number)))
```

すでにイベントループがある場合は、関数を直接 `await` してください。

## 出典と利用条件

コードはMIT Licenseです。照会結果を扱う場合は、個人事業者の情報を含め、国税庁の利用規約に従って管理してください。

照会には登録番号を指定します。期間を指定した全件差分の取得には対応していません。

このサービスは、適格請求書発行事業者公表システムWeb-API機能を利用して取得した情報をもとに作成しているが、サービスの内容は国税庁によって保証されたものではない。

[公式API案内](https://www.invoice-kohyo.nta.go.jp/web-api/index.html) · [リクエスト・応答仕様](https://www.invoice-kohyo.nta.go.jp/files/k-web-api-kinou.pdf) · [Web-API利用規約](https://www.invoice-kohyo.nta.go.jp/web-api/riyou_kiyaku.html)

## 開発

```sh
uv sync --locked
uv run ruff check .
uv run ty check
uv run pytest
uv build
```
