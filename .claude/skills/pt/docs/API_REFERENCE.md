# Polymarket Trader API Reference

Polymarket CLOB (Central Limit Order Book) API 的詳細參考文檔。

## 概述

Polymarket 使用 CLOB API 來處理所有的市場數據查詢和交易執行。API 基於 REST 架構。

## Base URL

```
https://clob.polymarket.com
```

## 認證

目前大部分 API endpoints 不需要認證。交易相關的操作需要使用私鑰簽名。

## 主要 Endpoints

### 1. 獲取市場列表

**Endpoint**: `GET /markets`

**參數**:
- `search` (string, optional): 搜尋關鍵字
- `limit` (integer, optional): 返回結果數量，預設 10
- `offset` (integer, optional): 分頁偏移量
- `active` (boolean, optional): 只顯示活躍市場

**回應範例**:
```json
[
  {
    "condition_id": "0x123...",
    "question": "Will Bitcoin reach $100k in 2025?",
    "outcomes": [
      {
        "name": "Yes",
        "price": 0.65,
        "token_id": "123"
      },
      {
        "name": "No",
        "price": 0.35,
        "token_id": "124"
      }
    ],
    "volume": 2500000,
    "liquidity": 500000,
    "end_date_iso": "2025-12-31T23:59:59Z",
    "active": true,
    "closed": false
  }
]
```

### 2. 獲取市場詳情

**Endpoint**: `GET /markets/{market_id}`

**參數**:
- `market_id` (string): 市場的 condition_id

**回應**: 單個市場對象 (同上)

### 3. 獲取訂單簿

**Endpoint**: `GET /orderbook/{market_id}`

**參數**:
- `market_id` (string): 市場 ID
- `side` (string, optional): "buy" 或 "sell"

**回應範例**:
```json
{
  "bids": [
    {
      "price": 0.64,
      "size": 100.50,
      "timestamp": 1234567890
    }
  ],
  "asks": [
    {
      "price": 0.66,
      "size": 85.25,
      "timestamp": 1234567891
    }
  ]
}
```

### 4. 創建訂單

**Endpoint**: `POST /orders`

**請求體**:
```json
{
  "market": "0x123...",
  "side": "buy",
  "type": "limit",
  "price": 0.65,
  "size": 10.0,
  "signature": "0xabc...",
  "timestamp": 1234567890
}
```

**訂單類型**:
- `limit`: 限價單 - 指定價格
- `market`: 市價單 - 立即成交
- `post_only`: 只掛單不吃單

**回應**:
```json
{
  "order_id": "xyz789",
  "status": "pending",
  "created_at": 1234567890,
  "market": "0x123...",
  "side": "buy",
  "price": 0.65,
  "size": 10.0,
  "filled": 0.0
}
```

### 5. 查詢持倉

**Endpoint**: `GET /positions`

**參數**:
- `address` (string): 錢包地址

**回應範例**:
```json
[
  {
    "market": {
      "condition_id": "0x123...",
      "question": "Will Bitcoin reach $100k?"
    },
    "outcome": "Yes",
    "token_id": "123",
    "shares": 10.5,
    "avg_price": 0.62,
    "current_price": 0.65,
    "unrealized_pnl": 0.315
  }
]
```

### 6. 查詢訂單歷史

**Endpoint**: `GET /orders/history`

**參數**:
- `address` (string): 錢包地址
- `market` (string, optional): 篩選特定市場
- `status` (string, optional): "filled", "cancelled", "pending"

### 7. 取消訂單

**Endpoint**: `DELETE /orders/{order_id}`

**參數**:
- `order_id` (string): 訂單 ID
- `signature` (string): 簽名

## 簽名機制

Polymarket 使用 EIP-712 簽名標準。

### 訂單簽名流程

1. **構建訂單對象**:
```python
order = {
    "market": market_id,
    "side": "buy",
    "price": price,
    "size": size,
    "timestamp": int(time.time()),
    "nonce": nonce
}
```

