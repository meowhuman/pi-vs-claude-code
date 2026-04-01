#!/usr/bin/env python3
"""
Simple test - sign order with Phantom wallet, ignore Builder profile address
"""
import os
import sys
from pathlib import Path
from dotenv import load_dotenv
from py_clob_client.client import ClobClient
from py_clob_client.clob_types import OrderArgs, ApiCreds
from py_clob_client.constants import POLYGON

# Load .env
env_path = Path(__file__).parent.parent / ".env"
load_dotenv(env_path)

def main():
    # Get credentials
    private_key = os.getenv("POLYGON_PRIVATE_KEY")
    api_key = os.getenv("POLY_BUILDER_API_KEY")
    api_secret = os.getenv("POLY_BUILDER_SECRET")
    api_passphrase = os.getenv("POLY_BUILDER_PASSPHRASE")

    if not all([private_key, api_key, api_secret, api_passphrase]):
        print("❌ Missing credentials")
        return False

    print("🔐 Testing with L2 credentials ONLY (no Builder config)...")

    try:
        # L2 API Credentials
        api_creds = ApiCreds(
            api_key=api_key,
            api_secret=api_secret,
            api_passphrase=api_passphrase
        )

        # Initialize WITHOUT Builder config
        client = ClobClient(
            host="https://clob.polymarket.com",
            key=private_key,
            chain_id=POLYGON,
            creds=api_creds
        )
        print("✅ Client initialized")

        # Test get balance
        print("\n💰 Testing API access...")
        balance = client.get_balance_allowance()
        print(f"✅ Balance: ${balance}")

        return True

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
