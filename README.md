# nta-invoice-mcp

国税庁のインボイス公表サイトで、登録番号1件を指定日で照会できます。登録日・取消日・失効日と、公表情報上の登録状況を確認できます。

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

## MCPツール

### `lookup_invoice_registration`

`registration_number` は `T` と13桁の数字、`day` は `YYYY-MM-DD` です。`status` は `registered`（登録あり）、`not_registered`（登録期間外）、`no_record`（指定条件の公表情報なし）、`unknown`（公表情報はあるが登録日がなく判定不可）のいずれかです。データの最終更新日も返します。

## CLIで使う

CLIやPythonを実行するシェルで環境変数を設定します。

```powershell
$env:NTA_INVOICE_APP_ID = "YOUR_NTA_INVOICE_APP_ID"
```

macOSやLinuxのシェルでは `export NTA_INVOICE_APP_ID="YOUR_NTA_INVOICE_APP_ID"` を使います。

結果は標準出力にUTF-8のJSONで返ります。下の番号は形式例です。実際に照会したい登録番号に差し替えてください。

```sh
uvx --python 3.12 --from git+https://github.com/koizumikento/nta-invoice-mcp.git@main nta-invoice-mcp lookup-invoice-registration --registration-number T0000000000000 --day 2024-04-01
```

## Pythonから呼び出す

```sh
git clone https://github.com/koizumikento/nta-invoice-mcp.git
cd nta-invoice-mcp
uv sync --locked
```

```python
import asyncio

from nta_invoice_mcp import lookup_invoice_registration

result = asyncio.run(lookup_invoice_registration("T0000000000000", "2024-04-01"))
print(result)
```

すでにイベントループがある場合は、関数を直接 `await` してください。

## 出典と利用条件

コードはMIT Licenseです。照会結果を扱う場合は、個人事業者の情報を含め、国税庁の利用規約に従って管理してください。

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
