---
name: test
description: Test Polymarket wallet connection and API connectivity. Use when you need to verify that the pt skill environment is correctly configured and the wallet connection is working.
---

# Polymarket Connection Test

驗證 Polymarket 錢包連線和 API 環境是否正常運作。

## When to Use

- 首次設定 pt skill 後驗證環境
- 交易失敗時診斷連線問題
- 帳戶憑證變更後確認配置正確
- API 異常時排查根因

## Quick Start

```bash
# 使用父目錄的 venv（必須）
cd /path/to/pt
source venv/bin/activate

# 基本連線測試（所有帳戶）
python test/scripts/test_wallet_connection.py

# 測試指定帳戶
python test/scripts/test_wallet_connection.py --account 2

# 只測試 API 連線（不需要憑證）
python test/scripts/test_wallet_connection.py --public-only
```

## Test Coverage

| 測試項目          | 說明                                                      |
| ----------------- | --------------------------------------------------------- |
| **Env Vars**      | 檢查 POLYGON_PRIVATE_KEY, BUILDER_WALLET_ADDRESS 是否設定 |
| **Public API**    | 測試 CLOB API 公開端點連線                                |
| **Wallet Auth**   | 建立 API 憑證（create_or_derive_api_creds）               |
| **Balance**       | 查詢 USDC 餘額                                            |
| **Multi-Account** | 逐一測試所有已配置帳戶                                    |

## Resources

- `scripts/test_wallet_connection.py` - 主測試腳本
- 父目錄 `venv/` - 使用 pt skill 的共用虛擬環境
- 父目錄 `.env` - 環境變數配置

## Notes

- 必須從 `pt/` 根目錄執行（需要存取 `scripts/utils/client.py`）
- `.env` 必須在 `pt/` 目錄（不在 `test/` 子目錄）
