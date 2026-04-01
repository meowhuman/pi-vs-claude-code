#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = [
#     "requests>=2.31.0",
#     "python-dotenv>=1.0.0",
#     "web3>=6.0.0",
# ]
# ///

"""
查看 Polymarket 持倉
"""

import os
import sys
import requests
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Polymarket Data API
DATA_API = "https://data-api.polymarket.com"


def get_market_details(market_id):
    """獲取市場詳細信息

    Args:
        market_id: 市場 ID

    Returns:
        dict: 市場詳細信息
    """
    try:
        market_url = f"{DATA_API}/markets/{market_id}"
        response = requests.get(market_url, timeout=10)

        if response.status_code == 200:
            return response.json()
        return None
    except Exception as e:
        print(f"   ⚠️  無法獲取市場詳情: {str(e)}")
        return None


def get_positions(wallet_address=None, wallet_name="持倉", verbose=False):
    """查看當前持倉

    Args:
        wallet_address: 要查詢的錢包地址 (預設使用 WALLET_ADDRESS)
        wallet_name: 錢包名稱 (用於顯示)
        verbose: 是否顯示詳細信息
    """
    try:
        if not wallet_address:
            wallet_address = os.getenv("WALLET_ADDRESS")

        if not wallet_address:
            print("❌ 錯誤: 找不到 WALLET_ADDRESS 環境變數")
            return False

        print(f"📊 查詢{wallet_name}: {wallet_address}\n")

        # 查詢持倉
        positions_url = f"{DATA_API}/positions"

        response = requests.get(
            positions_url, params={"user": wallet_address}, timeout=10
        )

        if response.status_code != 200:
            print(f"❌ API 請求失敗: {response.status_code}")
            print(f"   Response: {response.text[:200]}")
            return False

        positions = response.json()

        if verbose:
            print(f"📋 API 原始數據 ({len(positions)} 筆):")
            import json
            print(json.dumps(positions[:1], indent=2, ensure_ascii=False))
            print()

        if not positions or len(positions) == 0:
            print("📭 目前沒有持倉")
            return True

        # 過濾掉空持倉
        valid_positions = [p for p in positions if float(p.get("size", p.get("shares", 0))) > 0]

        if valid_positions:
            print(f"找到 {len(valid_positions)} 個有效持倉 (API 返回 {len(positions)} 筆):\n")
        else:
            print(f"找到 0 個有效持倉 (API 返回 {len(positions)} 筆)")
            return True

        print("=" * 100)

        total_value = 0
        total_cost = 0
        positions_with_data = 0

        for idx, pos in enumerate(valid_positions, 1):
            # 嘗試從不同的字段獲取數據 - 支持多種 API 格式

            # 格式 1: market 物件
            market_info = pos.get("market", {})
            if isinstance(market_info, dict):
                market_name = market_info.get("question", None)
                market_id = market_info.get("id", None)
            else:
                market_name = None
                market_id = None

            # 格式 2: 直接字段 (Builder wallet API)
            if not market_name:
                market_name = pos.get("title", None)
            if not market_id:
                market_id = pos.get("conditionId", None)

            # 預設值
            if not market_name:
                market_name = "N/A"
            if not market_id:
                market_id = "N/A"

            # 獲取方向和數量
            side = pos.get("outcome", pos.get("side", "N/A"))  # Yes/No 或 outcome
            shares = float(pos.get("size", pos.get("shares", 0)))
            avg_price = float(pos.get("avgPrice", pos.get("avg_price", 0)))
            current_price = float(pos.get("curPrice", pos.get("current_price", 0)))

            # 如果缺少市場名稱，嘗試從市場 ID 獲取詳細信息
            if market_name == "N/A" and market_id != "N/A" and market_id != "0x...":
                market_details = get_market_details(market_id)
                if market_details:
                    market_name = market_details.get("question", "N/A")

            cost = shares * avg_price
            current_value = shares * current_price
            pnl = current_value - cost
            pnl_percent = (pnl / cost * 100) if cost > 0 else 0

            # 計算統計數據
            positions_with_data += 1
            total_cost += cost
            total_value += current_value

            print(f"\n{idx}. {market_name} - {side}")
            if market_id != "N/A" and not market_id.startswith("0x"):
                print(f"   📌 市場 ID: {market_id}")

            print(f"   持有: {shares:.2f} shares")
            print(f"   成本: {cost:.2f} USDC (平均 ${avg_price:.2f}/share)")
            print(f"   當前價值: {current_value:.2f} USDC (@ ${current_price:.2f}/share)")

            pnl_symbol = "📈" if pnl >= 0 else "📉"
            pnl_sign = "+" if pnl >= 0 else ""
            print(
                f"   盈虧: {pnl_symbol} {pnl_sign}{pnl:.2f} USDC ({pnl_sign}{pnl_percent:.1f}%)"
            )

        print("\n" + "=" * 100)

        total_pnl = total_value - total_cost
        total_pnl_percent = (total_pnl / total_cost * 100) if total_cost > 0 else 0

        print(f"\n📊 總持倉統計:")
        print(f"   有效持倉: {positions_with_data} 個")
        print(f"   總成本: {total_cost:.2f} USDC")
        print(f"   總價值: {total_value:.2f} USDC")

        pnl_symbol = "📈" if total_pnl >= 0 else "📉"
        pnl_sign = "+" if total_pnl >= 0 else ""
        print(
            f"   總盈虧: {pnl_symbol} {pnl_sign}{total_pnl:.2f} USDC ({pnl_sign}{total_pnl_percent:.1f}%)"
        )

        return True

    except requests.exceptions.RequestException as e:
        print(f"❌ 網絡請求錯誤: {str(e)}")
        return False
    except Exception as e:
        print(f"❌ 錯誤: {str(e)}")
        import traceback

        traceback.print_exc()
        return False


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="查詢 Polymarket 倉位")
    parser.add_argument(
        "--verbose", "-v", action="store_true", help="顯示詳細 API 數據"
    )
    parser.add_argument(
        "--wallet", "-w", help="查詢特定錢包地址", default=None
    )
    args = parser.parse_args()

    # Control wallet (從 .env 讀取)
    control_wallet = os.getenv("WALLET_ADDRESS")
    builder_wallet = "0xf5459aeE5E781371Fe4D32c6FD74D6154F52cA3B"

    print("=" * 100)
    print("🔍 Polymarket 倉位查詢 (Control + Builder Wallet)")
    print("=" * 100)
    print()

    # 如果指定了特定錢包，只查詢該錢包
    if args.wallet:
        print(f"🔍 查詢指定錢包: {args.wallet}")
        print("-" * 100)
        success = get_positions(wallet_address=args.wallet, wallet_name="指定錢包", verbose=args.verbose)
        sys.exit(0 if success else 1)

    # 查詢 Control wallet
    print("👤 Control Wallet (你的簽名錢包)")
    print("-" * 100)
    success1 = get_positions(
        wallet_address=control_wallet,
        wallet_name="Control Wallet 持倉",
        verbose=args.verbose,
    )

    print()
    print()

    # 查詢 Builder wallet
    print("🎯 Builder Wallet (Polymarket Custody)")
    print("-" * 100)
    success2 = get_positions(
        wallet_address=builder_wallet,
        wallet_name="Builder Wallet 持倉",
        verbose=args.verbose,
    )

    print()
    print("=" * 100)

    success = success1 and success2
    sys.exit(0 if success else 1)
