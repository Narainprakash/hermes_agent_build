"""
Shared Database Connection Pool for Benki Plugins
==================================================
Provides a single asyncpg connection pool that can be reused across
multiple plugins (risk-manager, db-client, etc.) to avoid creating
duplicate connections.
"""

import os
import asyncpg

# Global connection pool
_pool = None


async def get_pool():
    """
    Get or create the shared asyncpg connection pool.
    Returns None if BENKI_DB_URL is not configured.
    """
    global _pool
    
    if _pool is None:
        db_url = os.environ.get("BENKI_DB_URL", "")
        if not db_url:
            return None
        
        try:
            _pool = await asyncpg.create_pool(
                db_url,
                min_size=2,
                max_size=10,
                command_timeout=30,
                server_settings={'application_name': 'benki_shared_pool'}
            )
        except Exception as e:
            print(f"[db_pool] Failed to create pool: {e}")
            return None
    
    return _pool


async def close_pool():
    """Close the shared connection pool gracefully."""
    global _pool
    if _pool is not None:
        await _pool.close()
        _pool = None
