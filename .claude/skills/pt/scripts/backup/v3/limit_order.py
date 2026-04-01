#!/usr/bin/env python3
"""
Polymarket Limit Order Manager
- 以指定價格掛單
- 支援買入/賣出
- 查看未成交訂單
"""

import os
import sys
import json
import argparse
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

CLOB_API = "https://clob.polymarket.com"


def get_client():
    """初始化 CLOB Client"""
    from py_clob_client.client import ClobClient
    from py_clob_client.constants import POLYGON
    
    signing_key = os.getenv("POLYGON_PRIVATE_KEY")
    builder_wallet = os.getenv("BUILDER_WALLET_ADDRESS")
    
    if not signing_key or not builder_wallet:
        print("❌ 請設定 POLYGON_PRIVATE_KEY 和 BUILDER_WALLET_ADDRESS")
        sys.exit(1)
    
    client = ClobClient(
        CLOB_API,
        key=signing_key,
        chain_id=POLYGON,
        signature_type=1,
        funder=builder_wallet
    )
    
    # Derive API creds
    derived_creds = client.create_or_derive_api_creds()
    client.set_api_creds(derived_creds)
    
    return client


def get_token_id(client, condition_id: str, outcome: str) -> str:
    """獲取 Token ID"""
    market = client.get_market(condition_id)
    tokens = market.get('tokens', [])
    
    for t in tokens:
        if t['outcome'].lower() == outcome.lower():
            return t['token_id']
    
    return None


def place_limit_order(condition_id: str, outcome: str, side: str, price: float, 
                      size: float = None, amount: float = None, auto_confirm: bool = False):
    """
    掛 Limit Order
    
    Args:
        condition_id: 市場 ID
        outcome: Yes/No
        side: BUY/SELL
        price: 掛單價格 (0.01 - 0.99)
        size: 股數 (用於 SELL)
        amount: USDC 金額 (用於 BUY)
    """
    from py_clob_client.clob_types import OrderArgs
    
    print(f"\n📝 準備 Limit Order...")
    print(f"   市場: {condition_id[:20]}...")
    print(f"   方向: {side} {outcome}")
    print(f"   價格: ${price:.2f}")
    
    if side.upper() == "BUY":
        if not amount:
            print("❌ BUY 訂單需要指定 --amount (USDC 金額)")
            return False
        size = round(amount / price, 2)
        print(f"   金額: ${amount:.2f} USDC")
        print(f"   預計獲得: {size:.2f} shares")
    else:  # SELL
        if not size:
            print("❌ SELL 訂單需要指定 --size (股數)")
            return False
        estimated_value = size * price
        print(f"   股數: {size:.2f}")
        print(f"   預計收入: ${estimated_value:.2f} USDC")
    
    if not auto_confirm:
        confirm = input(f"\n確認掛單? (yes/no): ").strip().lower()
        if confirm not in ["yes", "y"]:
            print("❌ 已取消")
            return False
    
    try:
        client = get_client()
        token_id = get_token_id(client, condition_id, outcome)
        
        if not token_id:
            print(f"❌ 找不到 {outcome} outcome")
            return False
        
        order_args = OrderArgs(
            price=price,
            size=size,
            side=side.upper(),
            token_id=token_id,
        )
        
        print(f"\n🚀 正在掛單...")
        resp = client.create_and_post_order(order_args)
        
        order_id = resp.orderID if hasattr(resp, 'orderID') else resp.get('orderID', '?')
        
        print(f"\n✅ Limit Order 已提交!")
        print(f"   Order ID: {order_id}")
        print(f"   狀態: 等待成交...")
        
        return True
        
    except Exception as e:
        print(f"❌ 掛單失敗: {e}")
        import traceback
        traceback.print_exc()
        return False


def list_open_orders():
    """列出所有未成交訂單"""
    print(f"\n📋 查詢未成交訂單...")
    
    try:
        client = get_client()
        orders = client.get_orders()
        
        if not orders:
            print("📭 沒有未成交訂單")
            return
        
        print(f"\n找到 {len(orders)} 個訂單:\n")
        print("="*80)
        
        for i, order in enumerate(orders, 1):
            order_id = order.get('id', '?')[:16]
            side = order.get('side', '?')
            price = order.get('price', 0)
            size = order.get('original_size', order.get('size', 0))
            filled = order.get('size_matched', 0)
            status = order.get('status', '?')
            
            print(f"{i}. [{status}] {side} @ ${price}")
            print(f"   Size: {size} (Filled: {filled})")
            print(f"   ID: {order_id}...")
            print()
        
        print("="*80)
        
    except Exception as e:
        print(f"❌ 查詢失敗: {e}")


def cancel_order(order_id: str):
    """取消訂單"""
    print(f"\n🗑️ 取消訂單: {order_id[:20]}...")
    
    try:
        client = get_client()
        resp = client.cancel(order_id)
        
        print(f"✅ 訂單已取消")
        return True
        
    except Exception as e:
        print(f"❌ 取消失敗: {e}")
        return False


def cancel_all_orders():
    """取消所有訂單"""
    print(f"\n🗑️ 取消所有訂單...")
    
    try:
        client = get_client()
        resp = client.cancel_all()
        
        print(f"✅ 所有訂單已取消")
        return True
        
    except Exception as e:
        print(f"❌ 取消失敗: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(
        description="Polymarket Limit Order Manager",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
範例:
  # 以 $0.50 買入 $10 USDC 的 Yes
  python limit_order.py place <ID> --outcome Yes --side BUY --price 0.50 --amount 10
  
  # 以 $0.60 賣出 5 shares 的 No
  python limit_order.py place <ID> --outcome No --side SELL --price 0.60 --size 5
  
  # 查看未成交訂單
  python limit_order.py list
  
  # 取消指定訂單
  python limit_order.py cancel <order_id>
  
  # 取消所有訂單
  python limit_order.py cancel-all
        """
    )
    
    subparsers = parser.add_subparsers(dest="command", help="指令")
    
    # Place order
    place_parser = subparsers.add_parser("place", help="掛 Limit Order")
    place_parser.add_argument("condition_id", help="市場 Condition ID")
    place_parser.add_argument("--outcome", "-o", required=True, help="Outcome (Yes/No)")
    place_parser.add_argument("--side", "-s", required=True, choices=["BUY", "SELL"], help="買/賣")
    place_parser.add_argument("--price", "-p", type=float, required=True, help="掛單價格 (0.01-0.99)")
    place_parser.add_argument("--size", type=float, help="股數 (SELL 用)")
    place_parser.add_argument("--amount", type=float, help="USDC 金額 (BUY 用)")
    place_parser.add_argument("--auto", "-y", action="store_true", help="自動確認")
    
    # List orders
    subparsers.add_parser("list", help="列出未成交訂單")
    
    # Cancel order
    cancel_parser = subparsers.add_parser("cancel", help="取消訂單")
    cancel_parser.add_argument("order_id", help="Order ID")
    
    # Cancel all
    subparsers.add_parser("cancel-all", help="取消所有訂單")
    
    args = parser.parse_args()
    
    if args.command == "place":
        place_limit_order(
            args.condition_id,
            args.outcome,
            args.side,
            args.price,
            size=args.size,
            amount=args.amount,
            auto_confirm=args.auto
        )
    elif args.command == "list":
        list_open_orders()
    elif args.command == "cancel":
        cancel_order(args.order_id)
    elif args.command == "cancel-all":
        cancel_all_orders()
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
