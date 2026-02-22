#!/bin/bash
#
# AI Employee Vault - Agent Startup Script (Silver Tier)
#
# Starts both filesystem_watcher.py and task_executor.py concurrently
# with proper venv activation, logging, and graceful shutdown handling.
#
# Usage: bash run_agents.sh
# Stop:  Press Ctrl+C to gracefully shutdown all agents
#

set -e

# =============================================================================
# Configuration
# =============================================================================

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_DIR="$SCRIPT_DIR/venv"
LOGS_DIR="$SCRIPT_DIR/Logs"
AGENTS_LOG="$LOGS_DIR/agents.log"

WATCHER_SCRIPT="$SCRIPT_DIR/filesystem_watcher.py"
EXECUTOR_SCRIPT="$SCRIPT_DIR/task_executor.py"

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
    echo -e "[$timestamp] $1" | tee -a "$AGENTS_LOG"
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

# =============================================================================
# Cleanup and Shutdown Handlers
# =============================================================================

cleanup() {
    echo ""
    log_info "Initiating graceful shutdown..."
    
    # Kill background processes
    if [ -n "$WATCHER_PID" ] && kill -0 "$WATCHER_PID" 2>/dev/null; then
        log_info "Stopping filesystem watcher (PID: $WATCHER_PID)..."
        kill -TERM "$WATCHER_PID" 2>/dev/null || true
        wait "$WATCHER_PID" 2>/dev/null || true
        log_success "Filesystem watcher stopped"
    fi
    
    if [ -n "$EXECUTOR_PID" ] && kill -0 "$EXECUTOR_PID" 2>/dev/null; then
        log_info "Stopping task executor (PID: $EXECUTOR_PID)..."
        kill -TERM "$EXECUTOR_PID" 2>/dev/null || true
        wait "$EXECUTOR_PID" 2>/dev/null || true
        log_success "Task executor stopped"
    fi
    
    log_success "All agents stopped. Goodbye!"
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
    
    # Check venv
    if [ ! -d "$VENV_DIR" ]; then
        log_error "Virtual environment not found at: $VENV_DIR"
        log_info "Creating virtual environment..."
        $PYTHON_CMD -m venv "$VENV_DIR"
    fi
    log_success "Virtual environment verified"
    
    # Check scripts exist
    if [ ! -f "$WATCHER_SCRIPT" ]; then
        log_error "Filesystem watcher not found: $WATCHER_SCRIPT"
        exit 1
    fi
    log_success "Filesystem watcher script found"
    
    if [ ! -f "$EXECUTOR_SCRIPT" ]; then
        log_error "Task executor not found: $EXECUTOR_SCRIPT"
        exit 1
    fi
    log_success "Task executor script found"
    
    # Ensure logs directory exists
    mkdir -p "$LOGS_DIR"
    log_success "Logs directory verified"
    
    # Check watchdog is installed
    source "$VENV_DIR/bin/activate"
    if ! python -c "import watchdog" 2>/dev/null; then
        log_warning "Installing watchdog package..."
        pip install -q watchdog
    fi
    log_success "Dependencies verified"
    deactivate
}

# =============================================================================
# Agent Startup Functions
# =============================================================================

start_filesystem_watcher() {
    log_info "Starting filesystem watcher..."
    
    source "$VENV_DIR/bin/activate"
    python "$WATCHER_SCRIPT" >> "$AGENTS_LOG" 2>&1 &
    WATCHER_PID=$!
    deactivate
    
    sleep 1
    
    if kill -0 "$WATCHER_PID" 2>/dev/null; then
        log_success "Filesystem watcher started (PID: $WATCHER_PID)"
        return 0
    else
        log_error "Failed to start filesystem watcher"
        return 1
    fi
}

start_task_executor() {
    log_info "Starting task executor..."
    
    source "$VENV_DIR/bin/activate"
    python "$EXECUTOR_SCRIPT" >> "$AGENTS_LOG" 2>&1 &
    EXECUTOR_PID=$!
    deactivate
    
    sleep 1
    
    if kill -0 "$EXECUTOR_PID" 2>/dev/null; then
        log_success "Task executor started (PID: $EXECUTOR_PID)"
        return 0
    else
        log_error "Failed to start task executor"
        return 1
    fi
}

# =============================================================================
# Status Monitor (Background)
# =============================================================================

monitor_agents() {
    while true; do
        sleep 30
        
        # Check watcher
        if ! kill -0 "$WATCHER_PID" 2>/dev/null; then
            log_warning "Filesystem watcher died unexpectedly, restarting..."
            start_filesystem_watcher
        fi
        
        # Check executor
        if ! kill -0 "$EXECUTOR_PID" 2>/dev/null; then
            log_warning "Task executor died unexpectedly, restarting..."
            start_task_executor
        fi
    done
}

# =============================================================================
# Main Execution
# =============================================================================

main() {
    echo ""
    echo -e "${CYAN}============================================================${NC}"
    echo -e "${CYAN}       AI Employee Vault - Silver Tier Startup${NC}"
    echo -e "${CYAN}============================================================${NC}"
    echo ""
    
    log_info "Base Directory: $SCRIPT_DIR"
    log_info "Agents Log: $AGENTS_LOG"
    echo ""
    
    # Pre-flight checks
    check_prerequisites
    echo ""
    
    # Start agents
    log_info "Starting AI Employee agents..."
    echo ""
    
    start_filesystem_watcher
    FW_RESULT=$?
    
    start_task_executor
    TE_RESULT=$?
    
    echo ""
    
    if [ $FW_RESULT -eq 0 ] && [ $TE_RESULT -eq 0 ]; then
        log_success "============================================"
        log_success "  All agents started successfully!"
        log_success "============================================"
        log_success ""
        log_success "  Filesystem Watcher: PID $WATCHER_PID"
        log_success "  Task Executor:      PID $EXECUTOR_PID"
        log_success ""
        log_info "  Monitoring Inbox/ for new tasks..."
        log_info "  Processing Needs_Action/ queue..."
        log_success ""
        log_info "  Press Ctrl+C to stop all agents"
        log_success "============================================"
        echo ""
        
        # Start background monitor
        monitor_agents &
        MONITOR_PID=$!
        
        # Wait for interrupt
        wait
    else
        log_error "Failed to start one or more agents"
        cleanup
        exit 1
    fi
}

# Run main
main "$@"
