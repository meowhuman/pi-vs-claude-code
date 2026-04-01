#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = [
#     "web3>=6.0.0",
#     "python-dotenv>=1.0.0",
# ]
# ///

"""
測試 Polymarket 錢包連接和餘額檢查
"""

import os
import sys
from web3 import Web3
from dotenv import load_dotenv

def test_connection():
    """測試錢包連接"""
    try:
        print("🔧 測試 Polymarket Trader Skill")
        print("=" * 50)

        # Load environment variables
        load_dotenv()

        # 讀取配置
        private_key = os.getenv("POLYGON_PRIVATE_KEY")
        wallet_address = os.getenv("WALLET_ADDRESS")
        rpc_url = os.getenv("POLYGON_RPC_URL", "https://polygon-rpc.com")

        print(f"📍 錢包地址: {wallet_address}")
        print(f"🔗 RPC URL: {rpc_url}")

        # 檢查私鑰格式
        if not private_key:
            print("❌ 錯誤: 找不到 POLYGON_PRIVATE_KEY")
            print("請在 .env 文件中設定你的私鑰")
            return False

        if len(private_key) != 64:
            print(f"❌ 錯誤: 私鑰長度不正確 ({len(private_key)} 字符)")
            print("私鑰應該是 64 字符的 hex string (不含 0x)")
            return False

        # 連接到 Polygon
        print("\n🔗 連接到 Polygon 網絡...")
        w3 = Web3(Web3.HTTPProvider(rpc_url))

        if not w3.is_connected():
            print("❌ 無法連接到 Polygon RPC")
            return False

        print("✅ 成功連接到 Polygon")

        # 驗證錢包地址
        account = w3.eth.account.from_key(private_key)
        derived_address = account.address

        if wallet_address != derived_address:
            print(f"❌ 錯誤: 錢包地址不匹配")
            print(f"   設定地址: {wallet_address}")
            print(f"   從私鑰導出: {derived_address}")
            return False

        print(f"✅ 錢包地址驗證成功")

        # 檢查 MATIC 餘額
        print(f"\n💰 檢查錢包餘額...")
        matic_balance_wei = w3.eth.get_balance(derived_address)
        matic_balance = w3.from_wei(matic_balance_wei, "ether")

        print(f"💎 MATIC 餘額: {matic_balance:.4f} MATIC")

        if matic_balance < 0.01:
            print("⚠️  警告: MATIC 餘額過低，可能不足以支付 gas fee")
        else:
            print("✅ MATIC 餘額充足")

        # USDC Contract on Polygon
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

        # 檢查 USDC 餘額
        usdc_contract = w3.eth.contract(
            address=Web3.to_checksum_address(USDC_ADDRESS), abi=USDC_ABI
        )

        usdc_balance_raw = usdc_contract.functions.balanceOf(
            Web3.to_checksum_address(derived_address)
        ).call()
        usdc_decimals = usdc_contract.functions.decimals().call()
        usdc_balance = usdc_balance_raw / (10**usdc_decimals)

        print(f"💵 USDC 餘額: {usdc_balance:.2f} USDC")

        if usdc_balance == 0:
            print("⚠️  警告: USDC 餘額為 0，無法執行交易")
            return False
        elif usdc_balance < 0.5:
            print("⚠️  提示: USDC 餘額較低，建議充值")
        else:
            print("✅ USDC 餘額充足，可以開始交易")

        # 檢查交易限額
        max_auto = float(os.getenv("MAX_AUTO_AMOUNT", "1.0"))
        print(f"\n⚙️  自動交易限額: {max_auto} USDC")

        if usdc_balance >= 0.1:
            print(f"✅ 可以進行 0.1 USDC 測試交易")
            if usdc_balance >= max_auto:
                print(f"✅ 可以進行 {max_auto} USDC 以下的自動交易")
            else:
                print(f"⚠️  餘額少於自動交易限額，需要手動確認")

        print("\n" + "=" * 50)
        print("🎉 錢包測試完成！可以開始使用 Polymarket Trader Skill")
        return True

    except Exception as e:
        print(f"❌ 錯誤: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = test_connection()
    sys.exit(0 if success else 1)