# Polymarket 程式交易完整指南

> 最後更新：2025-12-04
> 狀態：✅ 已驗證成功

## 🎯 目標

使用 Python 同 Polymarket CLOB API 執行自動化交易。

## 📊 我哋解決咗嘅問題

### 核心挑戰：Builder Wallet Trading

**問題**：點樣用 Polymarket Builder wallet 入面嘅 USDC 嚟 trade？

傳統做法：
- 錢包 A (control) → 簽名
- 錢包 A (control) → 有資金
- 用錢包 A 嘅 private key 衍生 API keys

**我哋嘅情況**：
- 錢包 A (0x92dF9A... 我哋 control) → 簽名
- 錢包 B (0xf5459a... Builder wallet) → 有 $5.09 USDC
- Builder API keys (019ae73e...) → 只係用嚟 attribution，唔係 trade

**解決方案**：
- 用 `signature_type=1` (Magic Link mode)
- 用 `funder` parameter 指定 Builder wallet
- 用我哋嘅 PK 衍生 L2 API keys
- Builder wallet 提供資金，我哋嘅錢包簽名

## 🔧 環境設置

### 1. .env 配置

```bash
# Polymarket 環境變數
# ⚠️ 千祈唔好 commit 呢個 file!

# ========================================
# 錢包配置
# ========================================
# 你 control 嘅錢包 (用嚟簽名)
POLYGON_PRIVATE_KEY=ec207394fb56205bc3ebad623f8c7ffe75f7fa4fcb0d5511bb9e62e0bccf1b30
WALLET_ADDRESS=0x92dF9A0b5068690f02C18ABdC75985aC2906f6AF

# ========================================
# Polymarket API 配置 (衍生嘅 Trading API 憑證)
# ========================================
# 執行 python -c "from py_clob_client.client import ClobClient; client = ClobClient('https://clob.polymarket.com', key='YOUR_PK', chain_id=137); print(client.derive_api_key())"
POLYMARKET_API_KEY=9d8670bd-5925-4e09-8400-7688eddb9372
POLYMARKET_SECRET=MDYNV30dLi32qvIIJ8bpYCkWgLmOqrKp29QSXJql58M=
POLYMARKET_PASSPHRASE=f13125aba439ddc3d8d1b6076c776ebb76a3307b32f52fdd56b7b1a7ca1ca866

# ========================================
# Polymarket Builder API 配置 (Order Attribution)
# ========================================
# 從 https://polymarket.com/settings 獲取
POLY_BUILDER_API_KEY=019ae73e-d01f-7ed3-a687-460fe5fcadaa
POLY_BUILDER_SECRET=hEZphhGEhaDylY6osMJfFoWth_Myy_5ZTn-e5iUscMo=
POLY_BUILDER_PASSPHRASE=f194f6615806ba93d3f5a1e64ac171684ab90f7ec7b3ad6722ecd9c412c64092

# ========================================
# 網絡配置
# ========================================
POLYGON_RPC_URL=https://polygon-rpc.com
CHAIN_ID=137

# ========================================
# 交易配置
# ========================================
# 自動交易最大金額 (USDC)
MAX_AUTO_AMOUNT=5.0
```

### 2. Python 環境

```bash
cd /Users/terivercheung/Documents/AI/pi-vs-claude-code/.claude/skills/pt/scripts

# 創建 virtual environment
python -m venv venv
source venv/bin/activate

# 安裝 dependencies
pip install py-clob-client python-dotenv web3 eth-account
```

## 📁 所需 Python Scripts

### 1. `setup_polymarket_api.py` - 初始化 API

```python
#!/usr/bin/env python3
"""
設置 Polymarket API 憑證
用法: python setup_polymarket_api.py
"""
import os
import sys
from pathlib import Path
from dotenv import load_dotenv
from py_clob_client.client import ClobClient
from py_clob_client.constants import POLYGON

def main():
    """設置 Polymarket API 憑證"""
    # Load environment
    load_dotenv()

    private_key = os.getenv("POLYGON_PRIVATE_KEY")
    if not private_key:
        print("❌ 錯誤: 找不到 POLYGON_PRIVATE_KEY")
        return False

    # Initialize client
    client = ClobClient(
        host="https://clob.polymarket.com",
        key=private_key,
        chain_id=POLYGON
    )

    print("🔑 Deriving API credentials...")
    creds = client.derive_api_key()

    print("\n✅ 請將以下加入 .env:")
    print(f"POLYMARKET_API_KEY={creds.api_key}")
    print(f"POLYMARKET_SECRET={creds.api_secret}")
    print(f"POLYMARKET_PASSPHRASE={creds.api_passphrase}")

    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
```

