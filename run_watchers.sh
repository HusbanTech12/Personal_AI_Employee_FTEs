#!/bin/bash
#
# AI Employee Vault - External Watchers Startup Script
#
# Starts all external watcher agents:
# - gmail_watcher.py (Email monitoring)
# - whatsapp_watcher.py (Message monitoring)
# - linkedin_watcher.py (Professional network monitoring)
#
# Usage: bash run_watchers.sh
# Stop:  Press Ctrl+C to gracefully shutdown all watchers
#

set -e

# =============================================================================
# Configuration
# =============================================================================

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_DIR="$SCRIPT_DIR/venv"
LOGS_DIR="$SCRIPT_DIR/Logs"
WATCHERS_DIR="$SCRIPT_DIR/Watchers"
WATCHERS_LOG="$LOGS_DIR/watchers.log"

# Watcher scripts
GMAIL_WATCHER="$WATCHERS_DIR/gmail_watcher.py"
WHATSAPP_WATCHER="$WATCHERS_DIR/whatsapp_watcher.py"
LINKEDIN_WATCHER="$WATCHERS_DIR/linkedin_watcher.py"

# =============================================================================
# Colors for Output
# =============================================================================

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
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

log_watcher() {
    log "${CYAN}[WATCHER]${NC} $1"
}

# =============================================================================
# Cleanup and Shutdown Handlers
# =============================================================================

cleanup() {
    echo ""
    log_info "Initiating graceful shutdown..."
    
    # Kill all watcher processes
    for pid in "$GMAIL_PID" "$WHATSAPP_PID" "$LINKEDIN_PID"; do
        if [ -n "$pid" ] && kill -0 "$pid" 2>/dev/null; then
            kill -TERM "$pid" 2>/dev/null || true
            wait "$pid" 2>/dev/null || true
        fi
    done
    
    log_success "All watchers stopped. Goodbye!"
    exit 0
}

# Trap Ctrl+C and termination signals
trap cleanup SIGINT SIGTERM EXIT

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
    
    # Check watcher scripts exist
    for script in "$GMAIL_WATCHER" "$WHATSAPP_WATCHER" "$LINKEDIN_WATCHER"; do
        if [ ! -f "$script" ]; then
            log_error "Watcher script not found: $script"
            exit 1
        fi
    done
    log_success "All watcher scripts found"
    
    # Ensure logs directory exists
    mkdir -p "$LOGS_DIR"
    mkdir -p "$WATCHERS_DIR"
    log_success "Directories verified"
}

# =============================================================================
# Watcher Startup Functions
# =============================================================================

start_gmail_watcher() {
    log_watcher "Starting Gmail watcher..."
    
    source "$VENV_DIR/bin/activate" 2>/dev/null || true
    python "$GMAIL_WATCHER" >> "$WATCHERS_LOG" 2>&1 &
    GMAIL_PID=$!
    deactivate 2>/dev/null || true
    
    sleep 2
    
    if kill -0 "$GMAIL_PID" 2>/dev/null; then
        log_success "Gmail watcher started (PID: $GMAIL_PID)"
        return 0
    else
        log_error "Failed to start Gmail watcher"
        return 1
    fi
}

start_whatsapp_watcher() {
    log_watcher "Starting WhatsApp watcher..."
    
    source "$VENV_DIR/bin/activate" 2>/dev/null || true
    python "$WHATSAPP_WATCHER" >> "$WATCHERS_LOG" 2>&1 &
    WHATSAPP_PID=$!
    deactivate 2>/dev/null || true
    
    sleep 2
    
    if kill -0 "$WHATSAPP_PID" 2>/dev/null; then
        log_success "WhatsApp watcher started (PID: $WHATSAPP_PID)"
        return 0
    else
        log_error "Failed to start WhatsApp watcher"
        return 1
    fi
}

start_linkedin_watcher() {
    log_watcher "Starting LinkedIn watcher..."
    
    source "$VENV_DIR/bin/activate" 2>/dev/null || true
    python "$LINKEDIN_WATCHER" >> "$WATCHERS_LOG" 2>&1 &
    LINKEDIN_PID=$!
    deactivate 2>/dev/null || true
    
    sleep 2
    
    if kill -0 "$LINKEDIN_PID" 2>/dev/null; then
        log_success "LinkedIn watcher started (PID: $LINKEDIN_PID)"
        return 0
    else
        log_error "Failed to start LinkedIn watcher"
        return 1
    fi
}

# =============================================================================
# Status Display
# =============================================================================

show_status() {
    echo ""
    log_success "============================================"
    log_success "  External Watchers - Status"
    log_success "============================================"
    log_success ""
    log_success "  Gmail Watcher:     PID $GMAIL_PID"
    log_success "  WhatsApp Watcher:  PID $WHATSAPP_PID"
    log_success "  LinkedIn Watcher:  PID $LINKEDIN_PID"
    log_success ""
    log_success "  All watchers are converting messages to tasks"
    log_success "  Tasks are being saved to: Inbox/"
    log_success ""
    log_info "  Logs: $WATCHERS_LOG"
    log_info "  Press Ctrl+C to stop all watchers"
    log_success "============================================"
    echo ""
}

# =============================================================================
# Main Execution
# =============================================================================

main() {
    echo ""
    echo -e "${CYAN}============================================================${NC}"
    echo -e "${CYAN}       AI Employee Vault - External Watchers${NC}"
    echo -e "${CYAN}============================================================${NC}"
    echo ""
    
    log_info "Base Directory: $SCRIPT_DIR"
    log_info "Watchers Directory: $WATCHERS_DIR"
    log_info "Watchers Log: $WATCHERS_LOG"
    echo ""
    
    # Pre-flight checks
    check_prerequisites
    echo ""
    
    # Start all watchers
    log_info "Starting external watchers..."
    echo ""
    
    start_gmail_watcher
    start_whatsapp_watcher
    start_linkedin_watcher
    
    echo ""
    
    # Show status
    show_status
    
    # Wait for interrupt
    wait
}

# Run main
main "$@"
