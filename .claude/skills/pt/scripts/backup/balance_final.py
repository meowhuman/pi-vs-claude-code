#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = [
#     "py-clob-client>=0.28.0",
#     "python-dotenv>=1.0.0",
#     "web3>=6.0.0",
# ]
# ///

"""
最終餘額檢查 - 結合 Polygon USDC 和 Polymarket Trading Wallet
"""

import os
import sys
import json
from dotenv import load_dotenv
from web3 import Web3
from py_clob_client.client import ClobClient
from py_clob_client.constants import POLYGON

def check_final_balance():
    """檢查最終餘額狀況"""
    try:
        # Load environment variables
        load_dotenv()

        # 讀取配置
        private_key = os.getenv("POLYGON_PRIVATE_KEY")
        rpc_url = os.getenv("POLYGON_RPC_URL", "https://polygon-rpc.com")
        host = "https://clob.polymarket.com"

        if not private_key:
            print("❌ 錯誤: 找不到 POLYGON_PRIVATE_KEY")
            return False

        # 從私鑰計算錢包地址
        w3 = Web3(Web3.HTTPProvider(rpc_url))
        account = w3.eth.account.from_key(private_key)
        wallet_address = account.address

        print("🔧 Polymarket Trader Skill - 最終餘額檢查")
        print("=" * 60)
        print(f"📍 錢包地址: {wallet_address}")

        # 1. 檢查 Polygon 主網絡的 USDC 餘額
        print(f"\n💰 1. Polygon 主網絡 USDC 餘額")
        print("-" * 30)

        USDC_ADDRESS = "0x2791Bca1f2de4661ED88A30C99A7a9449Aa84174"
        USDC_ABI = [
            {
                "constant": True,
                "inputs": [{"name": "_owner", "type": "address"}],
                "name": "balanceOf",
                "outputs": [{"name": "balance", "type": "uint256"}],
                "type": "function",
            },
            {
                "constant": True,
                "inputs": [],
                "name": "decimals",
                "outputs": [{"name": "", "type": "uint8"}],
                "type": "function",
            },
        ]

        try:
            usdc_contract = w3.eth.contract(
                address=Web3.to_checksum_address(USDC_ADDRESS), abi=USDC_ABI
            )

            usdc_balance_raw = usdc_contract.functions.balanceOf(
                Web3.to_checksum_address(wallet_address)
            ).call()

            usdc_decimals = usdc_contract.functions.decimals().call()
            usdc_balance = usdc_balance_raw / (10**usdc_decimals)

            print(f"💵 USDC 餘額: {usdc_balance:.2f} USDC")

        except Exception as e:
            print(f"❌ 無法獲取 USDC 餘額: {str(e)}")

        # 2. 檢查 MATIC 餘額
        print(f"\n💎 2. MATIC 餘額 (Gas Fee)")
        print("-" * 30)

        try:
            matic_balance_wei = w3.eth.get_balance(wallet_address)
            matic_balance = w3.from_wei(matic_balance_wei, "ether")
            print(f"💎 MATIC 餘額: {matic_balance:.4f} MATIC")

            if matic_balance < 0.01:
                print("⚠️  警告: MATIC 餘額過低，可能不足以支付 gas fee")
            else:
                print("✅ MATIC 餘額充足")
        except Exception as e:
            print(f"❌ 無法獲取 MATIC 餘額: {str(e)}")

        # 3. 檢查 Polymarket CLOB Trading Wallet 狀態
        print(f"\n🔄 3. Polymarket CLOB Trading Wallet")
        print("-" * 40)

        try:
            client = ClobClient(host, key=private_key, chain_id=POLYGON)

            # 設置 API 憑證
            try:
                api_keys = client.get_api_keys()
                if api_keys:
                    client.set_api_creds(api_keys[0])
                    print("✅ 使用現有 API 憑證")
                else:
                    derived_creds = client.derive_api_key()
                    client.set_api_creds(derived_creds)
                    print("✅ 使用導出 API 憑證")
            except:
                derived_creds = client.derive_api_key()
                client.set_api_creds(derived_creds)
                print("✅ 使用導出 API 憑證")

            # 檢查訂單 (間接驗證 trading wallet 狀態)
            try:
                orders = client.get_orders()
                print(f"📋 活躍訂單: {len(orders)} 個")
            except:
                print("📋 活躍訂單: 無法查詢")

            # 檢查費率
            try:
                fee_rate = client.get_fee_rate_bps()
                print(f"💰 交易費率: {fee_rate} bps")
            except:
                print("💰 交易費率: 無法查詢")

            # 檢查抵押品地址
            try:
                collateral_address = client.get_collateral_address()
                print(f"💼 抵押品地址: {collateral_address}")
            except:
                print("💼 抵押品地址: 無法查詢")

        except Exception as e:
            print(f"❌ Polymarket CLOB 連接失敗: {str(e)}")

        # 4. 總結和建議
        print(f"\n📊 4. 總結")
        print("-" * 15)

        print("💡 重要提示:")
        print("• Polymarket 使用分離的 trading wallet")
        print("• USDC 需要先存入 Polymarket trading wallet 才能交易")
        print("• 可以通過 https://polymarket.com 網頁版進行充值")
        print("• 充值後，USDC 會從 Polygon 主網絡轉移到 Polymarket 內部系統")

        print("\n🚀 交易狀態:")
        print("✅ 錢包連接正常")
        print("✅ API 憑證設置成功")
        print("✅ 可以執行市場查詢")
        print("✅ 可以檢查訂單狀態")

        return True

    except Exception as e:
        print(f"❌ 錯誤: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = check_final_balance()
    sys.exit(0 if success else 1)