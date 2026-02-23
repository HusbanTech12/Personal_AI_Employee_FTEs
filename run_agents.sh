#!/bin/bash
#
# AI Employee Vault - Gold Tier Multi-Agent Startup Script
#
# Starts all Gold Tier agents concurrently:
# - filesystem_watcher.py (Inbox monitoring)
# - task_executor.py (Legacy executor)
# - planner_agent.py (Task analysis & planning)
# - manager_agent.py (Skill routing & orchestration)
# - validator_agent.py (Completion verification)
# - memory_agent.py (Logging & history)
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
AGENTS_DIR="$SCRIPT_DIR/Agents"
AGENTS_LOG="$LOGS_DIR/agents.log"

# Agent scripts
WATCHER_SCRIPT="$SCRIPT_DIR/filesystem_watcher.py"
EXECUTOR_SCRIPT="$SCRIPT_DIR/task_executor.py"
PLANNER_SCRIPT="$AGENTS_DIR/planner_agent.py"
MANAGER_SCRIPT="$AGENTS_DIR/manager_agent.py"
VALIDATOR_SCRIPT="$AGENTS_DIR/validator_agent.py"
MEMORY_SCRIPT="$AGENTS_DIR/memory_agent.py"

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

log_agent() {
    log "${MAGENTA}[AGENT]${NC} $1"
}

# =============================================================================
# Cleanup and Shutdown Handlers
# =============================================================================

cleanup() {
    echo ""
    log_info "Initiating graceful shutdown..."
    
    # Kill all agent processes
    for pid in "$WATCHER_PID" "$EXECUTOR_PID" "$PLANNER_PID" "$MANAGER_PID" "$VALIDATOR_PID" "$MEMORY_PID"; do
        if [ -n "$pid" ] && kill -0 "$pid" 2>/dev/null; then
            kill -TERM "$pid" 2>/dev/null || true
            wait "$pid" 2>/dev/null || true
        fi
    done
    
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
    
    # Check required scripts exist
    for script in "$WATCHER_SCRIPT" "$EXECUTOR_SCRIPT" "$PLANNER_SCRIPT" "$MANAGER_SCRIPT" "$VALIDATOR_SCRIPT" "$MEMORY_SCRIPT"; do
        if [ ! -f "$script" ]; then
            log_error "Script not found: $script"
            exit 1
        fi
    done
    log_success "All agent scripts found"
    
    # Check skill definitions
    SKILLS_DIR="$SCRIPT_DIR/Skills"
    for skill in task_processor coding research documentation planner; do
        if [ ! -f "$SKILLS_DIR/${skill}.SKILL.md" ]; then
            log_warning "Skill definition missing: ${skill}.SKILL.md"
        fi
    done
    log_success "Skill definitions verified"
    
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
    log_agent "Starting filesystem watcher..."
    
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
    log_agent "Starting task executor..."
    
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

start_planner_agent() {
    log_agent "Starting planner agent..."
    
    source "$VENV_DIR/bin/activate"
    python "$PLANNER_SCRIPT" >> "$AGENTS_LOG" 2>&1 &
    PLANNER_PID=$!
    deactivate
    
    sleep 1
    
    if kill -0 "$PLANNER_PID" 2>/dev/null; then
        log_success "Planner agent started (PID: $PLANNER_PID)"
        return 0
    else
        log_error "Failed to start planner agent"
        return 1
    fi
}

start_manager_agent() {
    log_agent "Starting manager agent..."
    
    source "$VENV_DIR/bin/activate"
    python "$MANAGER_SCRIPT" >> "$AGENTS_LOG" 2>&1 &
    MANAGER_PID=$!
    deactivate
    
    sleep 1
    
    if kill -0 "$MANAGER_PID" 2>/dev/null; then
        log_success "Manager agent started (PID: $MANAGER_PID)"
        return 0
    else
        log_error "Failed to start manager agent"
        return 1
    fi
}

start_validator_agent() {
    log_agent "Starting validator agent..."
    
    source "$VENV_DIR/bin/activate"
    python "$VALIDATOR_SCRIPT" >> "$AGENTS_LOG" 2>&1 &
    VALIDATOR_PID=$!
    deactivate
    
    sleep 1
    
    if kill -0 "$VALIDATOR_PID" 2>/dev/null; then
        log_success "Validator agent started (PID: $VALIDATOR_PID)"
        return 0
    else
        log_error "Failed to start validator agent"
        return 1
    fi
}

start_memory_agent() {
    log_agent "Starting memory agent..."
    
    source "$VENV_DIR/bin/activate"
    python "$MEMORY_SCRIPT" >> "$AGENTS_LOG" 2>&1 &
    MEMORY_PID=$!
    deactivate
    
    sleep 1
    
    if kill -0 "$MEMORY_PID" 2>/dev/null; then
        log_success "Memory agent started (PID: $MEMORY_PID)"
        return 0
    else
        log_error "Failed to start memory agent"
        return 1
    fi
}

# =============================================================================
# Status Monitor (Background)
# =============================================================================

monitor_agents() {
    while true; do
        sleep 30
        
        # Check and restart agents if needed
        for name_pid in "Watcher:WATCHER_PID" "Executor:EXECUTOR_PID" "Planner:PLANNER_PID" "Manager:MANAGER_PID" "Validator:VALIDATOR_PID" "Memory:MEMORY_PID"; do
            name="${name_pid%%:*}"
            pid_var="${name_pid##*:}"
            pid="${!pid_var}"
            
            if ! kill -0 "$pid" 2>/dev/null; then
                log_warning "$name agent died unexpectedly, restarting..."
                case "$name" in
                    Watcher) start_filesystem_watcher ;;
                    Executor) start_task_executor ;;
                    Planner) start_planner_agent ;;
                    Manager) start_manager_agent ;;
                    Validator) start_validator_agent ;;
                    Memory) start_memory_agent ;;
                esac
            fi
        done
    done
}

