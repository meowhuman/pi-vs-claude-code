#!/usr/bin/env python3
"""
搜索市場 - 根據用戶指定嘅主題、年月範圍、機率同成交量
Search markets by user-specified topic, date range, probability, and volume

新增功能 (New Features):
  --prob      機率篩選 (e.g., 80:20, 75:25, 60:40)
  --min-vol   最低成交量篩選
  --urgent    只顯示 7 日內截止嘅市場
  --sort      排序方式 (volume / prob / date)
"""

import json
import sys
import argparse
from datetime import datetime, timezone
from fetch_all_markets import fetch_all_markets


def parse_prob_range(prob_arg: str):
    """
    解析機率範圍
    Parse probability range

    支持格式:
    - 80:20 -> (20, 80)  # 20% ~ 80%
    - 75:25 -> (25, 75)
    - 60:40 -> (40, 60)

    返回: (min_prob, max_prob) as percentages
    """
    try:
        if ":" in prob_arg:
            high, low = prob_arg.split(":")
            high = int(high)
            low = int(low)
            # Ensure low <= high
            min_prob = min(low, 100 - high)
            max_prob = max(high, 100 - low)
            return (min_prob, max_prob)
        else:
            raise ValueError("格式錯誤")
    except Exception:
        raise ValueError(f"❌ 無效嘅機率格式: {prob_arg}\n"
                        f"支持格式: 80:20, 75:25, 60:40 等")


def parse_year_range(year_arg):
    """
    解析年月範圍
    支持格式：
    - 2025 -> ["2025-01" 到 "2025-12"]
    - 2025-01 -> ["2025-01"]
    - 2025-2026 -> ["2025-01" 到 "2026-12"]
    - 2025-01:2026-06 -> ["2025-01" 到 "2026-06"]

    返回: (start_date_str, end_date_str, months_list)
    """
    try:
        if ":" in year_arg:
            # 格式: 2025-01:2026-06
            start, end = year_arg.split(":")
        elif "-" in year_arg:
            parts = year_arg.split("-")
            if len(parts) == 2 and len(parts[1]) == 2:
                # 格式: 2025-01 (單一月份)
                start = end = year_arg
            elif len(parts) == 2 and len(parts[1]) == 4:
                # 格式: 2025-2026 (年份範圍)
                start = f"{parts[0]}-01"
                end = f"{parts[1]}-12"
            else:
                raise ValueError("無效格式")
        else:
            # 格式: 2025 (整年)
            start = f"{year_arg}-01"
            end = f"{year_arg}-12"

        # 驗證日期格式
        datetime.strptime(start, "%Y-%m")
        datetime.strptime(end, "%Y-%m")

        # 生成所有月份列表
        start_year, start_month = map(int, start.split("-"))
        end_year, end_month = map(int, end.split("-"))

        months = []
        current_year = start_year
        current_month = start_month

        while (current_year, current_month) <= (end_year, end_month):
            months.append(f"{current_year:04d}-{current_month:02d}")
            current_month += 1
            if current_month > 12:
                current_month = 1
                current_year += 1

        return start, end, months

    except Exception as e:
        raise ValueError(f"❌ 無效嘅年月格式: {year_arg}\n"
                        f"支持格式:\n"
                        f"  - 2025\n"
                        f"  - 2025-01\n"
                        f"  - 2025-2026\n"
                        f"  - 2025-01:2026-06")

def filter_markets_by_date_range(markets, months):
    """根據月份列表過濾市場"""
    filtered = []
    for market in markets:
        end_date = market.get('end_date_iso', '')
        for month in months:
            if month in end_date:
                filtered.append(market)
                break
    return filtered


def filter_by_probability(markets, prob_range):
    """
    根據機率範圍過濾市場
    Filter markets by probability range

    Args:
        markets: 市場列表
        prob_range: (min_prob, max_prob) as percentages (e.g., (20, 80))
    """
    if not prob_range:
        return markets

    min_prob, max_prob = prob_range
    filtered = []

    for market in markets:
        chance = market.get('chance', 0) * 100  # Convert to percentage
        if min_prob <= chance <= max_prob:
            filtered.append(market)

    return filtered


def filter_by_volume(markets, min_volume):
    """
    根據最低成交量過濾市場
    Filter out illiquid markets below minimum volume
    """
    if not min_volume or min_volume <= 0:
        return markets

    return [m for m in markets if m.get('volume', 0) >= min_volume]