### 2. `check_balance.py` - 檢查餘額

```python
#!/usr/bin/env python3
"""
檢查錢包 USDC 餘額
用法: python check_balance.py
"""
import os
from pathlib import Path
from dotenv import load_dotenv
from web3 import Web3

load_dotenv()

def check_balance():
    """檢查 USDC 餘額"""
    w3 = Web3(Web3.HTTPProvider(os.getenv("POLYGON_RPC_URL")))

    # USDC 合約
    USDC_ADDRESS = "0x2791Bca1f2de4661ED88A30C99A7a9449Aa84174"
    usdc_abi = [
        {
            "constant": True,
            "inputs": [{"name": "_owner", "type": "address"}],
            "name": "balanceOf",
            "outputs": [{"name": "balance", "type": "uint256"}],
            "type": "function"
        }
    ]
    usdc = w3.eth.contract(address=Web3.to_checksum_address(USDC_ADDRESS), abi=usdc_abi)

    # 檢查 Builder wallet
    builder_wallet = w3.to_checksum_address("0xf5459aeE5E781371Fe4D32c6FD74D6154F52cA3B")
    balance = usdc.functions.balanceOf(builder_wallet).call() / 10**6

    print(f"💰 Builder Wallet (0xf5459a): {balance} USDC")
    print(f"Minimum needed: 2.175 USDC (5 shares @ $0.435)")
    print(f"Can trade: {'✅ YES' if balance >= 2.175 else '❌ NO'}")

    return balance >= 2.175

if __name__ == "__main__":
    check_balance()
```

### 3. `execute_trade.py` - 執行交易

```python
#!/usr/bin/env python3
"""
執行 Polymarket 交易
用法: python execute_trade.py
"""
import os
import sys
from pathlib import Path
from dotenv import load_dotenv
from py_clob_client.client import ClobClient
from py_clob_client.clob_types import OrderArgs
from py_clob_client.constants import POLYGON

def execute_trade(market_id="0x18d8c59309811ce5618ea941f9bde2a96afa5d876a69c42fba2da4bcc56d3c5e",
                 outcome="yes",
                 size=5.0):
    """
    執行 Polymarket 交易

    Args:
        market_id: 市場 ID (從網址攞)
        outcome: "yes" 或 "no"
        size: 交易股數 (最少 5 shares)
    """
    # Load environment
    load_dotenv()

    private_key = os.getenv("POLYGON_PRIVATE_KEY")
    builder_funder = "0xf5459aeE5E781371Fe4D32c6FD74D6154F52cA3B"

    print("🔐 Initializing Polymarket CLOB Client...")

    # Initialize client with signature_type=1 for Builder wallet trading
    client = ClobClient(
        host="https://clob.polymarket.com",
        key=private_key,
        chain_id=POLYGON,
        signature_type=1,
        funder=builder_funder
    )

    # Derive and set API credentials
    creds = client.create_or_derive_api_creds()
    client.set_api_creds(creds)

    print(f"✅ Connected: {client.get_address()}")
    print(f"✅ Using Builder wallet for funding: {builder_funder}")

    # Get market
    print(f"\n📊 Fetching market...")
    market = client.get_market(market_id)
    print(f"Market: {market['question'][:60]}...")

    # Find token
    token_id = None
    price = 0.0
    for token in market.get("tokens", []):
        if token.get("outcome", "").lower() == outcome.lower():
            token_id = token["token_id"]
            price = float(token.get("price", 0))
            print(f"✅ {outcome.title()} Token: ${price}")
            break

    if not token_id:
        print(f"❌ {outcome} token not found")
        return False

    # Place order
    print(f"\n🚀 Placing order...")
    print(f"Size: {size} shares")
    print(f"Price: ${price}")
    print(f"Cost: ${size * price:.3f} USDC")

    order_args = OrderArgs(
        token_id=token_id,
        price=price,
        size=size,
        side="BUY",
        fee_rate_bps=0
    )

    try:
        result = client.create_and_post_order(order_args)
        print(f"\n🎉 SUCCESS!")
        print(f"Order ID: {result.get('orderID', 'N/A')}")
        print(f"Status: {result.get('status', 'Unknown')}")
        return True
    except Exception as e:
        print(f"\n❌ Failed: {str(e)[:200]}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Main function"""
    success = execute_trade()
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()
```

