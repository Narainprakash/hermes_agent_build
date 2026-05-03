"""
Benki Solana Client Plugin
===========================
Solana operations: token swaps via Jupiter aggregator, balance checks.
Supports DRY_RUN mode — simulates transactions without broadcasting.
"""

import os
import json

# Token mint address map for Jupiter swaps
SOLANA_TOKENS = {
    "SOL": "So11111111111111111111111111111111111111112",
    "USDC": "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v",
    "USDT": "Es9vMFrzaCERmJfrF4H2FYD4KCoNkY11McCe8BenwNYB",
    "BONK": "DezXAZ8z7PnrnRJjz3wXBoRgixCa6xjnB7YaB1pPB263",
    "WIF": "EKpQGSJtjMFqKZ9KQanSqYXRcF8fBopzLHYxdM65zcjm",
    "JTO": "jtojtomepa8beP8AuQc6eXt5FriJwfFMwQx2Hs2dhT9",
    "RNDR": "rndrizKT3MK1iimdmRd7VWZUVvXjMNZct8e34EZPge5",
    "INJ": "inj1q2f3...",  # Placeholder — update with real mint
}


def _resolve_mint(token: str) -> str:
    """Resolve a token symbol to its mint address."""
    if token.startswith("A") and len(token) >= 32:
        return token  # Already a mint address
    return SOLANA_TOKENS.get(token.upper(), token)


def _get_config():
    return {
        "rpc_url": os.environ.get("SOLANA_RPC_URL", ""),
        "private_key": os.environ.get("SOLANA_PRIVATE_KEY", ""),
        "dry_run": os.environ.get("DRY_RUN", "true").lower() == "true",
    }


async def handle_solana_balance(params, **kwargs):
    """Check Solana wallet balance (SOL or SPL token)."""
    config = _get_config()
    if not config["rpc_url"]:
        return json.dumps({"error": "SOLANA_RPC_URL not configured"})

    try:
        import aiohttp
        token_mint = params.get("token_mint", None)

        # Derive public key from private key
        from solders.keypair import Keypair
        keypair = Keypair.from_base58_string(config["private_key"])
        pubkey = str(keypair.pubkey())

        async with aiohttp.ClientSession() as session:
            if token_mint and token_mint.lower() != "native":
                # SPL Token balance via RPC
                payload = {
                    "jsonrpc": "2.0", "id": 1,
                    "method": "getTokenAccountsByOwner",
                    "params": [pubkey, {"mint": token_mint},
                               {"encoding": "jsonParsed"}]
                }
                async with session.post(config["rpc_url"], json=payload) as resp:
                    data = await resp.json()
                    accounts = data.get("result", {}).get("value", [])
                    if accounts:
                        info = accounts[0]["account"]["data"]["parsed"]["info"]
                        amount = info["tokenAmount"]["uiAmount"]
                        return json.dumps({
                            "wallet": pubkey, "token_mint": token_mint,
                            "balance": amount, "chain": "solana"
                        })
                    return json.dumps({
                        "wallet": pubkey, "token_mint": token_mint,
                        "balance": 0, "chain": "solana"
                    })
            else:
                # Native SOL balance
                payload = {
                    "jsonrpc": "2.0", "id": 1,
                    "method": "getBalance",
                    "params": [pubkey]
                }
                async with session.post(config["rpc_url"], json=payload) as resp:
                    data = await resp.json()
                    lamports = data.get("result", {}).get("value", 0)
                    sol = lamports / 1e9
                    return json.dumps({
                        "wallet": pubkey, "token": "SOL",
                        "balance": sol, "chain": "solana"
                    })
    except ImportError as e:
        return json.dumps({"error": f"Missing package: {e}. Run: pip install solders aiohttp"})
    except Exception as e:
        return json.dumps({"error": str(e)})


