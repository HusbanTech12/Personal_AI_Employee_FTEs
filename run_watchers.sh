#!/bin/bash
#
# AI Employee Vault - External Watchers Startup Script (Gold Tier)
#
# Starts all external watcher agents with graceful degradation:
# - If one watcher fails, system continues running others
# - Failed watchers marked OFFLINE
# - Centralized management via watcher_manager.py
#
# Watchers:
# - gmail_watcher.py (Email monitoring)
# - whatsapp_watcher.py (Message monitoring)
# - linkedin_watcher.py (Professional network monitoring)
# - filesystem_watcher.py (Inbox file monitoring)
#
# Usage: bash run_watchers.sh
# Stop:  Press Ctrl+C to gracefully shutdown all watchers
#

# =============================================================================
# Configuration
# =============================================================================

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_DIR="$SCRIPT_DIR/venv"
LOGS_DIR="$SCRIPT_DIR/Logs"
WATCHERS_DIR="$SCRIPT_DIR/Watchers"
WATCHERS_LOG="$LOGS_DIR/watchers.log"
WATCHER_MANAGER="$SCRIPT_DIR/watcher_manager.py"

# =============================================================================
# Colors for Output
# =============================================================================

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
MAGENTA='\033[0;35m'
NC='\033[0m' # No Color

# =============================================================================
# Logging Functions
# =============================================================================

log() {
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    echo -e "[$timestamp] $1" | tee -a "$WATCHERS_LOG"
}

log_info() {
    log "${BLUE}[INFO]${NC} $1"
}

log_success() {
    log "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    log "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    log "${RED}[ERROR]${NC} $1"
}

log_watcher() {
    log "${CYAN}[WATCHER]${NC} $1"
}

log_gold() {
    log "${MAGENTA}[GOLD TIER]${NC} $1"
}

# =============================================================================
# Cleanup and Shutdown Handlers
# =============================================================================

cleanup() {
    echo ""
    log_info "Initiating graceful shutdown..."

    # Kill the watcher manager process if running
    if [ -n "$MANAGER_PID" ] && kill -0 "$MANAGER_PID" 2>/dev/null; then
        kill -TERM "$MANAGER_PID" 2>/dev/null || true
        wait "$MANAGER_PID" 2>/dev/null || true
    fi

    log_success "All watchers stopped. Goodbye!"
    exit 0
}

# Trap Ctrl+C and termination signals
trap cleanup SIGINT SIGTERM

# =============================================================================
# Pre-flight Checks
# =============================================================================

check_prerequisites() {
    log_info "Running pre-flight checks..."

    # Check Python
    if command -v python3 &> /dev/null; then
        PYTHON_CMD="python3"
    elif command -v python &> /dev/null; then
        PYTHON_CMD="python"
    else
        log_error "Python not found. Please install Python 3.8+"
        exit 1
    fi

    log_success "Python found: $($PYTHON_CMD --version)"

    # Check watcher manager script exists
    if [ ! -f "$WATCHER_MANAGER" ]; then
        log_error "Watcher manager not found: $WATCHER_MANAGER"
        exit 1
    fi
    log_success "Watcher manager found"

    # Check individual watcher scripts (warn if missing, but continue)
    local missing_watchers=0
    for script in "$WATCHERS_DIR/gmail_watcher.py" "$WATCHERS_DIR/whatsapp_watcher.py" "$WATCHERS_DIR/linkedin_watcher.py" "$SCRIPT_DIR/filesystem_watcher.py"; do
        if [ ! -f "$script" ]; then
            log_warning "Watcher script not found (will be marked OFFLINE): $script"
            ((missing_watchers++))
        fi
    done

    if [ $missing_watchers -gt 0 ]; then
        log_warning "$missing_watchers watcher(s) missing - system will run in degraded mode"
    else
        log_success "All watcher scripts found"
    fi

    # Check WhatsApp watcher dependencies
    if [ -f "$WATCHERS_DIR/whatsapp_watcher.py" ]; then
        source "$VENV_DIR/bin/activate" 2>/dev/null || true
        if ! python -c "import flask" 2>/dev/null; then
            log_warning "Flask not installed - required for WhatsApp webhook server"
            log_info "Install with: pip install flask"
        fi
        if ! python -c "import twilio" 2>/dev/null; then
            log_info "Twilio package not installed - WhatsApp will run in demo mode"
            log_info "Install with: pip install twilio (optional for production)"
        fi
        deactivate 2>/dev/null || true
    fi

    # Ensure logs directory exists
    mkdir -p "$LOGS_DIR"
    mkdir -p "$WATCHERS_DIR"
    log_success "Directories verified"
}