### 4. `approve_usdc.py` - USDC 授權 (一次性)

```python
#!/usr/bin/env python3
"""
授權 Polymarket CLOB 合約使用你嘅 USDC
用法: python approve_usdc.py [--amount 1000]
⚠️ 只係需要執行一次！
"""
import os
import sys
from pathlib import Path
from dotenv import load_dotenv
from web3 import Web3

load_dotenv()

def approve_usdc(amount_usdc=1000.0, auto_confirm=False):
    """授權 USDC"""
    w3 = Web3(Web3.HTTPProvider(os.getenv("POLYGON_RPC_URL")))

    private_key = os.getenv("POLYGON_PRIVATE_KEY")
    wallet_address = os.getenv("WALLET_ADDRESS")

    # USDC 合約
    USDC_ADDRESS = "0x2791Bca1f2de4661ED88A30C99A7a9449Aa84174"
    EXCHANGE_ADDRESS = "0x4bFb41d5B3570DeFd03C39a9A4D8dE6Bd8B8982E"

    usdc_abi = [
        {
            "constant": False,
            "inputs": [
                {"name": "_spender", "type": "address"},
                {"name": "_value", "type": "uint256"}
            ],
            "name": "approve",
            "outputs": [{"name": "", "type": "bool"}],
            "type": "function"
        }
    ]

    usdc = w3.eth.contract(address=Web3.to_checksum_address(USDC_ADDRESS), abi=usdc_abi)

    # Prepare transaction
    amount_wei = int(amount_usdc * 10**6)
    nonce = w3.eth.get_transaction_count(wallet_address)
    gas_price = w3.eth.gas_price

    tx = usdc.functions.approve(
        Web3.to_checksum_address(EXCHANGE_ADDRESS),
        amount_wei
    ).build_transaction({
        "from": wallet_address,
        "nonce": nonce,
        "gas": 100000,
        "gasPrice": gas_price
    })

    # Sign and send
    print(f"💰 Approving {amount_usdc} USDC for Polymarket...")
    account = w3.eth.account.from_key(private_key)
    signed_tx = account.sign_transaction(tx)
    tx_hash = w3.eth.send_raw_transaction(signed_tx.raw_transaction)

    print(f"✅ Transaction sent: {tx_hash.hex()}")
    print(f"🔗 View: https://polygonscan.com/tx/{tx_hash.hex()}")

    # Wait for confirmation
    receipt = w3.eth.wait_for_transaction_receipt(tx_hash)
    if receipt["status"] == 1:
        print("✅ Approval successful!")
    else:
        print("❌ Approval failed!")

    return receipt["status"] == 1

def main():
    """Main function"""
    import argparse

    parser = argparse.ArgumentParser(description="Approve USDC for Polymarket")
    parser.add_argument("--amount", type=float, default=1000.0, help="Amount of USDC to approve")
    parser.add_argument("--auto-confirm", action="store_true", help="Skip confirmation prompt")

    args = parser.parse_args()

    if not args.auto_confirm:
        confirm = input(f"Approve {args.amount} USDC? (yes/no): ").strip().lower()
        if confirm != "yes":
            print("❌ Cancelled")
            return False

    success = approve_usdc(args.amount, args.auto_confirm)
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()
```

## 🚀 快速開始

### Step 1: 檢查餘額

```bash
cd /Users/terivercheung/Documents/AI/pi-vs-claude-code/.claude/skills/pt/scripts
source venv/bin/activate
python check_balance.py
```

**需要**: Builder wallet 有 ≥ $2.175 USDC (5 shares minimum)

### Step 2: 執行交易

```bash
source venv/bin/activate
python execute_trade.py
```

**參數**:
- `market_id`: 市場 ID (默認: Maduro out by March 31, 2026?)
- `outcome`: "yes" 或 "no" (默認: "yes")
- `size`: 最少 5 shares (默認: 5.0)

### Step 3: 檢查 Positions

登入 https://polymarket.com/portfolio 查看你嘅 positions

## 🔑 關鍵概念

### 1. Builder Wallet vs Trading Wallet

```
Builder Wallet (0xf5459a...)
├── 有 USDC (資金)
├── 由 Polymarket custody
└── 用嚟 manual trading UI

Trading Wallet (0x92dF9A...)
├── 冇 USDC
├── 你 control (有 PK)
└── 用嚟程式交易簽名
```

