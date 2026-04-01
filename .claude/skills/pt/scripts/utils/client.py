#!/usr/bin/env python3
"""
Polymarket CLOB Client - Shared client initialization with multi-account support
"""

import os
from dotenv import load_dotenv

load_dotenv()

# API URLs
DATA_API = "https://data-api.polymarket.com"
GAMMA_API = "https://gamma-api.polymarket.com"
CLOB_API = "https://clob.polymarket.com"


def get_api_urls() -> dict:
    """獲取所有 API URLs"""
    return {
        "data": DATA_API,
        "gamma": GAMMA_API,
        "clob": CLOB_API
    }


def get_account_config(account_id: int = 1) -> dict:
    """
    獲取指定帳戶的配置
    
    Args:
        account_id: 帳戶編號 (1, 2, 3...)
    
    Returns:
        Dict with private_key, builder_wallet, wallet_address
    """
    # Account #1 uses the original env var names (backward compatible)
    if account_id == 1:
        private_key = os.getenv("POLYGON_PRIVATE_KEY")
        builder_wallet = os.getenv("BUILDER_WALLET_ADDRESS")
        wallet_address = os.getenv("WALLET_ADDRESS")
    else:
        # Account #2, #3... use numbered env vars
        private_key = os.getenv(f"POLYGON_PRIVATE_KEY_{account_id}")
        builder_wallet = os.getenv(f"BUILDER_WALLET_ADDRESS_{account_id}")
        wallet_address = os.getenv(f"WALLET_ADDRESS_{account_id}")
    
    if not private_key or not builder_wallet:
        raise ValueError(f"❌ Account #{account_id} not configured in .env")
    
    return {
        "account_id": account_id,
        "private_key": private_key,
        "builder_wallet": builder_wallet,
        "wallet_address": wallet_address or builder_wallet
    }


def get_available_accounts() -> list:
    """獲取所有已配置的帳戶"""
    accounts = []
    
    # Check account #1 (original)
    if os.getenv("POLYGON_PRIVATE_KEY") and os.getenv("BUILDER_WALLET_ADDRESS"):
        accounts.append(1)
    
    # Check numbered accounts
    for i in range(2, 10):  # Support up to 9 accounts
        if os.getenv(f"POLYGON_PRIVATE_KEY_{i}") and os.getenv(f"BUILDER_WALLET_ADDRESS_{i}"):
            accounts.append(i)
    
    return accounts


def get_client(with_creds: bool = True, account_id: int = 1):
    """
    初始化 CLOB Client
    
    Args:
        with_creds: 是否自動設定 API credentials (需要於交易時)
        account_id: 帳戶編號 (1, 2, 3...)
    
    Returns:
        ClobClient instance
    """
    from py_clob_client.client import ClobClient
    from py_clob_client.constants import POLYGON
    
    # Read-only mode (no private key needed)
    if not with_creds:
        client = ClobClient(CLOB_API, chain_id=POLYGON)
        return client
    
    # Trading mode (needs private key)
    config = get_account_config(account_id)
    
    client = ClobClient(
        CLOB_API,
        key=config["private_key"],
        chain_id=POLYGON,
        signature_type=1,  # Magic Link mode
        funder=config["builder_wallet"]
    )
    
    derived_creds = client.create_or_derive_api_creds()
    client.set_api_creds(derived_creds)
    
    return client


def get_wallets(account_id: int = 1) -> dict:
    """獲取指定帳戶的錢包地址"""
    config = get_account_config(account_id)
    return {
        "account_id": account_id,
        "control": config["wallet_address"],
        "builder": config["builder_wallet"]
    }
