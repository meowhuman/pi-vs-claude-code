#!/usr/bin/env python3
"""
Parallel Batch Whale Classifier
Efficiently classify whale wallets using parallel processing with analyze.py
"""

import json
import subprocess
import time
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
import sys
import re

# Configuration
WHALE_SCAN_FILE = Path(__file__).parent.parent / 'state' / 'whale_holders_scan.json'
PROGRESS_FILE = Path(__file__).parent.parent / 'state' / 'classification_progress.json'
RESULTS_FILE = Path(__file__).parent.parent / 'state' / 'whale_classifications.json'

MAX_WORKERS = 5  # Parallel workers (避免 API rate limit)
BATCH_SIZE = 100  # Process top 100 first
TIMEOUT = 45  # Seconds per wallet analysis


def load_progress():
    """Load classification progress"""
    if PROGRESS_FILE.exists():
        with open(PROGRESS_FILE, 'r') as f:
            return json.load(f)
    return {'completed': [], 'failed': [], 'total_processed': 0}


def save_progress(progress):
    """Save classification progress"""
    with open(PROGRESS_FILE, 'w') as f:
        json.dump(progress, f, indent=2)


def load_results():
    """Load existing classification results"""
    if RESULTS_FILE.exists():
        with open(RESULTS_FILE, 'r') as f:
            return json.load(f)
    return {'classifications': [], 'summary': {}}


def save_results(results):
    """Save classification results"""
    with open(RESULTS_FILE, 'w') as f:
        json.dump(results, f, indent=2)


def extract_classification(output):
    """Extract role from analyze.py output"""
    role_markers = {
        'SMART_MONEY': ['🧠 SMART_MONEY', 'Smart Money'],
        'WHALE': ['🐋 WHALE', '🐋 Whale'],
        'LOSER': ['📉 LOSER', '📉 Whale Loser'],
        'MARKET_MAKER': ['🏦 MARKET_MAKER', 'Market Maker'],
        'RETAILER': ['🎰 RETAILER', 'Retailer'],
        'REGULAR': ['👤 REGULAR', 'Regular']
    }
    
    for role, markers in role_markers.items():
        for marker in markers:
            if marker in output:
                return role, get_emoji(role)
    
    return 'UNKNOWN', '❓'


def get_emoji(role):
    """Get emoji for role"""
    emoji_map = {
        'SMART_MONEY': '🧠',
        'WHALE': '🐋',
        'LOSER': '📉',
        'MARKET_MAKER': '🏦',
        'RETAILER': '🎰',
        'REGULAR': '👤',
        'UNKNOWN': '❓',
        'ERROR': '❌'
    }
    return emoji_map.get(role, '❓')


def analyze_wallet(wallet_data, index, total):
    """Analyze a single wallet using analyze.py"""
    wallet = wallet_data['wallet']
    rank = wallet_data['rank']
    value = wallet_data['total_value']
    
    wallet_short = wallet[:10] + '...' + wallet[-4:]
    
    try:
        # Run analyze.py wallet
        result = subprocess.run(
            ['python', 'analyze.py', 'wallet', wallet],
            capture_output=True,
            text=True,
            timeout=TIMEOUT,
            cwd=Path(__file__).parent
        )
        
        output = result.stdout + result.stderr
        
        # Extract classification
        role, emoji = extract_classification(output)
        
        # Extract key metrics if available
        pnl = 0
        win_rate = 0
        
        # Try to extract PnL
        pnl_match = re.search(r'總 P&L.*?\$?([-\d,]+\.?\d*)', output)
        if pnl_match:
            try:
                pnl = float(pnl_match.group(1).replace(',', ''))
            except:
                pass
        
        # Try to extract win rate
        win_match = re.search(r'勝率.*?([\d.]+)%', output)
        if win_match:
            try:
                win_rate = float(win_match.group(1))
            except:
                pass
        
        print(f"[{index}/{total}] {emoji} {wallet_short}: {role} (${value:,.0f})")
        
        return {
            'success': True,
            'wallet': wallet,
            'rank': rank,
            'value': value,
            'role': role,
            'emoji': emoji,
            'pnl': pnl,
            'win_rate': win_rate,
            'timestamp': datetime.now().isoformat()
        }
        
    except subprocess.TimeoutExpired:
        print(f"[{index}/{total}] ⏱️ {wallet_short}: TIMEOUT")
        return {
            'success': False,
            'wallet': wallet,
            'rank': rank,
            'value': value,
            'role': 'TIMEOUT',
            'emoji': '⏱️',
            'error': 'Analysis timeout'
        }
    
    except Exception as e:
        print(f"[{index}/{total}] ❌ {wallet_short}: ERROR - {str(e)[:30]}")
        return {
            'success': False,
            'wallet': wallet,
            'rank': rank,
            'value': value,
            'role': 'ERROR',
            'emoji': '❌',
            'error': str(e)[:100]
        }


