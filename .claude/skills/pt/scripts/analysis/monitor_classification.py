#!/usr/bin/env python3
"""
Monitor batch classification progress
"""

import json
from pathlib import Path
import time
import sys

PROGRESS_FILE = Path(__file__).parent.parent / 'state' / 'classification_progress.json'
RESULTS_FILE = Path(__file__).parent.parent / 'state' / 'whale_classifications.json'

def show_progress():
    """Display current progress"""
    if not PROGRESS_FILE.exists():
        print("❌ No progress file found. Classification not started yet.")
        return
    
    with open(PROGRESS_FILE, 'r') as f:
        progress = json.load(f)
    
    completed = len(progress.get('completed', []))
    failed = len(progress.get('failed', []))
    total = progress.get('total_processed', 0)
    
    print(f"\n📊 批量分類進度")
    print("=" * 50)
    print(f"✅ 已完成: {completed}")
    print(f"❌ 失敗: {failed}")
    print(f"📈 總處理: {total}")
    print(f"🎯 目標: 100")
    print(f"📊 進度: {total}/100 ({total}%)")
    
    if RESULTS_FILE.exists():
        with open(RESULTS_FILE, 'r') as f:
            results = json.load(f)
        
        classifications = results.get('classifications', [])
        
        if classifications:
            from collections import Counter
            role_counts = Counter(c.get('role', 'UNKNOWN') for c in classifications)
            
            print(f"\n🏷️ 目前分類:")
            emoji_map = {
                'SMART_MONEY': '🧠',
                'WHALE': '🐋',
                'LOSER': '📉',
                'MARKET_MAKER': '🏦',
                'RETAILER': '🎰',
                'REGULAR': '👤',
                'UNKNOWN': '❓',
                'ERROR': '❌',
                'TIMEOUT': '⏱️'
            }
            
            for role, count in sorted(role_counts.items(), key=lambda x: x[1], reverse=True):
                emoji = emoji_map.get(role, '❓')
                print(f"  {emoji} {role:<15}: {count:>3}")
    
    print("=" * 50)

if __name__ == "__main__":
    try:
        while True:
            print("\033[2J\033[H")  # Clear screen
            show_progress()
            print(f"\n🔄 更新中... (Ctrl+C 退出)")
            time.sleep(3)
    except KeyboardInterrupt:
        print("\n\n✅ 監控結束")
        sys.exit(0)
