"""
Benki Robinhood MCP Client Plugin
=================================
Adapter tool surface for Robinhood MCP agentic account operations.
Uses DRY_RUN mode by default and expects the actual Robinhood MCP server/account
binding to be configured outside this repository.
"""

import json
import os
from datetime import datetime, timezone


def _get_config():
    return {
        "account_id": os.environ.get("ROBINHOOD_ACCOUNT_ID", ""),
        "mcp_server": os.environ.get("ROBINHOOD_MCP_SERVER", "robinhood"),
        "dry_run": os.environ.get("DRY_RUN", "true").lower() == "true",
    }


async def handle_robinhood_mcp_account(params, **kwargs):
    """Return configured Robinhood MCP account context."""
    config = _get_config()
    return json.dumps({
        "platform": "robinhood_mcp",
        "account_id": config["account_id"] or "default",
        "mcp_server": config["mcp_server"],
        "dry_run": config["dry_run"],
        "fetched_at": datetime.now(timezone.utc).isoformat(),
        "note": "Use the configured Robinhood MCP server for live balances/positions.",
    })


async def handle_robinhood_mcp_positions(params, **kwargs):
    """Placeholder position query for Robinhood MCP account positions."""
    config = _get_config()
    return json.dumps({
        "platform": "robinhood_mcp",
        "account_id": config["account_id"] or "default",
        "positions": [],
        "status": "dry_run" if config["dry_run"] else "mcp_required",
        "note": "Live positions should be retrieved by the Robinhood MCP server binding.",
    })


async def handle_robinhood_mcp_order(params, **kwargs):
    """Submit or simulate a Robinhood MCP order. Call risk_check first."""
    config = _get_config()
    symbol = params.get("symbol") or params.get("asset", "")
    action = params.get("action", "buy").lower()
    amount = float(params.get("amount", 0))
    order_type = params.get("order_type", "market")
    quantity = params.get("quantity")

    if config["dry_run"]:
        return json.dumps({
            "status": "dry_run",
            "message": f"DRY RUN: Would {action} {symbol} via Robinhood MCP",
            "platform": "robinhood_mcp",
            "venue": "robinhood_mcp",
            "asset": symbol,
            "action": action,
            "amount": amount,
            "quantity": quantity,
            "order_type": order_type,
            "tx_hash": "dry_run_no_tx",
        })

    return json.dumps({
        "status": "mcp_required",
        "platform": "robinhood_mcp",
        "venue": "robinhood_mcp",
        "asset": symbol,
        "action": action,
        "amount": amount,
        "quantity": quantity,
        "order_type": order_type,
        "error": "Live Robinhood execution must be routed through the configured MCP server.",
    })


def register(ctx):
    """Register Robinhood MCP adapter tools with Hermes."""

    ctx.register_tool("robinhood_mcp_account", "benki_robinhood", {
        "name": "robinhood_mcp_account",
        "description": "Return configured Robinhood MCP account context.",
        "parameters": {"type": "object", "properties": {}},
    }, handle_robinhood_mcp_account, is_async=True)

    ctx.register_tool("robinhood_mcp_positions", "benki_robinhood", {
        "name": "robinhood_mcp_positions",
        "description": "Retrieve or represent Robinhood MCP account positions.",
        "parameters": {"type": "object", "properties": {}},
    }, handle_robinhood_mcp_positions, is_async=True)

    ctx.register_tool("robinhood_mcp_order", "benki_robinhood", {
        "name": "robinhood_mcp_order",
        "description": "Place or simulate a Robinhood MCP order. IMPORTANT: Call risk_check first.",
        "parameters": {
            "type": "object",
            "properties": {
                "symbol": {"type": "string", "description": "Robinhood tradable symbol"},
                "asset": {"type": "string", "description": "Alias for symbol"},
                "action": {"type": "string", "description": "buy or sell"},
                "amount": {"type": "number", "description": "Dollar amount"},
                "quantity": {"type": "number", "description": "Optional share/contract quantity"},
                "order_type": {"type": "string", "description": "market or limit"},
                "limit_price": {"type": "number", "description": "Optional limit price"},
            },
            "required": ["action", "amount"],
        },
    }, handle_robinhood_mcp_order, is_async=True)