# =============================================================================
# Watcher Manager Startup (Gold Tier Resilience)
# =============================================================================

start_watcher_manager() {
    log_gold "Starting Watcher Manager with Gold Tier resilience..."
    log_info "Features:"
    log_info "  - Graceful degradation on watcher failure"
    log_info "  - Failed watchers marked OFFLINE"
    log_info "  - Other watchers continue running"
    log_info "  - Centralized status tracking"
    echo ""

    # Activate virtual environment if it exists
    if [ -f "$VENV_DIR/bin/activate" ]; then
        source "$VENV_DIR/bin/activate" 2>/dev/null || true
        log_info "Virtual environment activated"
    fi

    # Start the watcher manager
    log_watcher "Launching watcher_manager.py..."
    python "$WATCHER_MANAGER" >> "$WATCHERS_LOG" 2>&1 &
    MANAGER_PID=$!

    # Deactivate virtual environment
    deactivate 2>/dev/null || true

    sleep 3

    # Check if manager started successfully
    if kill -0 "$MANAGER_PID" 2>/dev/null; then
        log_success "Watcher Manager started (PID: $MANAGER_PID)"
        return 0
    else
        log_error "Failed to start Watcher Manager"
        return 1
    fi
}

# =============================================================================
# Legacy Mode: Individual Watcher Startup with Try/Except
# =============================================================================
# Use this mode if you want to run watchers individually without the manager
# This provides maximum control and isolation

# Track individual watcher PIDs
GMAIL_PID=""
WHATSAPP_PID=""
LINKEDIN_PID=""
FILESYSTEM_PID=""

# Track watcher status
declare -A WATCHER_STATUS
declare -A WATCHER_ERRORS

start_watcher_with_protection() {
    local watcher_name="$1"
    local watcher_script="$2"
    local pid_var="$3"

    log_watcher "Starting $watcher_name with protection..."

    # Check if script exists
    if [ ! -f "$watcher_script" ]; then
        log_error "[$watcher_name] Script not found: $watcher_script"
        WATCHER_STATUS["$watcher_name"]="OFFLINE"
        WATCHER_ERRORS["$watcher_name"]="Script not found"
        return 1
    fi

    # Try to start the watcher (wrapped in error handling)
    if [ -f "$VENV_DIR/bin/activate" ]; then
        source "$VENV_DIR/bin/activate" 2>/dev/null || true
    fi

    local log_file="$LOGS_DIR/${watcher_name,,}_watcher.log"
    python "$watcher_script" >> "$log_file" 2>&1 &
    local pid=$!

    deactivate 2>/dev/null || true

    sleep 2

    # Check if process is running
    if kill -0 "$pid" 2>/dev/null; then
        log_success "[$watcher_name] Started successfully (PID: $pid)"
        WATCHER_STATUS["$watcher_name"]="ACTIVE"
        WATCHER_ERRORS["$watcher_name"]=""
        eval "$pid_var=$pid"
        return 0
    else
        log_error "[$watcher_name] Failed to start - process exited immediately"
        WATCHER_STATUS["$watcher_name"]="OFFLINE"
        WATCHER_ERRORS["$watcher_name"]="Process exited immediately"
        return 1
    fi
}

