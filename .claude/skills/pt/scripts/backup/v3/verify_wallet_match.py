#!/usr/bin/env python3
"""
Verify that the private key matches the wallet address
"""
import os
from dotenv import load_dotenv
from web3 import Web3
from eth_account import Account

load_dotenv()

def verify_wallet():
    """Verify private key matches wallet address"""

    private_key = os.getenv("POLYGON_PRIVATE_KEY")
    expected_address = os.getenv("WALLET_ADDRESS")

    if not private_key:
        print("❌ POLYGON_PRIVATE_KEY not found in .env")
        return False

    if not expected_address:
        print("❌ WALLET_ADDRESS not found in .env")
        return False

    # Ensure private key has 0x prefix
    if not private_key.startswith('0x'):
        private_key = '0x' + private_key

    try:
        # Derive address from private key
        account = Account.from_key(private_key)
        derived_address = account.address

        print(f"🔐 驗證錢包配對:")
        print(f"="*60)
        print(f"預期地址 (.env): {expected_address}")
        print(f"私鑰推導地址:     {derived_address}")
        print(f"="*60)

        if derived_address.lower() == expected_address.lower():
            print("✅ 匹配成功！私鑰和錢包地址配對正確")
            return True
        else:
            print("❌ 錯誤：私鑰和錢包地址不匹配！")
            print("\n⚠️  請檢查:")
            print("   1. POLYGON_PRIVATE_KEY 是否正確")
            print("   2. WALLET_ADDRESS 是否是你在 Polymarket 使用的地址")
            return False

    except Exception as e:
        print(f"❌ 錯誤: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    verify_wallet()
