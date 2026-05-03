"""
Benki EVM Client Plugin
========================
Polygon/EVM operations: token swaps, balance checks, transaction execution.
Uses Web3.py for on-chain interactions.
Supports DRY_RUN mode — simulates transactions without broadcasting.
"""

import os
import json

# Polygon token address map
POLYGON_TOKENS = {
    "MATIC": "0x0000000000000000000000000000000000001010",
    "WMATIC": "0x0d500B1d8E8eF31E21C99d1Db9A6444d3ADf1270",
    "USDC": "0x2791Bca1f2de4661ED88A30C99A7a9449Aa84174",
    "USDT": "0xc2132D05D31c914a87C6611C10748AEb04B58e8F",
    "WETH": "0x7ceB23fD6bC0adD59E62ac25578270cFf1b9f619",
    "WBTC": "0x1BFD67037B42Cf73acF2047067bd4F2C47D9BfD6",
    "LINK": "0x53E0bca35eC356BD5ddDFebbD1Fc0fD03FaBad39",
    "AAVE": "0xD6DF932A45C0f255f85145f286eA0b292B21C90B",
    "UNI": "0xb33EaAd8d922B1084f63203d4933b1E0d8d4A4e2",
    "CRV": "0x172370d5Cd63279eFa6d502DAB29171933a610AF",
}


def _resolve_address(token: str) -> str:
    """Resolve a token symbol to its Polygon contract address."""
    if token.startswith("0x") and len(token) == 42:
        return token  # Already an address
    return POLYGON_TOKENS.get(token.upper(), token)


def _get_config():
    """Get EVM configuration from environment."""
    return {
        "rpc_url": os.environ.get("POLYGON_RPC_URL", ""),
        "private_key": os.environ.get("EVM_PRIVATE_KEY", ""),
        "dry_run": os.environ.get("DRY_RUN", "true").lower() == "true",
    }


async def handle_evm_balance(params, **kwargs):
    """Check EVM wallet balance for a token."""
    config = _get_config()
    if not config["rpc_url"]:
        return json.dumps({"error": "POLYGON_RPC_URL not configured"})

    try:
        from web3 import Web3

        w3 = Web3(Web3.HTTPProvider(config["rpc_url"]))
        if not w3.is_connected():
            return json.dumps({"error": "Cannot connect to Polygon RPC"})

        account = w3.eth.account.from_key(config["private_key"])
        token_address = params.get("token_address", None)

        if token_address and token_address.lower() != "native":
            # ERC-20 balance
            erc20_abi = [{"constant": True, "inputs": [{"name": "_owner", "type": "address"}],
                          "name": "balanceOf", "outputs": [{"name": "balance", "type": "uint256"}],
                          "type": "function"},
                         {"constant": True, "inputs": [], "name": "decimals",
                          "outputs": [{"name": "", "type": "uint8"}], "type": "function"},
                         {"constant": True, "inputs": [], "name": "symbol",
                          "outputs": [{"name": "", "type": "string"}], "type": "function"}]
            contract = w3.eth.contract(
                address=Web3.to_checksum_address(token_address), abi=erc20_abi
            )
            raw_balance = contract.functions.balanceOf(account.address).call()
            decimals = contract.functions.decimals().call()
            symbol = contract.functions.symbol().call()
            balance = raw_balance / (10 ** decimals)
            return json.dumps({
                "wallet": account.address,
                "token": symbol,
                "balance": balance,
                "chain": "polygon"
            })
        else:
            # Native MATIC balance
            balance_wei = w3.eth.get_balance(account.address)
            balance = w3.from_wei(balance_wei, "ether")
            return json.dumps({
                "wallet": account.address,
                "token": "MATIC",
                "balance": float(balance),
                "chain": "polygon"
            })
    except ImportError:
        return json.dumps({"error": "web3 package not installed. Run: pip install web3"})
    except Exception as e:
        return json.dumps({"error": str(e)})


async def handle_evm_swap(params, **kwargs):
    """
    Execute a token swap on Polygon.
    In DRY_RUN mode, simulates the transaction without broadcasting.
    """
    config = _get_config()
    if not config["rpc_url"] or not config["private_key"]:
        return json.dumps({"error": "POLYGON_RPC_URL or EVM_PRIVATE_KEY not configured"})

    token_in = _resolve_address(params.get("token_in", ""))
    token_out = _resolve_address(params.get("token_out", ""))
    amount = float(params.get("amount", 0))
    slippage = float(params.get("slippage", 0.5))  # 0.5% default

    if config["dry_run"]:
        return json.dumps({
            "status": "dry_run",
            "message": f"DRY RUN: Would swap {amount} {token_in} → {token_out} on Polygon",
            "chain": "polygon",
            "token_in": token_in,
            "token_out": token_out,
            "amount": amount,
            "slippage": slippage,
            "tx_hash": "dry_run_no_tx",
            "note": "Set DRY_RUN=false in .env to enable live transactions"
        })

    try:
        from web3 import Web3

        w3 = Web3(Web3.HTTPProvider(config["rpc_url"]))
        account = w3.eth.account.from_key(config["private_key"])

        # In production, this would:
        # 1. Get quote from Uniswap V3 / Quickswap / 1inch
        # 2. Build the swap transaction
        # 3. Estimate gas
        # 4. Sign and broadcast
        # 5. Wait for confirmation

        # TODO: Implement actual swap via Uniswap V3 / Quickswap / 1inch
        # 1. Get quote from DEX router
        # 2. Build the swap transaction
        # 3. Estimate gas
        # 4. Sign and broadcast
        # 5. Wait for confirmation
        return json.dumps({
            "status": "failed",
            "message": f"Live EVM swap not yet implemented for {amount} {token_in} → {token_out} on Polygon",
            "chain": "polygon",
            "token_in": token_in,
            "token_out": token_out,
            "amount": amount,
            "wallet": account.address,
            "tx_hash": "",
            "error": "DEX router integration required. Do NOT record this as a successful trade."
        })
    except Exception as e:
        return json.dumps({"error": str(e), "status": "failed"})


def register(ctx):
    """Register EVM tools with Hermes."""

    ctx.register_tool("evm_balance", "benki_evm", {
        "name": "evm_balance",
        "description": "Check wallet balance for native MATIC or any ERC-20 token on Polygon.",
        "parameters": {
            "type": "object",
            "properties": {
                "token_address": {
                    "type": "string",
                    "description": "ERC-20 contract address, or 'native' for MATIC balance"
                }
            }
        }
    }, handle_evm_balance, is_async=True)

    ctx.register_tool("evm_swap", "benki_evm", {
        "name": "evm_swap",
        "description": (
            "Execute a token swap on Polygon. In DRY_RUN mode, simulates without broadcasting. "
            "IMPORTANT: Call risk_check BEFORE this tool."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "token_in": {"type": "string", "description": "Token to sell (symbol or address)"},
                "token_out": {"type": "string", "description": "Token to buy (symbol or address)"},
                "amount": {"type": "number", "description": "Amount of token_in to swap"},
                "slippage": {"type": "number", "description": "Max slippage % (default: 0.5)"}
            },
            "required": ["token_in", "token_out", "amount"]
        }
    }, handle_evm_swap, is_async=True)
