#!/usr/bin/env python3
"""
Approve USDC for Polymarket trading
"""
import os
import sys
from dotenv import load_dotenv
from web3 import Web3
from eth_account import Account

load_dotenv()

# Polymarket contracts
USDC_ADDRESS = "0x2791Bca1f2de4661ED88A30C99A7a9449Aa84174"  # Polygon USDC
EXCHANGE_ADDRESS = "0x4bFb41d5B3570DeFd03C39a9A4D8dE6Bd8B8982E"  # Polymarket Exchange

# ERC20 ABI
ERC20_ABI = [
    {
        "constant": False,
        "inputs": [
            {"name": "spender", "type": "address"},
            {"name": "amount", "type": "uint256"}
        ],
        "name": "approve",
        "outputs": [{"name": "", "type": "bool"}],
        "type": "function"
    },
    {
        "constant": True,
        "inputs": [{"name": "owner", "type": "address"}, {"name": "spender", "type": "address"}],
        "name": "allowance",
        "outputs": [{"name": "", "type": "uint256"}],
        "type": "function"
    }
]

def approve_usdc(amount_usdc: float = 1000.0, auto_confirm: bool = False):
    """
    Approve USDC for Polymarket trading

    Args:
        amount_usdc: Amount of USDC to approve (default: 1000)
        auto_confirm: Skip confirmation prompt
    """
    private_key = os.getenv("POLYGON_PRIVATE_KEY")
    wallet_address = os.getenv("WALLET_ADDRESS")
    rpc_url = os.getenv("POLYGON_RPC_URL", "https://polygon-rpc.com")

    if not private_key or not wallet_address:
        print("❌ Missing POLYGON_PRIVATE_KEY or WALLET_ADDRESS in .env")
        return False

    # Ensure private key has 0x prefix
    if not private_key.startswith('0x'):
        private_key = '0x' + private_key

    try:
        # Connect to Polygon
        w3 = Web3(Web3.HTTPProvider(rpc_url))

        if not w3.is_connected():
            print("❌ Cannot connect to Polygon RPC")
            return False

        print(f"✅ Connected to Polygon")
        print(f"📍 Wallet: {wallet_address}")
        print()

        # Create account from private key
        account = Account.from_key(private_key)

        # USDC contract
        usdc_contract = w3.eth.contract(
            address=Web3.to_checksum_address(USDC_ADDRESS),
            abi=ERC20_ABI
        )

        # Convert amount to USDC decimals (6 decimals)
        amount_wei = int(amount_usdc * 1_000_000)

        print(f"💰 準備 Approve USDC:")
        print(f"="*60)
        print(f"金額: {amount_usdc:,.2f} USDC")
        print(f"Exchange: {EXCHANGE_ADDRESS}")
        print(f"="*60)

        # Build transaction
        nonce = w3.eth.get_transaction_count(Web3.to_checksum_address(wallet_address))
        gas_price = w3.eth.gas_price

        print(f"\n🔨 建立交易...")
        print(f"   Nonce: {nonce}")
        print(f"   Gas Price: {w3.from_wei(gas_price, 'gwei'):.2f} Gwei")

        tx = usdc_contract.functions.approve(
            Web3.to_checksum_address(EXCHANGE_ADDRESS),
            amount_wei
        ).build_transaction({
            'from': Web3.to_checksum_address(wallet_address),
            'nonce': nonce,
            'gas': 100000,  # Standard ERC20 approve gas limit
            'gasPrice': gas_price
        })

        # Estimate gas
        try:
            estimated_gas = w3.eth.estimate_gas(tx)
            tx['gas'] = int(estimated_gas * 1.2)  # Add 20% buffer
            print(f"   Estimated Gas: {tx['gas']}")
        except Exception as e:
            print(f"⚠️  Gas estimation failed: {e}")
            print(f"   Using default gas limit: 100,000")

        # Calculate total cost
        gas_cost_wei = tx['gas'] * gas_price
        gas_cost_matic = w3.from_wei(gas_cost_wei, 'ether')

        print(f"\n💵 交易成本:")
        print(f"   Gas Fee: ~{gas_cost_matic:.4f} MATIC")
        print()

        # Ask for confirmation
        if not auto_confirm:
            confirm = input("確認執行 approve? (yes/no): ").strip().lower()
            if confirm != "yes":
                print("❌ 取消交易")
                return False
        else:
            print("✅ Auto-confirm enabled, proceeding...")

        # Sign transaction
        print(f"\n✍️  簽署交易...")
        signed_tx = account.sign_transaction(tx)

        # Send transaction
        print(f"📤 發送交易...")
        tx_hash = w3.eth.send_raw_transaction(signed_tx.raw_transaction)

        print(f"✅ 交易已發送！")
        print(f"   Tx Hash: {tx_hash.hex()}")
        print(f"   Explorer: https://polygonscan.com/tx/{tx_hash.hex()}")

        # Wait for confirmation
        print(f"\n⏳ 等待確認...")
        receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=120)

        if receipt['status'] == 1:
            print(f"✅ 交易成功！")
            print(f"   Block: {receipt['blockNumber']}")
            print(f"   Gas Used: {receipt['gasUsed']}")

            # Verify allowance
            allowance = usdc_contract.functions.allowance(
                Web3.to_checksum_address(wallet_address),
                Web3.to_checksum_address(EXCHANGE_ADDRESS)
            ).call()

            allowance_usdc = allowance / 1_000_000

            print(f"\n💰 新的 Allowance: {allowance_usdc:,.2f} USDC")
            print(f"✅ 現在可以在 Polymarket 交易了！")

            return True
        else:
            print(f"❌ 交易失敗")
            return False

    except Exception as e:
        print(f"❌ 錯誤: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Approve USDC for Polymarket")
    parser.add_argument(
        "--amount",
        type=float,
        default=1000.0,
        help="Amount of USDC to approve (default: 1000)"
    )
    parser.add_argument(
        "--auto-confirm",
        action="store_true",
        help="Skip confirmation prompt"
    )

    args = parser.parse_args()

    approve_usdc(args.amount, args.auto_confirm)
