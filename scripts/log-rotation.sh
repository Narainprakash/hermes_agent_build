#!/bin/bash
# Log rotation script for Benki agents
# Cleans up old logs and compresses recent logs to save disk space

set -e

LOG_DIR="/opt/data/logs"
SESSION_DIR="/opt/data/sessions"
CRON_OUTPUT_DIR="/opt/data/cron/output"

# Retention periods (in days)
LOG_RETENTION_DAYS=7
SESSION_RETENTION_DAYS=30
CRON_OUTPUT_RETENTION_DAYS=14

echo "[$(date -u +"%Y-%m-%d %H:%M:%S UTC")] Starting log rotation..."

# Function to compress and rotate logs
rotate_logs() {
    local dir=$1
    local retention=$2
    local pattern=$3
    
    if [ ! -d "$dir" ]; then
        echo "  Directory $dir does not exist, skipping"
        return
    fi
    
    # Compress logs older than 1 day but newer than retention period
    find "$dir" -name "$pattern" -type f -mtime +1 -mtime -$retention ! -name "*.gz" -exec gzip {} \;
    
    # Delete compressed logs older than retention period
    find "$dir" -name "*.gz" -type f -mtime +$retention -delete
    
    # Delete uncompressed logs older than retention period
    find "$dir" -name "$pattern" -type f -mtime +$retention -delete
    
    echo "  Rotated logs in $dir (retention: ${retention} days)"
}

# Function to clean up old sessions
cleanup_sessions() {
    local dir=$1
    local retention=$2
    
    if [ ! -d "$dir" ]; then
        echo "  Directory $dir does not exist, skipping"
        return
    fi
    
    # Delete session files older than retention period
    find "$dir" -type f -mtime +$retention -delete
    
    # Remove empty session directories
    find "$dir" -type d -empty -delete 2>/dev/null || true
    
    echo "  Cleaned up sessions in $dir (retention: ${retention} days)"
}

# Rotate agent logs
echo "Rotating agent logs..."
rotate_logs "$LOG_DIR" $LOG_RETENTION_DAYS "*.log"

# Clean up old sessions
echo "Cleaning up old sessions..."
cleanup_sessions "$SESSION_DIR" $SESSION_RETENTION_DAYS

# Rotate cron output files
echo "Rotating cron output files..."
rotate_logs "$CRON_OUTPUT_DIR" $CRON_OUTPUT_RETENTION_DAYS "*.json"
rotate_logs "$CRON_OUTPUT_DIR" $CRON_OUTPUT_RETENTION_DAYS "*.md"

# Calculate disk usage
if command -v du &> /dev/null; then
    DISK_USAGE=$(du -sh /opt/data 2>/dev/null | cut -f1)
    echo "Current /opt/data disk usage: $DISK_USAGE"
fi

echo "[$(date -u +"%Y-%m-%d %H:%M:%S UTC")] Log rotation completed"
