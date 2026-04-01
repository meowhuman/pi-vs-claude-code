#!/usr/bin/env python3
"""
Polymarket Wallet Connection Test
測試 Polymarket 錢包連線和 API 環境是否正常

Usage (從 pt/ 根目錄執行):
    source venv/bin/activate
    python test/scripts/test_wallet_connection.py
    python test/scripts/test_wallet_connection.py --account 2
    python test/scripts/test_wallet_connection.py --public-only
"""

import sys
import os
import argparse
# 確保可以 import 父目錄的 utils
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))

from dotenv import load_dotenv
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), "../../.env"))


PASS = "✅"
FAIL = "❌"
INFO = "ℹ️ "

results = []


def check(label: str, passed: bool, detail: str = ""):
    symbol = PASS if passed else FAIL
    msg = f"{symbol} {label}"
    if detail:
        msg += f" — {detail}"
    print(msg)
    results.append({"label": label, "passed": passed, "detail": detail})
    return passed


def test_env_vars(account_id: int = 1):
    print(f"\n── ENV VARS (Account #{account_id}) ──")

    if account_id == 1:
        pk = os.getenv("POLYGON_PRIVATE_KEY")
        bw = os.getenv("BUILDER_WALLET_ADDRESS")
        wa = os.getenv("WALLET_ADDRESS")
    else:
        pk = os.getenv(f"POLYGON_PRIVATE_KEY_{account_id}")
        bw = os.getenv(f"BUILDER_WALLET_ADDRESS_{account_id}")
        wa = os.getenv(f"WALLET_ADDRESS_{account_id}")

    pk_ok = check(
        "POLYGON_PRIVATE_KEY",
        bool(pk),
        f"{'set (' + str(len(pk)) + ' chars)' if pk else 'NOT SET'}"
    )
    bw_ok = check(
        "BUILDER_WALLET_ADDRESS",
        bool(bw),
        f"{bw[:10] + '...' if bw else 'NOT SET'}"
    )
    check(
        "WALLET_ADDRESS",
        bool(wa),
        f"{wa[:10] + '...' if wa else 'not set (will use BUILDER_WALLET_ADDRESS)'}"
    )

    return pk_ok and bw_ok


def test_public_api():
    print("\n── PUBLIC API ──")
    import requests

    CLOB_API = "https://clob.polymarket.com"
    GAMMA_API = "https://gamma-api.polymarket.com"

    # Test CLOB API
    try:
        r = requests.get(f"{CLOB_API}/ok", timeout=10)
        check("CLOB API /ok", r.status_code == 200, f"status={r.status_code}")
    except Exception as e:
        check("CLOB API /ok", False, str(e))

    # Test Gamma API
    try:
        r = requests.get(f"{GAMMA_API}/markets?limit=1", timeout=10)
        check("Gamma API /markets", r.status_code == 200, f"status={r.status_code}")
    except Exception as e:
        check("Gamma API /markets", False, str(e))


def test_wallet_auth(account_id: int = 1):
    print(f"\n── WALLET AUTH (Account #{account_id}) ──")

    try:
        from scripts.utils.client import get_client, get_account_config
    except ImportError as e:
        check("Import utils.client", False, str(e))
        return False

    check("Import utils.client", True)

    try:
        config = get_account_config(account_id)
        check(
            "Account config loaded",
            True,
            f"builder={config['builder_wallet'][:10]}..."
        )
    except Exception as e:
        check("Account config loaded", False, str(e))
        return False

    # Test client init (with creds)
    try:
        client = get_client(with_creds=True, account_id=account_id)
        check("ClobClient init", True, "credentials derived")
    except Exception as e:
        check("ClobClient init", False, str(e))
        return False

    # Test fetching open orders (simple authenticated call)
    try:
        orders = client.get_orders()
        order_count = len(orders) if orders else 0
        check(
            "Authenticated API call (get_orders)",
            True,
            f"open orders: {order_count}"
        )
    except Exception as e:
        check("Authenticated API call (get_orders)", False, str(e))

    return True


def test_balance(account_id: int = 1):
    print(f"\n── BALANCE (Account #{account_id}) ──")

    try:
        from scripts.utils.client import get_client
        from py_clob_client.clob_types import AssetType, BalanceAllowanceParams
        client = get_client(with_creds=True, account_id=account_id)
        result = client.get_balance_allowance(params=BalanceAllowanceParams(asset_type=AssetType.COLLATERAL))
        balance = result.get("balance", "unknown") if isinstance(result, dict) else str(result)
        check("USDC Balance", True, f"raw balance: {balance}")
    except Exception as e:
        check("USDC Balance", False, str(e))


def print_summary():
    passed = sum(1 for r in results if r["passed"])
    total = len(results)
    failed = [r for r in results if not r["passed"]]

    print(f"\n{'='*50}")
    print(f"RESULT: {passed}/{total} passed")

    if failed:
        print("\nFailed checks:")
        for r in failed:
            print(f"  {FAIL} {r['label']}: {r['detail']}")
        return False
    else:
        print(f"{PASS} All checks passed — wallet connection is working!")
        return True


def main():
    parser = argparse.ArgumentParser(description="Test Polymarket wallet connection")
    parser.add_argument("--account", type=int, default=1, help="Account number (default: 1)")
    parser.add_argument("--all-accounts", action="store_true", help="Test all configured accounts")
    parser.add_argument("--public-only", action="store_true", help="Only test public API (no credentials)")
    args = parser.parse_args()

    print("=" * 50)
    print("Polymarket Connection Test")
    print("=" * 50)

    if args.public_only:
        test_public_api()
    elif args.all_accounts:
        try:
            from scripts.utils.client import get_available_accounts
            accounts = get_available_accounts()
            print(f"{INFO} Found accounts: {accounts}")
            test_public_api()
            for acc in accounts:
                env_ok = test_env_vars(acc)
                if env_ok:
                    test_wallet_auth(acc)
                    test_balance(acc)
        except ImportError:
            print(f"{FAIL} Cannot import utils.client — run from pt/ root directory")
    else:
        env_ok = test_env_vars(args.account)
        test_public_api()
        if env_ok:
            test_wallet_auth(args.account)
            test_balance(args.account)

    ok = print_summary()
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