2. **創建 EIP-712 結構化數據**:
```python
domain = {
    "name": "Polymarket CLOB",
    "version": "1",
    "chainId": 137,  # Polygon
    "verifyingContract": CLOB_CONTRACT_ADDRESS
}

types = {
    "Order": [
        {"name": "market", "type": "address"},
        {"name": "side", "type": "uint8"},
        {"name": "price", "type": "uint256"},
        {"name": "size", "type": "uint256"},
        {"name": "timestamp", "type": "uint256"},
        {"name": "nonce", "type": "uint256"}
    ]
}
```

3. **簽名**:
```python
from eth_account.messages import encode_structured_data

structured_data = {
    "types": types,
    "domain": domain,
    "primaryType": "Order",
    "message": order
}

signable_message = encode_structured_data(structured_data)
signed = account.sign_message(signable_message)
signature = signed.signature.hex()
```

## USDC 合約

Polymarket 使用 USDC 作為交易貨幣。

**USDC 合約地址 (Polygon)**:
```
0x2791Bca1f2de4661ED88A30C99A7a9449Aa84174
```

### Approval 流程

交易前需要 approve CLOB 合約使用你的 USDC:

```python
from web3 import Web3

usdc_contract = w3.eth.contract(
    address=USDC_ADDRESS,
    abi=USDC_ABI
)

# Approve CLOB 合約
tx = usdc_contract.functions.approve(
    CLOB_CONTRACT_ADDRESS,
    amount_in_wei  # 使用 6 decimals for USDC
).build_transaction({
    'from': wallet_address,
    'nonce': w3.eth.get_transaction_count(wallet_address),
    'gas': 100000,
    'gasPrice': w3.eth.gas_price
})

signed_tx = w3.eth.account.sign_transaction(tx, private_key)
tx_hash = w3.eth.send_raw_transaction(signed_tx.rawTransaction)
```

## 錯誤處理

### 常見錯誤碼

- `400 Bad Request`: 請求參數錯誤
- `401 Unauthorized`: 簽名驗證失敗
- `404 Not Found`: 市場或訂單不存在
- `429 Too Many Requests`: 請求頻率過高
- `500 Internal Server Error`: 服務器錯誤

### 錯誤回應格式

```json
{
  "error": "Invalid signature",
  "code": "INVALID_SIGNATURE",
  "details": "Signature verification failed"
}
```

## Rate Limiting

- 每個 IP 每分鐘最多 60 次請求
- 交易相關操作每分鐘最多 10 次

建議使用 exponential backoff 重試機制。

## WebSocket API

實時市場數據可以通過 WebSocket 獲取:

```
wss://clob.polymarket.com/ws
```

### 訂閱市場更新

```json
{
  "type": "subscribe",
  "channel": "market",
  "market_id": "0x123..."
}
```

### 接收價格更新

```json
{
  "type": "price_update",
  "market_id": "0x123...",
  "outcome": "Yes",
  "price": 0.65,
  "timestamp": 1234567890
}
```

## 最佳實踐

1. **快取市場數據**: 市場列表不會頻繁變化，可以快取 5-10 分鐘
2. **使用 WebSocket**: 實時價格追蹤使用 WebSocket 而非輪詢
3. **批次請求**: 盡可能合併多個請求
4. **錯誤重試**: 實現 exponential backoff
5. **簽名快取**: 相同訂單的簽名可以快取（注意 nonce）

## 示例代碼

完整的 Python 示例代碼請參考 `scripts/` 目錄。

## 參考資源

- [Polymarket 官方文檔](https://docs.polymarket.com)
- [EIP-712 規範](https://eips.ethereum.org/EIPS/eip-712)
- [Web3.py 文檔](https://web3py.readthedocs.io)

---

**注意**: 此文檔基於 Polymarket CLOB API 的公開信息。實際 API 可能有所變化，請參考官方文檔獲取最新信息。
