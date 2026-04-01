#!/usr/bin/env python3
"""
Test trade using official py-clob-client with Builder API
"""
import os
import sys
from pathlib import Path
from dotenv import load_dotenv
from py_clob_client.client import ClobClient, BuilderConfig
from py_clob_client.clob_types import OrderArgs, OrderType, ApiCreds
from py_clob_client.constants import POLYGON
from py_builder_signing_sdk.config import BuilderApiKeyCreds

# Load .env from parent directory
env_path = Path(__file__).parent.parent / ".env"
load_dotenv(env_path)

def main():
    # Get credentials from env
    owner_key = os.getenv("OWNER_PRIVATE_KEY")    # Signer private key (for approval)
    proxy_key = os.getenv("PROXY_PRIVATE_KEY")    # Proxy private key (for trading)
    wallet_address = os.getenv("OWNER_ADDRESS")   # Phantom Wallet (Signer)
    poly_address = os.getenv("PROXY_ADDRESS")     # Proxy Wallet (Target)

    # Derived API credentials (for L2 authentication) - USE PROXY CREDENTIALS
    api_key = os.getenv("PROXY_MARKET_API_KEY")
    api_secret = os.getenv("PROXY_MARKET_SECRET")
    api_passphrase = os.getenv("PROXY_MARKET_PASSPHRASE")

    # Builder API credentials (for proxy signature handling)
    builder_api_key = os.getenv("POLY_BUILDER_API_KEY")
    builder_secret = os.getenv("POLY_BUILDER_SECRET")
    builder_passphrase = os.getenv("POLY_BUILDER_PASSPHRASE")

    if not all([proxy_key, api_key, api_secret, api_passphrase]):
        print("❌ Missing PROXY_PRIVATE_KEY or POLYMARKET_API_KEY credentials")
        print(f"   PROXY_PRIVATE_KEY: {'✅' if proxy_key else '❌'}")
        print(f"   POLYMARKET_API_KEY: {'✅' if api_key else '❌'}")
        return False

    print("🔐 Initializing Polymarket CLOB Client with BuilderConfig...")
    print(f"   Signer (Phantom): {wallet_address}")
    print(f"   Target (Proxy):   {poly_address}")
    print(f"   Using Proxy PK: ✅")
    print(f"   API Credentials: {api_key[:8]}... (derived)")
    print(f"   Builder Config: {builder_api_key[:8] if builder_api_key else 'NONE'}... (builder)")

    # Initialize client with Builder API
    try:
        # Create L2 API Credentials (derived for trading)
        api_creds = ApiCreds(
            api_key=api_key,
            api_secret=api_secret,
            api_passphrase=api_passphrase
        )

        # Create Builder credentials (from Builder Profile, for signature)
        if builder_api_key and builder_secret and builder_passphrase:
            builder_creds = BuilderApiKeyCreds(
                key=builder_api_key,
                secret=builder_secret,
                passphrase=builder_passphrase
            )

            # Create Builder config for proxy wallet handling
            builder_config = BuilderConfig(
                local_builder_creds=builder_creds
            )
            print("✅ BuilderConfig created with Builder API credentials")
        else:
            builder_config = None
            print("⚠️  BuilderConfig disabled - missing Builder API credentials")

        # Initialize CLOB client with both L2 and Builder credentials
        # key = Proxy private key (because we're trading from proxy wallet)
        # funder = Proxy wallet address (target account)
        client = ClobClient(
            host="https://clob.polymarket.com",
            key=proxy_key,                    # 🔑 關鍵：使用 Proxy wallet 的私鑰
            chain_id=POLYGON,
            creds=api_creds,
            builder_config=builder_config,    # Handle proxy signatures
            funder=poly_address               # ⚠️ 關鍵：使用 Proxy wallet 作為目標帳戶
        )
        print("✅ Client initialized successfully!")
    except Exception as e:
        print(f"❌ Failed to initialize client: {e}")
        import traceback
        traceback.print_exc()
        return False

    # Test market
    market_id = "0x18d8c59309811ce5618ea941f9bde2a96afa5d876a69c42fba2da4bcc56d3c5e"

    try:
        # Get market info
        print("\n📊 Fetching market data...")
        market = client.get_market(market_id)
        print(f"✅ Market: {market['question']}")
        print(f"   Status: {'✅ Active' if market.get('active') else '❌ Closed'}")

        # Get token ID for "Yes"
        token_id = None
        for token in market.get('tokens', []):
            if token.get('outcome', '').lower() == 'yes':
                token_id = token.get('token_id')
                price = float(token.get('price', 0.5))
                print(f"   Yes Token: {token_id}")
                print(f"   Current Price: ${price}")
                break

        if not token_id:
            print("❌ Yes token not found")
            return False

        # Prepare order
        amount = 1.0  # $1.00 USDC (minimum required)
        execution_price = min(price * 1.05, 0.99)  # 5% slippage
        size = amount / execution_price

        print(f"\n💰 Creating order...")
        print(f"   Token ID: {token_id[:20]}...")
        print(f"   Price: ${execution_price:.4f}")
        print(f"   Size: {size:.2f} shares")
        print(f"   Total: ${amount} USDC")

        # Create order using official client
        order_args = OrderArgs(
            token_id=token_id,
            price=execution_price,
            size=size,
            side="BUY",
            fee_rate_bps=0
        )

        print("\n🚀 Submitting order via Builder API...")
        signed_order = client.create_and_post_order(order_args)

        print(f"\n🎉 ORDER SUBMITTED SUCCESSFULLY!")
        print(f"   Order ID: {signed_order.get('orderID', 'N/A')}")
        print(f"   Status: {signed_order.get('status', 'Unknown')}")

        return True

    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