# =============================================================================
# Status Display
# =============================================================================

show_status() {
    echo ""
    log_success "============================================"
    log_success "  Gold Tier AI Employee - Agent Status"
    log_success "============================================"
    log_success ""
    log_success "  Filesystem Watcher:  PID $WATCHER_PID"
    log_success "  Task Executor:       PID $EXECUTOR_PID"
    log_success "  Planner Agent:       PID $PLANNER_PID"
    log_success "  Manager Agent:       PID $MANAGER_PID"
    log_success "  Validator Agent:     PID $VALIDATOR_PID"
    log_success "  Memory Agent:        PID $MEMORY_PID"
    log_success ""
    log_info "  Logs: $AGENTS_LOG"
    log_info "  Press Ctrl+C to stop all agents"
    log_success "============================================"
    echo ""
}

# =============================================================================
# Main Execution
# =============================================================================

main() {
    echo ""
    echo -e "${CYAN}============================================================${NC}"
    echo -e "${CYAN}       AI Employee Vault - Gold Tier Multi-Agent${NC}"
    echo -e "${CYAN}============================================================${NC}"
    echo ""
    
    log_info "Base Directory: $SCRIPT_DIR"
    log_info "Agents Directory: $AGENTS_DIR"
    log_info "Agents Log: $AGENTS_LOG"
    echo ""
    
    # Pre-flight checks
    check_prerequisites
    echo ""
    
    # Start all agents
    log_info "Starting Gold Tier agent system..."
    echo ""
    
    start_filesystem_watcher
    start_task_executor
    start_planner_agent
    start_manager_agent
    start_validator_agent
    start_memory_agent
    
    echo ""
    
    # Show status
    show_status
    
    # Start background monitor
    monitor_agents &
    MONITOR_PID=$!
    
    # Wait for interrupt
    wait
}

# Run main
main "$@"
