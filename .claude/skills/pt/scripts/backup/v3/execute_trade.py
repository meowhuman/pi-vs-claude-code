#!/usr/bin/env python3
import os
import sys
import argparse
from dotenv import load_dotenv
from py_clob_client.client import ClobClient
from py_clob_client.clob_types import OrderArgs, ApiCreds
from py_clob_client.constants import POLYGON

# Load environment variables
load_dotenv()

def execute_trade(market_id: str, side: str, amount: float, auto_confirm: bool = False, trade_side: str = "BUY"):
    """
    Execute a trade on Polymarket using py-clob-client.

    Args:
        market_id: The condition_id of the market
        side: "Yes" or "No" (or other outcome name) - the outcome to trade
        amount: Amount in USDC to spend (for BUY) or to receive (for SELL)
        auto_confirm: Skip confirmation prompt
        trade_side: "BUY" or "SELL" - the trade direction
    """
    # 1. Setup Client
    host = "https://clob.polymarket.com"

    # Signing wallet (用於簽名)
    signing_key = os.getenv("POLYGON_PRIVATE_KEY")

    # Builder wallet (提供資金)
    builder_wallet = os.getenv("BUILDER_WALLET_ADDRESS")

    if not signing_key:
        print("❌ Error: POLYGON_PRIVATE_KEY not found in .env")
        return False

    if not builder_wallet:
        print("❌ Error: BUILDER_WALLET_ADDRESS not found in .env")
        return False

    try:
        # Initialize client with proper configuration
        print("🔐 Initializing Polymarket client...")
        print(f"   Signing Wallet: {os.getenv('WALLET_ADDRESS')}")
        print(f"   Builder Wallet (Funder): {builder_wallet}")

        # Step 1: Create client with Magic Link mode (signature_type=1)
        client = ClobClient(
            host,
            key=signing_key,
            chain_id=POLYGON,
            signature_type=1,  # Magic Link mode - 容許 external funder
            funder=builder_wallet  # Builder wallet 提供資金
        )

        # Step 2: Derive L2 Trading API credentials (CRITICAL - fixes 401 error)
        print("🔑 Deriving L2 Trading API credentials from private key...")
        derived_creds = client.create_or_derive_api_creds()
        client.set_api_creds(derived_creds)
        print("✅ L2 Trading API credentials set")

    except Exception as e:
        print(f"❌ Error initializing client: {e}")
        import traceback
        traceback.print_exc()
        return False

    # 2. Get Market Details
    print(f"🔍 Fetching market details for {market_id}...")
    try:
        market = client.get_market(market_id)
    except Exception as e:
        print(f"❌ Error fetching market: {e}")
        return False

    if not market:
        print("❌ Market not found")
        return False

    if market.get('closed'):
        print("❌ Market is closed.")
        return False

    # 3. Find Token ID for the requested side
    token_id = None
    target_outcome = side.lower()
    opposite_outcome = None

    # market['tokens'] contains the mapping
    tokens = market.get('tokens', [])

    # Find the token ID for the requested outcome
    if trade_side.upper() == "SELL":
        # SELL order - sell the requested outcome (close position)
        for t in tokens:
            if t['outcome'].lower() == target_outcome:
                token_id = t['token_id']
                break
    else:
        # BUY order - buy the requested outcome
        for t in tokens:
            if t['outcome'].lower() == target_outcome:
                token_id = t['token_id']
                break

    if not token_id:
        print(f"❌ Outcome '{side}' not found in market.")
        print("Available outcomes:")
        for t in tokens:
            print(f" - {t['outcome']}")
        return False

    # 4. Get Orderbook to determine price
    print(f"📊 Fetching orderbook for {side}...")
    try:
        ob = client.get_order_book(token_id)
    except Exception as e:
        print(f"❌ Error fetching orderbook: {e}")
        return False

    # For BUYING, we look at ASKS (lowest price sellers)
    # For SELLING, we look at BIDS (highest price buyers)
    if trade_side.upper() == "SELL":
        # SELLING - look at BIDS (highest price buyers)
        bids = ob.bids if hasattr(ob, 'bids') else []
        if not bids:
            print("❌ No liquidity (no bids) for this outcome.")
            return False
        # bids[0] is the best bid (highest price)
        best_bid = bids[0]
        best_price = float(best_bid.price)
        print(f"💰 Best Bid Price: {best_price} USDC")
    else:
        # BUYING - look at ASKS (lowest price sellers)
        asks = ob.asks if hasattr(ob, 'asks') else []
        if not asks:
            print("❌ No liquidity (no asks) for this outcome.")
            return False
        # asks[0] is the best ask (lowest price)
        best_ask = asks[0]
        best_price = float(best_ask.price)
        print(f"💰 Best Ask Price: {best_price} USDC")
    
    # 5. Calculate Execution Price and Size
    # Use best market price without slippage
    if trade_side.upper() == "SELL":
        # For SELLING, use best bid price (no discount)
        execution_price = round(best_price, 2)
        # For SELLING, amount is shares to sell, not USDC to receive
        size = amount  # amount is shares for SELL orders
    else:
        # For BUYING, use best ask price (no premium)
        execution_price = round(best_price, 2)
        # Calculate size (shares) = Amount (USDC) / Price
        size = amount / execution_price
        size = round(size, 2) # Round to 2 decimals

    # Round price to 2 decimals
    execution_price = round(execution_price, 2)

    if size < 0.1:
        print("❌ Size too small (must be > 0.1 shares).")
        return False

    print(f"\n📝 Trade Summary:")
    print(f"  - Market: {market.get('question', market_id)}")
    print(f"  - Action: {trade_side.upper()}")
    print(f"  - Position: {side}")
    print(f"  - Executing: {trade_side.upper()} {side.title()}")
    if trade_side.upper() == "SELL":
        print(f"  - Shares: {size} (selling)")
        print(f"  - Est. Price: {execution_price} USDC (at best bid)")
    else:
        print(f"  - Amount: {amount} USDC")
        print(f"  - Est. Price: {execution_price} USDC (at best ask)")
    print(f"  - Size: {size} Shares")
    
    # Check Auto Confirm Limit
    max_auto = float(os.getenv("MAX_AUTO_AMOUNT", "1.0"))
    if amount > max_auto and not auto_confirm:
        print(f"\n⚠️  Amount ({amount} USDC) exceeds auto-limit ({max_auto} USDC)")
        confirm = input("Confirm trade? (yes/no): ").strip().lower()
        if confirm != "yes":
            print("❌ Trade Cancelled")
            return False

    # 6. Execute Trade
    print("\n🚀 Executing trade...")
    try:
        # Create and Post Order
        # Using OrderArgs creates a Limit Order (GTC by default)
        order_args = OrderArgs(
            price=execution_price,
            size=size,
            side=trade_side.upper(),
            token_id=token_id,
        )
        
        resp = client.create_and_post_order(order_args)
        
        print("✅ Trade Submitted Successfully!")
        if hasattr(resp, 'orderID'):
            print(f"Order ID: {resp.orderID}")
        elif isinstance(resp, dict):
            print(f"Order ID: {resp.get('orderID')}")
        else:
            print(f"Response: {resp}")
            
        return True
        
    except Exception as e:
        print(f"❌ Trade Failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Execute Polymarket Trade")
    parser.add_argument("--market-id", required=True, help="Market Condition ID")
    parser.add_argument("--side", required=True, help="Outcome (Yes/No)")
    parser.add_argument("--amount", type=float, required=True, help="Amount in USDC")
    parser.add_argument("--auto-confirm", action="store_true", help="Skip confirmation")
    parser.add_argument("--trade-side", default="BUY", choices=["BUY", "SELL"], help="Trade direction (BUY or SELL)")

    args = parser.parse_args()

    success = execute_trade(args.market_id, args.side, args.amount, args.auto_confirm, args.trade_side)
    sys.exit(0 if success else 1)
