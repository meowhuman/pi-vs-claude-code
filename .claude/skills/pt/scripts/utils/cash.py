#!/usr/bin/env python3
"""
Polymarket Cash Utils - Check USDC/MATIC balances on Polygon
"""

import os
import requests
from web3 import Web3
from .client import get_wallets

# USDC Contract on Polygon
USDC_ADDRESS = "0x2791Bca1f2de4661ED88A30C99A7a9449Aa84174"
USDC_ABI = [
    {
        "constant": True,
        "inputs": [{"name": "_owner", "type": "address"}],
        "name": "balanceOf",
        "outputs": [{"name": "balance", "type": "uint256"}],
        "type": "function",
    },
    {
        "constant": True,
        "inputs": [],
        "name": "decimals",
        "outputs": [{"name": "", "type": "uint8"}],
        "type": "function",
    },
]

def get_cash_balances(account_id: int = 1):
    """
    獲取錢包嘅 USDC 和 MATIC 餘額
    
    Args:
        account_id: 帳戶編號
    
    Returns:
        Dict of balances: {wallet_type: {usdc: float, matic: float, address: str}}
    """
    rpc_url = os.getenv("POLYGON_RPC_URL", "https://polygon-rpc.com")
    
    try:
        wallets = get_wallets(account_id)
    except ValueError as e:
        return {"error": str(e)}
    
    results = {}
    
    try:
        w3 = Web3(Web3.HTTPProvider(rpc_url))
        if not w3.is_connected():
            return {"error": "無法連接到 Polygon RPC"}
            
        usdc_contract = w3.eth.contract(
            address=Web3.to_checksum_address(USDC_ADDRESS), 
            abi=USDC_ABI
        )
        
        # Filter out account_id from wallets dict
        wallet_addrs = {k: v for k, v in wallets.items() if k != 'account_id'}
        
        for name, addr in wallet_addrs.items():
            if not addr:
                continue
                
            checksum_addr = Web3.to_checksum_address(addr)
            
            # MATIC
            matic_wei = w3.eth.get_balance(checksum_addr)
            matic = float(w3.from_wei(matic_wei, 'ether'))
            
            # USDC
            usdc_raw = usdc_contract.functions.balanceOf(checksum_addr).call()
            usdc = float(usdc_raw / 10**6)
            
            results[name] = {
                "usdc": round(usdc, 2),
                "matic": round(matic, 4),
                "address": addr
            }
            
        return results
    except Exception as e:
        return {"error": str(e)}