start_all_watchers_legacy() {
    log_gold "Starting watchers in LEGACY mode (individual protection)..."
    echo ""

    # Initialize status tracking
    WATCHER_STATUS=()
    WATCHER_ERRORS=()

    # Start each watcher with individual protection
    # Failure of one does NOT affect others

    log_info "Starting Gmail watcher..."
    start_watcher_with_protection "Gmail" "$WATCHERS_DIR/gmail_watcher.py" "GMAIL_PID" || true

    log_info "Starting WhatsApp watcher..."
    start_watcher_with_protection "WhatsApp" "$WATCHERS_DIR/whatsapp_watcher.py" "WHATSAPP_PID" || true

    log_info "Starting LinkedIn watcher..."
    start_watcher_with_protection "LinkedIn" "$WATCHERS_DIR/linkedin_watcher.py" "LINKEDIN_PID" || true

    log_info "Starting Filesystem watcher..."
    start_watcher_with_protection "Filesystem" "$SCRIPT_DIR/filesystem_watcher.py" "FILESYSTEM_PID" || true

    echo ""

    # Show status summary
    show_legacy_status
}

show_legacy_status() {
    echo ""
    log_success "============================================"
    log_success "  External Watchers - Status (Legacy Mode)"
    log_success "============================================"
    log_success ""

    local active_count=0
    local offline_count=0

    for watcher in "Gmail" "WhatsApp" "LinkedIn" "Filesystem"; do
        local status="${WATCHER_STATUS[$watcher]:-OFFLINE}"
        local error="${WATCHER_ERRORS[$watcher]:-}"
        local icon="✗"

        if [ "$status" = "ACTIVE" ]; then
            icon="✓"
            ((active_count++))
        else
            ((offline_count++))
        fi

        log_success "  $watcher Watcher: $icon [$status]"
        if [ -n "$error" ]; then
            log_warning "    Error: $error"
        fi
    done

    log_success ""
    log_success "  Summary: $active_count active, $offline_count offline"

    if [ $offline_count -gt 0 ]; then
        log_warning "  SYSTEM RUNNING IN DEGRADED MODE"
    fi

    log_success ""
    log_success "  All active watchers are converting messages to tasks"
    log_success "  Tasks are being saved to: Inbox/"
    log_success ""
    log_info "  Logs: $WATCHERS_LOG"
    log_info "  Press Ctrl+C to stop all watchers"
    log_success "============================================"
    echo ""
}

# =============================================================================
# Mode Selection
# =============================================================================

show_usage() {
    echo ""
    echo "Usage: $0 [OPTIONS]"
    echo ""
    echo "Options:"
    echo "  --manager     Use Watcher Manager (Gold Tier, recommended)"
    echo "  --legacy      Use legacy individual watcher mode"
    echo "  --help        Show this help message"
    echo ""
    echo "Default: --manager (Gold Tier resilience)"
    echo ""
}

# =============================================================================
# Main Execution
# =============================================================================

main() {
    local mode="manager"

    # Parse arguments
    while [[ $# -gt 0 ]]; do
        case $1 in
            --manager)
                mode="manager"
                shift
                ;;
            --legacy)
                mode="legacy"
                shift
                ;;
            --help|-h)
                show_usage
                exit 0
                ;;
            *)
                log_error "Unknown option: $1"
                show_usage
                exit 1
                ;;
        esac
    done

    echo ""
    echo -e "${CYAN}============================================================${NC}"
    echo -e "${CYAN}       AI Employee Vault - External Watchers${NC}"
    echo -e "${CYAN}       Gold Tier Resilience Mode: $mode${NC}"
    echo -e "${CYAN}============================================================${NC}"
    echo ""

    log_info "Base Directory: $SCRIPT_DIR"
    log_info "Watchers Directory: $WATCHERS_DIR"
    log_info "Watchers Log: $WATCHERS_LOG"
    log_info "Mode: $mode"
    echo ""

    # Pre-flight checks
    check_prerequisites
    echo ""

    # Start watchers based on mode
    if [ "$mode" = "manager" ]; then
        start_watcher_manager
    else
        start_all_watchers_legacy
    fi

    # Wait for interrupt (manager handles its own waiting)
    if [ "$mode" = "manager" ]; then
        wait "$MANAGER_PID"
    else
        wait
    fi
}

# Run main
main "$@"