async def handle_solana_swap(params, **kwargs):
    """
    Execute a token swap on Solana via Jupiter aggregator.
    In DRY_RUN mode, gets a quote but doesn't broadcast.
    """
    config = _get_config()
    if not config["rpc_url"] or not config["private_key"]:
        return json.dumps({"error": "SOLANA_RPC_URL or SOLANA_PRIVATE_KEY not configured"})

    token_in = params.get("token_in", "")
    token_out = params.get("token_out", "")
    amount = float(params.get("amount", 0))
    slippage_bps = int(params.get("slippage_bps", 50))  # 50 bps = 0.5%

    if config["dry_run"]:
        # In dry-run, still fetch a real quote from Jupiter for price discovery
        try:
            import aiohttp
            async with aiohttp.ClientSession() as session:
                quote_url = (
                    f"https://quote-api.jup.ag/v6/quote"
                    f"?inputMint={token_in}&outputMint={token_out}"
                    f"&amount={int(amount * 1e6)}&slippageBps={slippage_bps}"
                )
                async with session.get(quote_url) as resp:
                    if resp.status == 200:
                        quote = await resp.json()
                        out_amount = int(quote.get("outAmount", 0)) / 1e6
                        price_impact = quote.get("priceImpactPct", "0")
                        try:
                            impact_pct = float(price_impact)
                        except (ValueError, TypeError):
                            impact_pct = 0.0

                        # H5: Warn on high slippage
                        slippage_warning = ""
                        if impact_pct > 1.0:
                            slippage_warning = (
                                f"⚠️ HIGH SLIPPAGE: {impact_pct:.2f}% price impact. "
                                f"Consider reducing position size or using a more liquid pair."
                            )
                        elif impact_pct > 0.5:
                            slippage_warning = (
                                f"⚡ Moderate slippage: {impact_pct:.2f}% price impact."
                            )

                        return json.dumps({
                            "status": "dry_run",
                            "message": f"DRY RUN: Would swap {amount} → {out_amount} via Jupiter",
                            "chain": "solana",
                            "token_in": token_in,
                            "token_out": token_out,
                            "amount_in": amount,
                            "amount_out": out_amount,
                            "price_impact_pct": impact_pct,
                            "slippage_warning": slippage_warning,
                            "route": quote.get("routePlan", []),
                            "tx_hash": "dry_run_no_tx"
                        })
                    else:
                        return json.dumps({
                            "status": "dry_run",
                            "message": f"DRY RUN: Would swap {amount} {token_in} → {token_out}",
                            "error": f"Jupiter API returned {resp.status}",
                            "tx_hash": "dry_run_no_tx"
                        })
        except Exception as e:
            return json.dumps({
                "status": "dry_run",
                "message": f"DRY RUN: Would swap {amount} {token_in} → {token_out}",
                "quote_error": str(e),
                "tx_hash": "dry_run_no_tx"
            })

    # LIVE execution placeholder
    return json.dumps({
        "status": "error",
        "message": "Live Solana swap execution requires Jupiter SDK integration",
        "note": "Implement swap transaction building, signing, and broadcast"
    })


def register(ctx):
    """Register Solana tools with Hermes."""

    ctx.register_tool("solana_balance", "benki_solana", {
        "name": "solana_balance",
        "description": "Check Solana wallet balance for native SOL or any SPL token.",
        "parameters": {
            "type": "object",
            "properties": {
                "token_mint": {
                    "type": "string",
                    "description": "SPL token mint address, or 'native' for SOL balance"
                }
            }
        }
    }, handle_solana_balance, is_async=True)

    ctx.register_tool("solana_swap", "benki_solana", {
        "name": "solana_swap",
        "description": (
            "Execute a token swap on Solana via Jupiter aggregator. "
            "In DRY_RUN mode, fetches a real quote but doesn't broadcast. "
            "IMPORTANT: Call risk_check BEFORE this tool."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "token_in": {"type": "string", "description": "Input token mint address"},
                "token_out": {"type": "string", "description": "Output token mint address"},
                "amount": {"type": "number", "description": "Amount of token_in to swap (in token units)"},
                "slippage_bps": {"type": "integer", "description": "Max slippage in basis points (default: 50 = 0.5%)"}
            },
            "required": ["token_in", "token_out", "amount"]
        }
    }, handle_solana_swap, is_async=True)
