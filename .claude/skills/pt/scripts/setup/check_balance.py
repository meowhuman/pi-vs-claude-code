#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = [
#     "web3>=6.0.0",
#     "python-dotenv>=1.0.0",
# ]
# ///

"""
檢查 Polygon 兩個錢包的 USDC 和 MATIC 餘額
- Builder Wallet (推薦用於交易)
- Control Wallet (備用)
"""

import os
import sys
from web3 import Web3
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# USDC Contract on Polygon
USDC_ADDRESS = "0x2791Bca1f2de4661ED88A30C99A7a9449Aa84174"  # USDC on Polygon
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


def check_wallet_balance(w3, usdc_contract, wallet_address, wallet_name):
    """檢查單個錢包的餘額"""
    try:
        # 檢查 MATIC 餘額
        matic_balance_wei = w3.eth.get_balance(wallet_address)
        matic_balance = w3.from_wei(matic_balance_wei, "ether")

        # 檢查 USDC 餘額
        usdc_balance_raw = usdc_contract.functions.balanceOf(
            Web3.to_checksum_address(wallet_address)
        ).call()
        usdc_decimals = usdc_contract.functions.decimals().call()
        usdc_balance = usdc_balance_raw / (10**usdc_decimals)

        # 打印結果
        print(f"\n🏢 {wallet_name}")
        print(f"   地址: {wallet_address}")
        print(f"   💎 MATIC: {matic_balance:.4f} MATIC", end="")
        if matic_balance < 0.01:
            print(" ⚠️")
        else:
            print(" ✓")

        print(f"   💵 USDC: {usdc_balance:.2f} USDC", end="")
        if usdc_balance == 0:
            print(" ⚠️")
        elif usdc_balance < 1:
            print(" ⚠️ (較低)")
        else:
            print(" ✓")

        return matic_balance, usdc_balance

    except Exception as e:
        print(f"\n❌ {wallet_name} 檢查失敗: {str(e)}")
        return None, None


def check_balance():
    """檢查兩個錢包的餘額"""
    try:
        # 讀取配置
        rpc_url = os.getenv("POLYGON_RPC_URL", "https://polygon-rpc.com")
        builder_wallet = os.getenv("BUILDER_WALLET_ADDRESS")
        control_wallet = os.getenv("CONTROL_WALLET_ADDRESS")

        if not builder_wallet:
            print("❌ 錯誤: 找不到 BUILDER_WALLET_ADDRESS 環境變數")
            print("請在 .env 文件中設定 Builder 錢包地址")
            return False

        # 連接到 Polygon
        w3 = Web3(Web3.HTTPProvider(rpc_url))

        if not w3.is_connected():
            print(f"❌ 無法連接到 Polygon RPC: {rpc_url}")
            return False

        print(f"✅ 已連接到 Polygon 網絡")
        print("=" * 50)

        # 初始化 USDC 合約
        usdc_contract = w3.eth.contract(
            address=Web3.to_checksum_address(USDC_ADDRESS), abi=USDC_ABI
        )

        # 檢查 Builder Wallet
        builder_matic, builder_usdc = check_wallet_balance(
            w3, usdc_contract, builder_wallet, "Builder Wallet (推薦)"
        )

        # 檢查 Control Wallet
        if control_wallet:
            control_matic, control_usdc = check_wallet_balance(
                w3, usdc_contract, control_wallet, "Control Wallet (備用)"
            )
        else:
            print("\n🏢 Control Wallet (備用)")
            print("   ⚠️  未在 .env 中設置")
            control_matic, control_usdc = None, None

        # 總結
        print("\n" + "=" * 50)
        print("📊 餘額總結")
        if builder_matic is not None and control_matic is not None:
            total_matic = builder_matic + control_matic
            total_usdc = builder_usdc + control_usdc
            print(f"   總 MATIC: {total_matic:.4f} MATIC")
            print(f"   總 USDC: {total_usdc:.2f} USDC")
        elif builder_matic is not None:
            print(f"   總 MATIC: {builder_matic:.4f} MATIC")
            print(f"   總 USDC: {builder_usdc:.2f} USDC")

        print("\n✅ 餘額檢查完成!")
        return True

    except Exception as e:
        print(f"❌ 錯誤: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = check_balance()
    sys.exit(0 if success else 1)
