#!/usr/bin/env python3
"""
Screen markets with 80/20 probability balances
Filters markets to find those with balanced probabilities (70-30 to 85-15 range)
"""

import json
import sys
from datetime import datetime

def load_all_markets():
    """Load all markets from cache"""
    try:
        with open('all_markets_cache.json', 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        print("❌ No market cache found. Please run search_extended_markets.py first to download markets.")
        return None

def filter_80_20_markets(markets, min_volume=10000, search_term=None):
    """
    Filter markets with probabilities in the 70-30 to 85-15 range
    and minimum volume threshold
    """
    filtered_markets = []

    for market in markets:
        # Skip if not active
        if not market.get('active', True):
            continue

        # Skip if closed
        if market.get('closed', False):
            continue

        prob = market.get('chance', 0) * 100  # Convert to percentage
        volume = market.get('volume', 0)
        question = market.get('question', '').lower()

        # Apply search term filter if provided
        if search_term and search_term.lower() not in question:
            continue

        # Skip if volume too low
        if volume < min_volume:
            continue

        # Check for balanced probabilities
        # 70-30 range: prob between 30-70%
        # 75-25 range: prob between 25-75%
        # 80-20 range: prob between 20-80%
        if 20 <= prob <= 80:
            filtered_markets.append({
                'question': market.get('question'),
                'probability': prob,
                'volume_24h': volume,
                'end_date_iso': market.get('end_date_iso'),
                'condition_id': market.get('condition_id'),
                'event_slug': market.get('event_slug')
            })

    # Sort by volume (descending)
    filtered_markets.sort(key=lambda x: x['volume_24h'], reverse=True)
    return filtered_markets

def main():
    import argparse

    parser = argparse.ArgumentParser(description='Screen for markets with 80/20 probability balances')
    parser.add_argument('--min-volume', type=float, default=10000, help='Minimum volume threshold (default: 10000)')
    parser.add_argument('--search', type=str, help='Filter markets containing this term')
    parser.add_argument('--finance', action='store_true', help='Filter for finance-related markets')

    args = parser.parse_args()

    print("🎯 Screening for 80/20 Markets\n")

    # Load all markets
    markets = load_all_markets()
    if not markets:
        return

    print(f"📊 Loaded {len(markets)} total markets")

    # Determine search terms
    search_terms = []
    if args.search:
        search_terms.append(args.search)
    elif args.finance:
        search_terms = ['fed', 'bitcoin', 'inflation', 'stock', 'market', 'economy', 'trading', 'finance', 'crypto', 'treasury', 'dollar']

    # Filter markets
    all_balanced = []
    if search_terms:
        for term in search_terms:
            balanced = filter_80_20_markets(markets, min_volume=args.min_volume, search_term=term)
            all_balanced.extend(balanced)
            print(f"  - '{term}': {len(balanced)} markets")

        # Remove duplicates
        seen_ids = set()
        unique_balanced = []
        for m in all_balanced:
            if m['condition_id'] not in seen_ids:
                seen_ids.add(m['condition_id'])
                unique_balanced.append(m)
        balanced_markets = unique_balanced
    else:
        balanced_markets = filter_80_20_markets(markets, min_volume=args.min_volume)

    print(f"\n✅ Found {len(balanced_markets)} markets with 20-80 probability balance (Volume > ${args.min_volume:,.0f})\n")

    if not balanced_markets:
        print("⚠️ No markets found with balanced probabilities.")
        print("Most markets show extreme probabilities (90-10 or worse)")
        print("\n💡 Tips:")
        print("- Try a lower --min-volume (e.g., 1000)")
        print("- Search specific topics with --search")
        print("- Use --finance for broader finance coverage")
        return

    # Display results
    print("="*180)
    print(f"{'Market':<60} | {'Prob':<6} | {'Volume':<12} | {'Closes':<12} | {'Market ID'}")
    print("-"*180)

    for market in balanced_markets[:25]:  # Show top 25
        question = market.get('question', 'Unknown')
        if len(question) > 57:
            question = question[:57] + "..."

        prob = market.get('probability', 0)
        volume = market.get('volume_24h', 0)
        end_date = market.get('end_date_iso', '')
        market_id = market.get('condition_id', 'N/A')

        # Format end date with time
        if end_date:
            try:
                dt = datetime.fromisoformat(end_date.replace('Z', '+00:00'))
                # Calculate days until close
                now = datetime.now(dt.tzinfo)
                days_left = (dt.date() - now.date()).days

                if days_left == 0:
                    days_str = "TODAY"
                elif days_left == 1:
                    days_str = "TOMORROW"
                elif days_left < 0:
                    days_str = "CLOSED"
                else:
                    days_str = f"{days_left} days"

                end_str = f"{dt.strftime('%Y-%m-%d')} ({days_str})"
            except:
                end_str = end_date[:10] + " (?)"
        else:
            end_str = 'N/A'

        # Shorten market ID for display
        if market_id != 'N/A' and len(market_id) > 15:
            market_display = market_id[:8] + "..." + market_id[-4:]
        else:
            market_display = market_id

        print(f"{question:<60} | {prob:>5.1f}% | ${volume:>10,.0f} | {end_str:<12} | {market_display}")

    print("="*120)

    # Additional analysis
    print("\n📈 Distribution Analysis:")
    print("-" * 50)

    # Count by probability ranges
    range_70_30 = sum(1 for m in balanced_markets if 30 <= m['probability'] <= 70)
    range_80_20 = sum(1 for m in balanced_markets if 20 <= m['probability'] <= 80)
    range_75_25 = sum(1 for m in balanced_markets if 25 <= m['probability'] <= 75)
    range_60_40 = sum(1 for m in balanced_markets if 40 <= m['probability'] <= 60)

    print(f"60-40 range: {range_60_40} markets (most balanced)")
    print(f"70-30 range: {range_70_30} markets")
    print(f"75-25 range: {range_75_25} markets")
    print(f"80-20 range: {range_80_20} markets")

    # Calculate average volume
    avg_volume = sum(m['volume_24h'] for m in balanced_markets) / len(balanced_markets) if balanced_markets else 0
    print(f"\nAverage volume: ${avg_volume:,.0f}")

    # Show high volume markets
    high_volume = [m for m in balanced_markets if m['volume_24h'] > 100000]
    if high_volume:
        print(f"\n💰 High Volume Markets (>$100k): {len(high_volume)}")
        for m in high_volume[:10]:
            print(f"  • {m['question'][:60]}... (${m['volume_24h']:,.0f}, {m['probability']:.1f}%)")

    # Show time-critical markets
    urgent_markets = []
    now = datetime.now()

    for market in balanced_markets:
        end_date = market.get('end_date_iso', '')
        if end_date:
            try:
                dt = datetime.fromisoformat(end_date.replace('Z', '+00:00'))
                days_left = (dt.date() - now.date()).days
                if days_left <= 7:  # Closing within a week
                    urgent_markets.append(market)
            except:
                pass

    if urgent_markets:
        print(f"\n🚨 URGENT - Markets Closing Soon (within 7 days):")
        print("-" * 80)
        for market in urgent_markets[:10]:
            end_date = market.get('end_date_iso', '')
            if end_date:
                try:
                    dt = datetime.fromisoformat(end_date.replace('Z', '+00:00'))
                    days_left = (dt.date() - now.date()).days
                    print(f"  • {market['question'][:50]}... - {days_left} days left ({market['probability']:.1f}%)")
                except:
                    pass

    # Export to JSON for further analysis
    output_file = 'balanced_markets.json'
    with open(output_file, 'w') as f:
        json.dump(balanced_markets, f, indent=2)
    print(f"\n💾 Results saved to {output_file}")

if __name__ == "__main__":
    main()