#!/usr/bin/env python3
"""
Python client for Polymarket Builder Signing Server
"""
import requests
import json
from typing import Dict, Any

class BuilderSigningClient:
    def __init__(self, server_url: str = "http://localhost:5001"):
        self.server_url = server_url.rstrip('/')

    def sign_order(self, order_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Send order to signing server for signature

        Args:
            order_data: Order data to be signed

        Returns:
            Signed order data
        """
        try:
            response = requests.post(
                f"{self.server_url}/sign",
                headers={"Content-Type": "application/json"},
                json=order_data,
                timeout=30
            )

            if response.status_code == 200:
                return response.json()
            else:
                print(f"❌ Signing server error: {response.status_code}")
                print(f"Response: {response.text}")
                return None

        except Exception as e:
            print(f"❌ Error communicating with signing server: {e}")
            return None

    def test_connection(self) -> bool:
        """Test connection to signing server"""
        try:
            response = requests.get(f"{self.server_url}/health", timeout=5)
            return response.status_code == 200
        except:
            return False

# Example usage
if __name__ == "__main__":
    client = BuilderSigningClient()

    if client.test_connection():
        print("✅ Connected to signing server")
    else:
        print("❌ Cannot connect to signing server")