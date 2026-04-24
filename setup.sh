#!/bin/bash
###############################################################################
# Benki Multi-Agent System — Setup Script
# Run this ONCE to initialize the Docker environment and prepare for launch.
###############################################################################
set -e

echo "═══════════════════════════════════════════════════════════════"
echo "  Benki Multi-Agent Crypto System — Setup"
echo "═══════════════════════════════════════════════════════════════"

# ── Pre-flight checks ───────────────────────────────────────────────
echo ""
echo "▸ Checking Docker..."
if ! command -v docker &> /dev/null; then
    echo "  ✗ Docker not found. Install Docker Desktop first."
    exit 1
fi
echo "  ✓ Docker found"

if ! docker compose version &> /dev/null; then
    echo "  ✗ Docker Compose not found."
    exit 1
fi
echo "  ✓ Docker Compose found"

# ── Check .env files ────────────────────────────────────────────────
echo ""
echo "▸ Checking configuration files..."

check_placeholder() {
    local file=$1
    if grep -q "PASTE_" "$file" 2>/dev/null; then
        echo "  ⚠ $file contains PASTE_ placeholders — fill these in before launching!"
        return 1
    fi
    return 0
}

HAS_PLACEHOLDERS=0
check_placeholder ".env" || HAS_PLACEHOLDERS=1
check_placeholder "configs/main/.env" || HAS_PLACEHOLDERS=1
check_placeholder "configs/trader/.env" || HAS_PLACEHOLDERS=1
check_placeholder "configs/predictor/.env" || HAS_PLACEHOLDERS=1
check_placeholder "configs/main/config.yaml" || HAS_PLACEHOLDERS=1
check_placeholder "configs/trader/config.yaml" || HAS_PLACEHOLDERS=1
check_placeholder "configs/predictor/config.yaml" || HAS_PLACEHOLDERS=1

if [ $HAS_PLACEHOLDERS -eq 1 ]; then
    echo ""
    echo "  ╔═══════════════════════════════════════════════════════════╗"
    echo "  ║  ACTION REQUIRED: Replace all PASTE_ values in .env     ║"
    echo "  ║  and config.yaml files before running docker compose up  ║"
    echo "  ╚═══════════════════════════════════════════════════════════╝"
    echo ""
    echo "  Files to edit:"
    echo "    1. .env                    → POSTGRES_PASSWORD"
    echo "    2. configs/main/.env       → Discord token, Minimax key, DB password"
    echo "    3. configs/trader/.env     → Discord token, OpenRouter key, wallet keys"
    echo "    4. configs/predictor/.env  → Discord token, OpenRouter key, wallet keys"
    echo "    5. configs/*/config.yaml   → Discord channel IDs"
fi

# ── Pull images ─────────────────────────────────────────────────────
echo ""
echo "▸ Pulling Docker images..."
docker compose pull
echo "  ✓ Images pulled"

# ── Start PostgreSQL first ──────────────────────────────────────────
echo ""
echo "▸ Starting PostgreSQL..."
docker compose up -d postgres
echo "  Waiting for PostgreSQL to be healthy..."
sleep 5

# Wait for health check
for i in {1..30}; do
    if docker compose ps postgres | grep -q "healthy"; then
        echo "  ✓ PostgreSQL is healthy"
        break
    fi
    if [ $i -eq 30 ]; then
        echo "  ✗ PostgreSQL health check timed out"
        exit 1
    fi
    sleep 2
done

# ── Verify database schema ─────────────────────────────────────────
echo ""
echo "▸ Verifying database schema..."
TABLES=$(docker compose exec -T postgres psql -U benki -d benki -t -c "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = 'public'")
TABLES=$(echo $TABLES | xargs)  # trim whitespace
echo "  ✓ Found $TABLES tables in benki database"

# ── Initial LLM configuration ──────────────────────────────────────
echo ""
echo "═══════════════════════════════════════════════════════════════"
echo "  One-Time Interactive Setup"
echo "═══════════════════════════════════════════════════════════════"

if [ $HAS_PLACEHOLDERS -eq 0 ]; then
    echo ""
    echo "▸ Configure LLM for each agent (interactive):"
    echo "  Run these commands one at a time:"
    echo ""
    echo "    docker compose run --rm benki-main model"
    echo "    docker compose run --rm benki-trader model"
    echo "    docker compose run --rm benki-predictor model"
    echo ""
    echo "  After configuring LLMs, launch all agents with:"
    echo ""
    echo "    docker compose up -d"
    echo ""
    echo "  Monitor logs with:"
    echo ""
    echo "    docker compose logs -f benki-main"
    echo "    docker compose logs -f benki-trader"
    echo "    docker compose logs -f benki-predictor"
else
    echo ""
    echo "  ⚠ Fill in the PASTE_ placeholders first, then re-run this script."
fi

echo ""
echo "═══════════════════════════════════════════════════════════════"
echo "  Setup complete!"
echo "═══════════════════════════════════════════════════════════════"
