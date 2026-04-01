#!/usr/bin/env python3
"""
Get market details from Polymarket URL
"""
import os
import sys
import requests
from dotenv import load_dotenv
from py_clob_client.client import ClobClient
from py_clob_client.constants import POLYGON

load_dotenv()

def get_market_from_slug(slug: str):
    """
    Get market details from slug (URL path)

    Args:
        slug: Market slug from URL (e.g., "maduro-out-in-2025")
    """
    # Use Polymarket API to search for the market
    api_url = "https://gamma-api.polymarket.com/events"

    try:
        # Search for events
        params = {
            "slug": slug,
            "closed": "false"
        }
        response = requests.get(api_url, params=params)
        response.raise_for_status()

        events = response.json()

        if not events:
            print(f"❌ 找不到市場: {slug}")
            return None

        event = events[0] if isinstance(events, list) else events

        print(f"\n📊 市場資訊:")
        print(f"="*60)
        print(f"標題: {event.get('title', 'N/A')}")
        print(f"描述: {event.get('description', 'N/A')[:100]}...")
        print(f"結束時間: {event.get('endDate', 'N/A')}")
        print(f"="*60)

        # Get markets from this event
        markets = event.get('markets', [])

        if not markets:
            print("❌ 沒有找到交易市場")
            return None

        print(f"\n💱 可交易市場:")
        print(f"="*60)

        for i, market in enumerate(markets, 1):
            question = market.get('question', 'N/A')
            condition_id = market.get('conditionId', 'N/A')

            # Get outcomes
            tokens = market.get('tokens', [])
            print(f"\n{i}. {question}")
            print(f"   Market ID: {condition_id}")
            print(f"   結果選項:")

            for token in tokens:
                outcome = token.get('outcome', 'N/A')
                token_id = token.get('token_id', 'N/A')
                price = token.get('price', 'N/A')
                print(f"     - {outcome}: ${price} (Token ID: {token_id})")

        return event

    except Exception as e:
        print(f"❌ 錯誤: {e}")
        import traceback
        traceback.print_exc()
        return None

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python get_market_from_url.py <market-slug>")
        print("Example: python get_market_from_url.py maduro-out-in-2025")
        sys.exit(1)

    slug = sys.argv[1]
    get_market_from_slug(slug)
