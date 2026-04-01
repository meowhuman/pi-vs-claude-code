#!/usr/bin/env python3
"""
Check USDC allowances for Polymarket trading
"""
import os
import sys
from dotenv import load_dotenv
from web3 import Web3

load_dotenv()

# Polymarket contracts
USDC_ADDRESS = "0x2791Bca1f2de4661ED88A30C99A7a9449Aa84174"  # Polygon USDC
EXCHANGE_ADDRESS = "0x4bFb41d5B3570DeFd03C39a9A4D8dE6Bd8B8982E"  # Polymarket Exchange

# ERC20 ABI (approve, allowance functions)
ERC20_ABI = [
    {
        "constant": True,
        "inputs": [{"name": "owner", "type": "address"}, {"name": "spender", "type": "address"}],
        "name": "allowance",
        "outputs": [{"name": "", "type": "uint256"}],
        "type": "function"
    }
]

def check_allowances():
    """Check USDC allowances"""

    private_key = os.getenv("POLYGON_PRIVATE_KEY")
    wallet_address = os.getenv("WALLET_ADDRESS")
    rpc_url = os.getenv("POLYGON_RPC_URL", "https://polygon-rpc.com")

    if not wallet_address:
        print("❌ WALLET_ADDRESS not found in .env")
        return False

    try:
        # Connect to Polygon
        w3 = Web3(Web3.HTTPProvider(rpc_url))

        if not w3.is_connected():
            print("❌ Cannot connect to Polygon RPC")
            return False

        print(f"✅ Connected to Polygon")
        print(f"📍 Wallet: {wallet_address}")
        print()

        # Check USDC contract
        usdc_contract = w3.eth.contract(
            address=Web3.to_checksum_address(USDC_ADDRESS),
            abi=ERC20_ABI
        )

        # Check allowance
        allowance = usdc_contract.functions.allowance(
            Web3.to_checksum_address(wallet_address),
            Web3.to_checksum_address(EXCHANGE_ADDRESS)
        ).call()

        # USDC has 6 decimals
        allowance_usdc = allowance / 1_000_000

        print(f"💰 USDC Allowance 狀態:")
        print(f"="*60)
        print(f"Exchange Contract: {EXCHANGE_ADDRESS}")
        print(f"Current Allowance: {allowance_usdc:,.2f} USDC")
        print(f"="*60)

        if allowance_usdc > 0:
            print(f"✅ USDC 已授權！可以交易")
            if allowance_usdc < 100:
                print(f"⚠️  授權額度較低，建議增加")
        else:
            print(f"❌ USDC 未授權！需要先 approve")
            print()
            print(f"💡 解決方法:")
            print(f"   1. 在 Polymarket 網站完成第一筆交易")
            print(f"   2. 這會自動 approve USDC")
            print(f"   3. 或使用 MetaMask 手動 approve")

        return True

    except Exception as e:
        print(f"❌ 錯誤: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    check_allowances()