def main():
    print("🐋 並行批量 Whale 分類器")
    print("=" * 80)
    
    # Load whale scan data
    if not WHALE_SCAN_FILE.exists():
        print(f"❌ Whale scan file not found: {WHALE_SCAN_FILE}")
        return
    
    with open(WHALE_SCAN_FILE, 'r') as f:
        whale_data = json.load(f)
    
    all_whales = whale_data['whales']
    
    # Load progress
    progress = load_progress()
    completed_wallets = set(progress['completed'])
    
    # Filter to process (Top 100, excluding already completed)
    to_process = [
        w for w in all_whales[:BATCH_SIZE]
        if w['wallet'] not in completed_wallets
    ]
    
    if not to_process:
        print("✅ All whales in batch already classified!")
        print(f"📊 Processed: {len(completed_wallets)} / {BATCH_SIZE}")
        return
    
    print(f"📊 Total whales: {len(all_whales)}")
    print(f"🎯 Batch size: {BATCH_SIZE}")
    print(f"✅ Already completed: {len(completed_wallets)}")
    print(f"⚡ To process: {len(to_process)}")
    print(f"🔧 Workers: {MAX_WORKERS}")
    print(f"⏱️ Estimated time: {len(to_process) * 10 / MAX_WORKERS / 60:.1f} minutes")
    print("=" * 80 + "\n")
    
    # Load existing results
    results = load_results()
    classifications = results.get('classifications', [])
    
    # Process in parallel
    start_time = time.time()
    
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = {
            executor.submit(analyze_wallet, whale, i, len(to_process)): whale
            for i, whale in enumerate(to_process, 1)
        }
        
        for future in as_completed(futures):
            result = future.result()
            
            if result['success']:
                progress['completed'].append(result['wallet'])
                classifications.append(result)
            else:
                progress['failed'].append({
                    'wallet': result['wallet'],
                    'error': result.get('error', 'Unknown')
                })
            
            progress['total_processed'] += 1
            
            # Save progress every 5 wallets
            if progress['total_processed'] % 5 == 0:
                save_progress(progress)
                
                # Update results
                results['classifications'] = classifications
                save_results(results)
    
    # Final save
    save_progress(progress)
    
    # Generate summary
    from collections import Counter
    role_counts = Counter(c['role'] for c in classifications)
    
    summary = {
        'total_classified': len(classifications),
        'role_distribution': dict(role_counts),
        'classification_date': datetime.now().isoformat(),
        'processing_time_minutes': (time.time() - start_time) / 60
    }
    
    results['classifications'] = classifications
    results['summary'] = summary
    save_results(results)
    
    # Print summary
    print("\n" + "=" * 80)
    print("📊 分類完成！")
    print("=" * 80)
    print(f"✅ 成功分類: {len([c for c in classifications if c.get('success', True)])}")
    print(f"❌ 失敗/超時: {len(progress['failed'])}")
    print(f"⏱️ 處理時間: {summary['processing_time_minutes']:.1f} 分鐘")
    print(f"\n角色分佈:")
    
    for role, count in sorted(role_counts.items(), key=lambda x: x[1], reverse=True):
        emoji = get_emoji(role)
        print(f"  {emoji} {role:<15}: {count:>3} 個")
    
    print(f"\n💾 結果已保存:")
    print(f"   分類結果: {RESULTS_FILE}")
    print(f"   進度文件: {PROGRESS_FILE}")
    print("\n🔄 如需繼續處理剩餘錢包，再次運行此腳本")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️ 中斷！進度已保存，可隨時恢復。")
        sys.exit(0)
