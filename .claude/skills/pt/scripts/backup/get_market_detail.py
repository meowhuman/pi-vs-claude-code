#!/usr/bin/env python3
"""
Get detailed market information using CLOB API
"""
import os
import sys
from dotenv import load_dotenv
from py_clob_client.client import ClobClient
from py_clob_client.constants import POLYGON

load_dotenv()

def get_market_detail(market_id: str):
    """
    Get market details from CLOB API
    """
    host = "https://clob.polymarket.com"
    key = os.getenv("POLYGON_PRIVATE_KEY")

    if not key:
        print("❌ Error: POLYGON_PRIVATE_KEY not found in .env")
        return None

    try:
        # Initialize client
        client = ClobClient(host, key=key, chain_id=POLYGON)

        # Get market details
        print(f"🔍 獲取市場詳情...")
        market = client.get_market(market_id)

        if not market:
            print("❌ 找不到市場")
            return None

        print(f"\n{'='*60}")
        print(f"📊 市場詳情")
        print(f"{'='*60}")
        print(f"問題: {market.get('question', 'N/A')}")
        print(f"市場 ID: {market_id}")
        print(f"狀態: {'✅ 開放' if market.get('active') and not market.get('closed') else '❌ 已關閉'}")
        print(f"結束時間: {market.get('end_date_iso', 'N/A')}")
        print(f"描述: {market.get('description', 'N/A')[:150]}...")
        print(f"{'='*60}")

        # Get tokens (outcomes)
        tokens = market.get('tokens', [])

        if tokens:
            print(f"\n💰 結果選項與價格:")
            print(f"{'='*60}")

            for token in tokens:
                outcome = token.get('outcome', 'N/A')
                token_id = token.get('token_id', 'N/A')

                # Get orderbook for this token
                try:
                    ob = client.get_order_book(token_id)
                    asks = ob.asks if hasattr(ob, 'asks') and ob.asks else []
                    bids = ob.bids if hasattr(ob, 'bids') and ob.bids else []

                    best_ask = float(asks[0].price) if asks else None
                    best_bid = float(bids[0].price) if bids else None

                    print(f"\n  {outcome}:")
                    print(f"    Token ID: {token_id}")
                    if best_bid and best_ask:
                        mid_price = (best_bid + best_ask) / 2
                        print(f"    最佳買價 (Bid): ${best_bid:.3f}")
                        print(f"    最佳賣價 (Ask): ${best_ask:.3f}")
                        print(f"    中間價: ${mid_price:.3f}")
                        print(f"    價差: ${(best_ask - best_bid):.3f}")
                    else:
                        print(f"    ⚠️  流動性不足")

                except Exception as e:
                    print(f"\n  {outcome}:")
                    print(f"    Token ID: {token_id}")
                    print(f"    ⚠️  無法獲取價格: {e}")

        print(f"\n{'='*60}")

        return market

    except Exception as e:
        print(f"❌ 錯誤: {e}")
        import traceback
        traceback.print_exc()
        return None

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python get_market_detail.py <market-id>")
        sys.exit(1)

    market_id = sys.argv[1]
    get_market_detail(market_id)
