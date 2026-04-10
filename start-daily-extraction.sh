#!/bin/bash
# Daily extraction scheduler setup

# Usage:
#   ./start-daily-extraction.sh            # Run once now
#   ./start-daily-extraction.sh schedule   # Setup cron job
#   ./start-daily-extraction.sh check      # Check cron status
#   ./start-daily-extraction.sh stop       # Remove cron job

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
EXTRACT_SCRIPT="$SCRIPT_DIR/ingestion/daily_extract_schedule.py"
LOG_FILE="$SCRIPT_DIR/logs/daily_extract.log"
CRON_MARKER="AI_OPTIMIZER_DAILY_EXTRACT"

ensure_log_dir() {
    mkdir -p "$SCRIPT_DIR/logs"
}

run_extraction() {
    MODE="${1:-daily}"
    echo "==================================================================="
    echo "Running extraction: $(date) [Mode: $MODE]"
    echo "==================================================================="
    
    cd "$SCRIPT_DIR"
    
    # Ensure virtualenv is sourced if it exists
    if [ -f "venv/bin/activate" ]; then
        source venv/bin/activate
    fi
    
    EXTRACT_MODE="$MODE" python3 ingestion/daily_extract_schedule.py
    
    EXIT_CODE=$?
    
    if [ $EXIT_CODE -eq 0 ]; then
        echo "✅ Extraction completed ($MODE mode) at $(date)" >> "$LOG_FILE"
    else
        echo "❌ Extraction failed ($MODE mode, exit code: $EXIT_CODE) at $(date)" >> "$LOG_FILE"
    fi
    
    return $EXIT_CODE
}

setup_cron() {
    echo "Setting up cron jobs for daily and monthly extraction..."
    
    ensure_log_dir
    
    # Daily extraction at 23:00 (daily mode - yesterday only, fast)
    DAILY_CRON="0 23 * * * cd $SCRIPT_DIR && EXTRACT_MODE=daily python3 ingestion/daily_extract_schedule.py >> $LOG_FILE 2>&1"
    
    # Monthly full refresh on the 1st at 22:00 (full mode - all 30 days, comprehensive)
    MONTHLY_CRON="0 22 1 * * cd $SCRIPT_DIR && EXTRACT_MODE=full python3 ingestion/daily_extract_schedule.py >> $LOG_FILE 2>&1"
    
    CRON_MARKER_DAILY="AI_OPTIMIZER_DAILY_EXTRACT"
    CRON_MARKER_MONTHLY="AI_OPTIMIZER_MONTHLY_EXTRACT"
    
    # Remove old entries
    if crontab -l 2>/dev/null | grep -q "$CRON_MARKER_DAILY\|$CRON_MARKER_MONTHLY"; then
        echo "Removing old cron entries..."
        crontab -l 2>/dev/null | grep -v "$CRON_MARKER_DAILY" | grep -v "$CRON_MARKER_MONTHLY" | crontab -
    fi
    
    # Add new entries
    (crontab -l 2>/dev/null || true; echo "# $CRON_MARKER_DAILY") | crontab -
    (crontab -l 2>/dev/null || true; echo "$DAILY_CRON") | crontab -
    
    (crontab -l 2>/dev/null || true; echo "# $CRON_MARKER_MONTHLY") | crontab -
    (crontab -l 2>/dev/null || true; echo "$MONTHLY_CRON") | crontab -
    
    echo ""
    echo "✅ Cron jobs scheduled:"
    echo "   Daily:   23:00 every day (yesterday data, fast)"
    echo "   Monthly: 22:00 on the 1st (full 30 days, comprehensive)"
    echo ""
    echo "Current cron entries:"
    crontab -l | grep "AI_OPTIMIZER"
}

check_cron() {
    echo "Current cron jobs:"
    echo ""
    
    if crontab -l 2>/dev/null | grep -q "AI_OPTIMIZER"; then
        echo "✅ AI Optimizer extraction jobs are active:"
        echo ""
        crontab -l | grep "AI_OPTIMIZER" -A 1 | head -6
        echo ""
    else
        echo "❌ No AI Optimizer extraction cron jobs found"
        echo ""
        echo "To set up, run:"
        echo "  ./start-daily-extraction.sh schedule"
    fi
}

stop_cron() {
    echo "Removing cron jobs..."
    
    if crontab -l 2>/dev/null | grep -q "AI_OPTIMIZER"; then
        crontab -l 2>/dev/null | grep -v "AI_OPTIMIZER" | crontab -
        echo "✅ Cron jobs removed"
    else
        echo "No cron jobs found to remove"
    fi
}

# Main
case "${1:-run}" in
    run)
        ensure_log_dir
        MODE="${2:-daily}"
        run_extraction "$MODE"
        ;;
    schedule)
        setup_cron
        ;;
    check)
        check_cron
        ;;
    stop)
        stop_cron
        ;;
    *)
        echo "Usage: $0 {run|schedule|check|stop} [mode]"
        echo ""
        echo "  run [mode]  - Run extraction (mode: daily|full, default: daily)"
        echo "  schedule    - Setup daily cron job"
        echo "  check       - Show cron status"
        echo "  stop        - Remove cron job"
        echo ""
        echo "Examples:"
        echo "  ./start-daily-extraction.sh run daily      # Run yesterday update"
        echo "  ./start-daily-extraction.sh run full       # Run monthly refresh"
        echo "  ./start-daily-extraction.sh schedule       # Setup auto schedule"
        exit 1
        ;;
esac