def filter_urgent_markets(markets, days=7):
    """
    只保留 N 日內截止嘅市場
    Filter to keep only markets closing within N days
    """
    now = datetime.now(timezone.utc)
    urgent = []

    for market in markets:
        end_date_str = market.get('end_date_iso', '')
        if end_date_str:
            try:
                end_dt = datetime.fromisoformat(end_date_str.replace('Z', '+00:00'))
                days_left = (end_dt - now).days
                if 0 <= days_left <= days:
                    market['_days_left'] = days_left
                    urgent.append(market)
            except:
                pass

    return urgent


def sort_markets(markets, sort_by='volume'):
    """
    排序市場
    Sort markets by specified criteria

    Args:
        sort_by: 'volume', 'prob', 'date'
    """
    if sort_by == 'volume':
        return sorted(markets, key=lambda x: x.get('volume', 0), reverse=True)
    elif sort_by == 'prob':
        # Sort by how balanced the probability is (closer to 50% = more balanced)
        return sorted(markets, key=lambda x: abs(x.get('chance', 0) * 100 - 50))
    elif sort_by == 'date':
        return sorted(markets, key=lambda x: x.get('end_date_iso', ''))
    else:
        return markets


def print_distribution_analysis(markets):
    """
    顯示機率分佈分析
    Show probability distribution analysis
    """
    if not markets:
        return

    print("\n" + "=" * 60)
    print("📈 機率分佈分析 / Probability Distribution Analysis")
    print("=" * 60)

    # Count by ranges
    range_60_40 = sum(1 for m in markets if 40 <= m.get('chance', 0) * 100 <= 60)
    range_70_30 = sum(1 for m in markets if 30 <= m.get('chance', 0) * 100 <= 70)
    range_75_25 = sum(1 for m in markets if 25 <= m.get('chance', 0) * 100 <= 75)
    range_80_20 = sum(1 for m in markets if 20 <= m.get('chance', 0) * 100 <= 80)

    print(f"  🎯 60-40 (最平衡 / Most Balanced): {range_60_40} 個市場")
    print(f"  📊 70-30: {range_70_30} 個市場")
    print(f"  📊 75-25: {range_75_25} 個市場")
    print(f"  📊 80-20: {range_80_20} 個市場")

    # Volume stats
    if markets:
        volumes = [m.get('volume', 0) for m in markets]
        avg_vol = sum(volumes) / len(volumes)
        max_vol = max(volumes)
        print(f"\n  💰 平均成交量: ${avg_vol:,.0f}")
        print(f"  💰 最高成交量: ${max_vol:,.0f}")

    # High volume count
    high_vol = sum(1 for m in markets if m.get('volume', 0) >= 100000)
    if high_vol:
        print(f"  🔥 高流動性市場 (>$100k): {high_vol} 個")


def display_markets(markets, limit=20):
    """
    顯示市場列表
    Display market list with details
    """
    if not markets:
        print("\n❌ 沒有找到符合條件嘅市場")
        return

    print(f"\n🎯 找到 {len(markets)} 個市場，顯示前 {min(limit, len(markets))} 個:")
    print("=" * 100)

    for i, market in enumerate(markets[:limit], 1):
        question = market.get('question', 'N/A')
        if len(question) > 70:
            question = question[:67] + "..."

        condition_id = market.get('condition_id', 'N/A')
        volume = market.get('volume', 0)
        chance = market.get('chance', 0) * 100
        end_date = market.get('end_date_iso', 'N/A')
        slug = market.get('event_slug', '')
        days_left = market.get('_days_left')

        print(f"\n{i}. {question}")
        print(f"   ID:     {condition_id}")
        print(f"   💰 Vol:  ${volume:,.0f}")
        print(f"   🎲 Prob: {chance:.1f}%")

        # Show days left if available
        if days_left is not None:
            if days_left == 0:
                print(f"   ⏰ 截止: {end_date[:10]} (🔴 TODAY!)")
            elif days_left == 1:
                print(f"   ⏰ 截止: {end_date[:10]} (🟠 TOMORROW)")
            else:
                print(f"   ⏰ 截止: {end_date[:10]} ({days_left} 日後)")
        else:
            print(f"   📅 截止: {end_date[:10] if end_date else 'N/A'}")

        if slug:
            print(f"   🔗 URL:  https://polymarket.com/event/{slug}")

    print("\n" + "=" * 100)


