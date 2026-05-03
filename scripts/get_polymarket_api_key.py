"""
Generate Polymarket CLOB API Credentials (L2 Authentication)
============================================================

Polymarket uses a two-level auth system:
  L1: Your wallet private key (proves ownership via EIP-712 signature)
  L2: API credentials (apiKey, secret, passphrase) — used for trading

This script derives L2 credentials from your L1 private key.
You only need to run this ONCE. The credentials are persistent per wallet.

Prerequisites:
  pip install py-clob-client web3

Usage:
  python scripts/get_polymarket_api_key.py
"""

import os
import sys

# ── Configuration ──
POLYGON_RPC = "https://polygon-rpc.com"
CLOB_HOST = "https://clob.polymarket.com"
CHAIN_ID = 137  # Polygon mainnet


def main():
    private_key = os.environ.get("EVM_PRIVATE_KEY", "").strip()
    if not private_key:
        print("ERROR: Set EVM_PRIVATE_KEY environment variable first.")
        print("Example: $env:EVM_PRIVATE_KEY='0x...'")
        sys.exit(1)

    try:
        from py_clob_client.client import ClobClient
    except ImportError:
        print("ERROR: py-clob-client not installed.")
        print("Run: pip install py-clob-client")
        sys.exit(1)

    print("Connecting to Polymarket CLOB...")
    client = ClobClient(
        host=CLOB_HOST,
        key=private_key,
        chain_id=CHAIN_ID,
    )

    print("Deriving API credentials (L1 → L2 auth)...")
    creds = None
    try:
        # Try v2 API first
        creds = client.create_or_derive_api_key()
    except AttributeError:
        # Fall back to v1 API — try all possible method names
        print("  (v1 client detected — trying fallback methods)")
        for method_name in ["create_or_derive_api_creds", "create_api_key", "derive_api_key"]:
            try:
                method = getattr(client, method_name)
                creds = method()
                print(f"  ✓ Success with: {method_name}()")
                break
            except Exception as e:
                print(f"  ✗ {method_name}() failed: {str(e)[:80]}")
                continue
    except Exception as e:
        print(f"ERROR: {e}")
        print("\nCommon causes:")
        print("  - Wallet has no POL for gas (need ~0.01 POL on Polygon)")
        print("  - Private key is malformed (must start with 0x)")
        print("  - Wallet not registered on Polymarket (deposit first)")
        print("  - py-clob-client version mismatch (try: pip install py-clob-client --upgrade)")
        sys.exit(1)

    if creds is None:
        print("\n" + "=" * 60)
        print("FAILED: Could not create or derive API credentials")
        print("=" * 60)
        print("\nThis almost certainly means your wallet has NEVER")
        print("interacted with Polymarket. You MUST deposit first.")
        print("\nSteps to fix:")
        print("  1. Go to https://polymarket.com")
        print("  2. Connect your wallet (same address as EVM_PRIVATE_KEY)")
        print("  3. Deposit at least $1 (or any amount) into Polymarket")
        print("  4. This deploys your proxy wallet + registers you on CLOB")
        print("  5. Re-run this script after deposit confirms (~2-5 min)")
        print("\nAlternative: Try upgrading to v2 client:")
        print("  pip uninstall py-clob-client")
        print("  pip install py-clob-client-v2")
        sys.exit(1)

    print("\n" + "=" * 60)
    print("SUCCESS — Add these to configs/predictor/.env:")
    print("=" * 60)
    print(f'POLYMARKET_API_KEY={creds["apiKey"]}')
    print(f'POLYMARKET_SECRET={creds["secret"]}')
    print(f'POLYMARKET_PASSPHRASE={creds["passphrase"]}')
    print("=" * 60)
    print("\nIMPORTANT:")
    print("  - These credentials are tied to your wallet forever.")
    print("  - Store them securely. Never commit them to git.")
    print("  - If you lose them, re-run this script to derive again.")


if __name__ == "__main__":
    main()