**Trade 流程**:
1. 用 Trading wallet PK 簽名 → 證明係你
2. 指定 Builder wallet 作為 funder → 用佢嘅錢
3. Polymarket 驗證 signature → 批准用 Builder funds

### 2. API Keys 類型

| 類型 | 用途 | 點樣攞 | 可以用嚟 Trade? |
|------|------|--------|----------------|
| **Builder API** | Order attribution | Settings page | ❌ NO (401 error) |
| **Derived L2** | Trading API | `derive_api_key()` | ✅ YES (need funds) |

### 3. signature_type 模式

- `signature_type=0`: 標準模式 (default) - 用你自己嘅錢包 funds
- `signature_type=1`: Magic Link 模式 - 容許 external funder (Builder wallet)

```python
# Magic Link mode + external funder
client = ClobClient(
    host="https://clob.polymarket.com",
    key=private_key,
    chain_id=POLYGON,
    signature_type=1,        # 關鍵！
    funder=builder_wallet    # 用 Builder wallet 嘅錢
)
```

### 4. Minimum Trade Size

Polymarket 要求：
- **最少 5 shares** 每張單
- Cost = 5 × price (e.g., 5 × $0.435 = $2.175)

如果你餘額唔夠，會出錯：
```
Size (4.7) lower than the minimum: 5
```

## 🛠️ 除錯指南

### 問題 1: 401 Unauthorized

**原因**: 用錯 API keys 或者冇 set credentials

**解決**:
```python
creds = client.create_or_derive_api_creds()
client.set_api_creds(creds)  # 千祈唔好漏！
```

### 問題 2: 400 "not enough balance"

**原因**: Trading wallet 冇 USDC

**解決**: 用 `signature_type=1` + `funder` parameter

### 問題 3: 400 "Size lower than minimum"

**原因**: 少過 5 shares

**解決**: 確保 `size >= 5.0`

```python
if size < 5.0:
    print("最少要 5 shares!")
    size = 5.0
```

### 問題 4: "invalid signature"

**原因**: signature_type 錯誤或者 funder mismatch

**解決**:
```python
client = ClobClient(
    ...,
    signature_type=1,  # 用 1 唔係 0
    funder=builder_wallet  # 確保 set 咗
)
```

### 問題 5: "Execution Reverted" / "Allowance"

**原因**: 未 approve USDC

**解決**:
```bash
python approve_usdc.py --amount 1000
```

## 📈 進階用法

### 自動睇住價格 trade

```python
import time

def monitor_and_trade(target_price=0.40):
    """價格跌到 target 就自動買"""
    while True:
        market = client.get_market(MARKET_ID)
        current_price = float(market['tokens'][0]['price'])

        if current_price <= target_price:
            print(f"價格跌到 ${current_price}，執行交易！")
            execute_trade(size=5.0)
            break

        print(f"而家價格: ${current_price}，等待中...")
        time.sleep(60)  # 每分鐘 check 一次
```

### 多個市場監控

```python
MARKETS = {
    "maduro": "0x18d8c59309811ce5618ea941f9bde2a96afa5d876a69c42fba2da4bcc56d3c5e",
    "bitcoin": "0x...",
    "election": "0x..."
}

for name, market_id in MARKETS.items():
    market = client.get_market(market_id)
    price = float(market['tokens'][0]['price'])
    print(f"{name}: ${price}")
```

## 📚 參考資料

- [Polymarket CLOB Python Client](https://github.com/Polymarket/py-clob-client)
- [Polymarket Builder Docs](https://docs.polymarket.com)
- [CLOB API Reference](https://clob.polymarket.com)

## 🎓 學到嘅嘢

1. **Builder API keys ≠ Trading keys** - Builder keys 只做 attribution
2. **signature_type=1 係關鍵** - 容許 external funder
3. **Minimum 5 shares** - Polymarket 嘅限制
4. **Double wallet pattern** - Signer vs Funder 分離
5. **L1/L2 distinction** - Private key sign → Derive API keys

## 💬 支援

有問題？檢查：
1. Balance 夠唔夠 (≥ $2.175)
2. API keys 啱唔啱 format
3. signature_type 係咪 1
4. funder 有冇 set
5. Size 係咪 ≥ 5.0

---

**最後成功交易**: 2025-12-04
**Order ID**: 0xa78afb92008478320a17f6ff5cc79d35772a3204cf21ce5ee25383310b4b23e6
**Status**: ✅ live