def search_markets_enhanced(args):
    """
    增強版市場搜索 - 支持機率、成交量、緊急程度過濾
    Enhanced market search with probability, volume, and urgency filters
    """
    print("🚀 獲取所有市場...")
    all_markets = fetch_all_markets(force_refresh=args.force_refresh)
    print(f"✅ 載入 {len(all_markets)} 個市場")

    # Step 1: Date range filter
    if args.year:
        try:
            start_date, end_date, months = parse_year_range(args.year)
            markets = filter_markets_by_date_range(all_markets, months)
            print(f"📅 日期範圍 {start_date} ~ {end_date}: {len(markets)} 個市場")
        except ValueError as e:
            print(str(e))
            sys.exit(1)
    else:
        markets = all_markets

    # Step 2: Topic/keyword filter
    if args.topic:
        keywords = [k.strip().lower() for k in args.topic.split(",")]
        filtered = []
        for market in markets:
            question_lower = market.get('question', '').lower()
            title_lower = market.get('event_title', '').lower()
            for kw in keywords:
                if kw in question_lower or kw in title_lower:
                    filtered.append(market)
                    break
        markets = filtered
        print(f"🔍 主題匹配 '{args.topic}': {len(markets)} 個市場")

    # Step 3: Probability filter
    if args.prob:
        try:
            prob_range = parse_prob_range(args.prob)
            markets = filter_by_probability(markets, prob_range)
            print(f"🎲 機率範圍 {args.prob}: {len(markets)} 個市場")
        except ValueError as e:
            print(str(e))
            sys.exit(1)

    # Step 4: Volume filter
    if args.min_vol:
        markets = filter_by_volume(markets, args.min_vol)
        print(f"💰 成交量 >= ${args.min_vol:,.0f}: {len(markets)} 個市場")

    # Step 5: Urgency filter
    if args.urgent:
        markets = filter_urgent_markets(markets, days=args.urgent)
        print(f"⏰ {args.urgent} 日內截止: {len(markets)} 個市場")

    # Step 6: Sort
    markets = sort_markets(markets, args.sort)

    # Display results
    display_markets(markets, limit=args.limit)

    # Show distribution analysis
    if args.analyze and markets:
        print_distribution_analysis(markets)

    # Save results
    output_file = 'extended_market_search.json'
    results = {
        "search_params": {
            "topic": args.topic,
            "year": args.year,
            "prob": args.prob,
            "min_vol": args.min_vol,
            "urgent": args.urgent,
            "sort": args.sort,
        },
        "total_matched": len(markets),
        "markets": markets[:100],  # Save top 100
    }
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2, default=str)
    print(f"\n💾 結果已保存到 {output_file}")

    return markets


def main():
    parser = argparse.ArgumentParser(
        description='Polymarket 增強版市場搜索工具',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
範例 / Examples:
  # 搜索 2025 年所有 Trump 相關市場
  python search_extended_markets.py --topic "Trump" --year 2025

  # 搜索機率在 75:25 範圍內嘅高流動性市場
  python search_extended_markets.py --prob 75:25 --min-vol 50000

  # 搜索 7 日內截止嘅選舉市場
  python search_extended_markets.py --topic "election" --urgent 7

  # 搜索平衡嘅 crypto 市場，按機率平衡度排序
  python search_extended_markets.py --topic "bitcoin,crypto" --prob 60:40 --sort prob

  # 顯示分佈分析
  python search_extended_markets.py --topic "politics" --year 2025 --analyze
"""
    )

    parser.add_argument('--topic', '-t', type=str, 
                        help='搜索主題/關鍵字 (可用逗號分隔多個)')
    parser.add_argument('--year', '-y', type=str, 
                        help='年月範圍 (e.g., 2025, 2025-01, 2025-2026)')
    parser.add_argument('--prob', '-p', type=str, 
                        help='機率範圍 (e.g., 80:20, 75:25, 60:40)')
    parser.add_argument('--min-vol', type=float, default=0,
                        help='最低成交量 (過濾冇流動性嘅市場)')
    parser.add_argument('--urgent', '-u', type=int, 
                        help='只顯示 N 日內截止嘅市場')
    parser.add_argument('--sort', '-s', type=str, default='volume',
                        choices=['volume', 'prob', 'date'],
                        help='排序方式: volume(成交量), prob(機率平衡度), date(截止日期)')
    parser.add_argument('--limit', '-l', type=int, default=20,
                        help='顯示結果數量 (預設: 20)')
    parser.add_argument('--analyze', '-a', action='store_true',
                        help='顯示機率分佈分析')
    parser.add_argument('--force-refresh', action='store_true',
                        help='強制重新下載市場數據 (忽略緩存)')

    args = parser.parse_args()

    # Validate: need at least one filter
    if not any([args.topic, args.year, args.prob, args.urgent]):
        parser.print_help()
        print("\n⚠️  請至少提供一個篩選條件 (--topic, --year, --prob, 或 --urgent)")
        sys.exit(1)

    search_markets_enhanced(args)


if __name__ == "__main__":
    main()