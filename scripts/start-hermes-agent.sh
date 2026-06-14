#!/usr/bin/env bash
###############################################################################
# Shared Benki Hermes agent startup
# - Prepares HERMES_HOME directory layout
# - Copies mounted config overlay into runtime data
# - Optionally resets cron next_run_at to a staggered startup time
###############################################################################
set -euo pipefail

source /opt/hermes/.venv/bin/activate

HERMES_HOME="${HERMES_HOME:-/opt/data}"
CONFIG_SOURCE="${HERMES_CONFIG_SOURCE:-/opt/config.yaml}"
CRON_STARTUP_DELAY_SECONDS="${HERMES_CRON_STARTUP_DELAY_SECONDS:-120}"

mkdir -p "${HERMES_HOME}"/{cron,sessions,logs,hooks,memories,skills,skins,plans,workspace,home}

if [ -f "${CONFIG_SOURCE}" ]; then
  cp "${CONFIG_SOURCE}" "${HERMES_HOME}/config.yaml"
fi

python3 - <<'PYEOF'
import json
import os
from datetime import datetime, timezone, timedelta

home = os.environ.get("HERMES_HOME", "/opt/data")
cron_file = os.path.join(home, "cron", "jobs.json")
delay = int(os.environ.get("HERMES_CRON_STARTUP_DELAY_SECONDS", "120"))

if os.path.exists(cron_file):
    with open(cron_file, encoding="utf-8") as f:
        data = json.load(f)

    trigger_at = (datetime.now(timezone.utc) + timedelta(seconds=delay)).strftime(
        "%Y-%m-%dT%H:%M:%S+00:00"
    )
    changed = 0
    for job in data.get("jobs", []):
        if job.get("enabled", True) and job.get("state") != "paused":
            job["next_run_at"] = trigger_at
            changed += 1

    with open(cron_file, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    print(f"[startup] Reset next_run_at for {changed} cron job(s) -> {trigger_at}")
else:
    print(f"[startup] No cron jobs file found at {cron_file}")
PYEOF

chown -R hermes:hermes "${HERMES_HOME}"
exec gosu hermes hermes gateway
