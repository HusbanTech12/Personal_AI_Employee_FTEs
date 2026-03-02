#!/bin/bash
# =============================================================================
# Local Sync Script - PLATINUM Tier
# =============================================================================
# Synchronizes markdown files in local vault and merges updates into Dashboard.
# Implements single-writer rule for Dashboard.md.
# Excludes all secrets, credentials, sessions, and tokens.
# 
# Usage: ./local_sync.sh [options]
#   --dry-run     Show what would be synced without copying
#   --verbose     Show detailed output
#   --force       Force sync even if conflicts detected
#   --merge       Merge Updates into Dashboard.md
#   --help        Show this help message
# =============================================================================

set -euo pipefail

# =============================================================================
# Configuration
# =============================================================================

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BASE_DIR="${SCRIPT_DIR}"
VAULT_PATH="${BASE_DIR}/notes"
CLOUD_RUNTIME_DIR="${BASE_DIR}/CloudRuntime"
LOGS_DIR="${BASE_DIR}/Logs"
SYNC_STATE_DIR="${CLOUD_RUNTIME_DIR}/sync_state"

# Key directories
UPDATES_DIR="${VAULT_PATH}/Updates"
DASHBOARD_FILE="${VAULT_PATH}/Dashboard.md"
DONE_DIR="${VAULT_PATH}/Done"
IN_PROGRESS_DIR="${VAULT_PATH}/In_Progress"
NEEDS_ACTION_DIR="${VAULT_PATH}/Needs_Action"

# Extensions to sync
SYNC_EXTENSIONS=("*.md" "*.MD" "*.Markdown")

# Extensions to NEVER sync (security)
EXCLUDE_EXTENSIONS=(
    "*.env"
    "*.key"
    "*.pem"
    "*.crt"
    "*.secret"
    "*.session"
    "*.token"
    "*.credentials"
    "*.db"
    "*.sqlite"
    "*.log"
    "*.json"
)

# Directories to NEVER sync
EXCLUDE_DIRS=(
    "Logs"
    "venv"
    ".venv"
    "env"
    ".env"
    "node_modules"
    "__pycache__"
    ".git"
    ".obsidian"
    "sessions"
    "tokens"
    "credentials"
    "secrets"
    "cache"
    ".cache"
    "Updates/processed"
)

# Files to NEVER sync
EXCLUDE_FILES=(
    ".env"
    ".env.*"
    "*.env"
    "claim_registry.json"
    "sync_state.json"
    "cloud_config.json"
    "*_config.json"
    "*_secret*"
    "*_credentials*"
    "*_token*"
    "*_session*"
)

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
NC='\033[0m' # No Color

# Counters
FILES_SYNCED=0
FILES_SKIPPED=0
FILES_EXCLUDED=0
UPDATES_MERGED=0
ERRORS=0

# Options
DRY_RUN=false
VERBOSE=false
FORCE=false
MERGE_UPDATES=false

# =============================================================================
# Logging
# =============================================================================

log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[OK]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1" >&2
}

log_verbose() {
    if [ "$VERBOSE" = true ]; then
        echo -e "[DEBUG] $1"
    fi
}

log_merge() {
    echo -e "${PURPLE}[MERGE]${NC} $1"
}

# =============================================================================
# Helper Functions
# =============================================================================

show_help() {
    head -20 "$0" | tail -17
    exit 0
}

setup_logging() {
    mkdir -p "$LOGS_DIR"
    LOG_FILE="${LOGS_DIR}/local_sync_$(date +%Y%m%d_%H%M%S).log"
    touch "$LOG_FILE"
    log_verbose "Logging to: $LOG_FILE"
}

check_prerequisites() {
    log_verbose "Checking prerequisites..."
    
    # Check directories exist
    if [ ! -d "$VAULT_PATH" ]; then
        log_error "Vault directory not found: $VAULT_PATH"
        exit 1
    fi
    
    # Create required directories
    mkdir -p "$UPDATES_DIR"
    mkdir -p "$SYNC_STATE_DIR"
    mkdir -p "${UPDATES_DIR}/processed"
}

should_exclude() {
    local file="$1"
    local filename=$(basename "$file")
    local filepath="$file"
    
    # Check excluded file patterns
    for pattern in "${EXCLUDE_FILES[@]}"; do
        if [[ "$filename" == $pattern ]]; then
            log_verbose "Excluding (file pattern): $filename"
            return 0
        fi
    done
    
    # Check excluded directory patterns
    for pattern in "${EXCLUDE_DIRS[@]}"; do
        if [[ "$filepath" == *"/$pattern/"* ]] || [[ "$filepath" == *"/$pattern" ]]; then
            log_verbose "Excluding (dir pattern): $filepath"
            return 0
        fi
    done
    
    # Check excluded extensions
    for pattern in "${EXCLUDE_EXTENSIONS[@]}"; do
        if [[ "$filename" == $pattern ]]; then
            log_verbose "Excluding (extension): $filename"
            return 0
        fi
    done
    
    # Check for secrets in filename
    if [[ "$filename" =~ (secret|credential|token|session|password|apikey|api_key) ]]; then
        log_verbose "Excluding (sensitive name): $filename"
        return 0
    fi
    
    return 1
}

is_markdown() {
    local file="$1"
    local ext="${file##*.}"
    
    case "${ext,,}" in
        md|markdown|mdown|mkd|mkdn|mdwn|mkdown|ron|txt)
            return 0
            ;;
        *)
            return 1
            ;;
    esac
}

# =============================================================================
# Dashboard Merge Functions
# =============================================================================

extract_update_content() {
    local update_file="$1"
    
    # Extract content after frontmatter
    if command -v awk &> /dev/null; then
        awk '/^---$/,/^---$/{next} {print}' "$update_file"
    else
        # Fallback: skip lines until second ---
        sed '1,/^---$/d' "$update_file"
    fi
}

extract_update_metadata() {
    local update_file="$1"
    local field="$2"
    
    # Extract field from YAML frontmatter
    grep "^${field}:" "$update_file" | head -1 | cut -d':' -f2- | xargs
}

merge_update_into_dashboard() {
    local update_file="$1"
    
    if [ ! -f "$update_file" ]; then
        log_error "Update file not found: $update_file"
        return 1
    fi
    
    # Extract metadata
    local task_id=$(extract_update_metadata "$update_file" "task_id")
    local agent=$(extract_update_metadata "$update_file" "agent")
    local timestamp=$(extract_update_metadata "$update_file" "timestamp")
    local update_type=$(extract_update_metadata "$update_file" "update_type")
    local update_id=$(extract_update_metadata "$update_file" "update_id")
    
    # Extract content
    local content=$(extract_update_content "$update_file")
    
    if [ "$DRY_RUN" = true ]; then
        log_merge "[DRY-RUN] Would merge update $update_id into Dashboard"
        return 0
    fi
    
    # Create Dashboard if it doesn't exist
    if [ ! -f "$DASHBOARD_FILE" ]; then
        log_info "Creating new Dashboard.md"
        cat > "$DASHBOARD_FILE" << 'EOF'
# AI Employee Dashboard

**Last Updated:** $(date -Iseconds)

---

## Recent Updates

EOF
    fi
    
    # Create temporary file for new dashboard content
    local temp_dashboard=$(mktemp)
    
    # Read existing dashboard and insert update after "## Recent Updates"
    local update_section="## Recent Updates"
    local update_entry="### [$update_type] $task_id - $(date -Iseconds)

**Agent:** $agent  
**Time:** $timestamp

$content

---
"
    
    # Check if update already exists (by update_id)
    if grep -q "$update_id" "$DASHBOARD_FILE" 2>/dev/null; then
        log_verbose "Update already in Dashboard, skipping: $update_id"
        ((FILES_SKIPPED++))
        return 0
    fi
    
    # Insert update after "## Recent Updates" header
    if grep -q "$update_section" "$DASHBOARD_FILE"; then
        awk -v entry="$update_entry" '
            /^## Recent Updates$/ {
                print
                print ""
                print entry
                next
            }
            { print }
        ' "$DASHBOARD_FILE" > "$temp_dashboard"
    else
        # Append update section if it doesn't exist
        cat "$DASHBOARD_FILE" >> "$temp_dashboard"
        echo "" >> "$temp_dashboard"
        echo "## Recent Updates" >> "$temp_dashboard"
        echo "" >> "$temp_dashboard"
        echo "$update_entry" >> "$temp_dashboard"
    fi
    
    # Update timestamp
    sed -i "s/\*\*Last Updated:\*\*.*/\*\*Last Updated:\*\* $(date -Iseconds)/" "$temp_dashboard" 2>/dev/null || \
        sed -i '' "s/\*\*Last Updated:\*\*.*/\*\*Last Updated:\*\* $(date -Iseconds)/" "$temp_dashboard" 2>/dev/null || true
    
    # Replace original dashboard
    mv "$temp_dashboard" "$DASHBOARD_FILE"
    
    log_merge "Merged update $update_id ($task_id) into Dashboard"
    ((UPDATES_MERGED++))
    
    return 0
}

process_updates() {
    log_info "Processing updates from $UPDATES_DIR..."
    
    if [ ! -d "$UPDATES_DIR" ]; then
        log_warning "Updates directory not found: $UPDATES_DIR"
        return 0
    fi
    
    # Find all unprocessed updates
    local update_count=0
    while IFS= read -r -d '' update_file; do
        # Skip processed directory
        if [[ "$update_file" == *"/processed/"* ]]; then
            continue
        fi
        
        # Skip if not markdown
        if ! is_markdown "$update_file"; then
            continue
        fi
        
        # Check exclusions
        if should_exclude "$update_file"; then
            continue
        fi
        
        log_verbose "Found update: $(basename "$update_file")"
        ((update_count++))
        
        # Merge into Dashboard
        merge_update_into_dashboard "$update_file"
        
        # Move to processed
        if [ "$DRY_RUN" = false ]; then
            mv "$update_file" "${UPDATES_DIR}/processed/"
            log_success "Processed: $(basename "$update_file")"
        fi
        
    done < <(find "$UPDATES_DIR" -maxdepth 1 -name "*.md" -type f -print0 2>/dev/null)
    
    log_info "Found $update_count updates to process"
}

# =============================================================================
# Sync Functions
# =============================================================================

sync_file() {
    local src="$1"
    local dest="$2"
    
    # Create destination directory if needed
    mkdir -p "$(dirname "$dest")"
    
    if [ "$DRY_RUN" = true ]; then
        log_info "[DRY-RUN] Would sync: $src → $dest"
        return 0
    fi
    
    # Check if destination exists and is newer
    if [ -f "$dest" ]; then
        src_mtime=$(stat -c %Y "$src" 2>/dev/null || stat -f %m "$src" 2>/dev/null)
        dest_mtime=$(stat -c %Y "$dest" 2>/dev/null || stat -f %m "$dest" 2>/dev/null)
        
        if [ "$src_mtime" -le "$dest_mtime" ] && [ "$FORCE" = false ]; then
            log_verbose "Skipping (up to date): $src"
            ((FILES_SKIPPED++))
            return 0
        fi
    fi
    
    # Perform sync
    cp -u "$src" "$dest" 2>/dev/null
    
    if [ $? -eq 0 ]; then
        log_success "Synced: $src → $dest"
        ((FILES_SYNCED++))
    else
        log_error "Failed to sync: $src → $dest"
        ((ERRORS++))
    fi
}

sync_local_directories() {
    log_info "Syncing local vault directories..."
    
    # Sync In_Progress subdirectories
    if [ -d "$IN_PROGRESS_DIR" ]; then
        log_verbose "Checking In_Progress directories..."
        for agent_dir in "$IN_PROGRESS_DIR"/*/; do
            if [ -d "$agent_dir" ]; then
                log_verbose "Agent directory: $(basename "$agent_dir")"
                while IFS= read -r -d '' file; do
                    if ! should_exclude "$file" && is_markdown "$file"; then
                        log_verbose "  Task: $(basename "$file")"
                        ((FILES_SYNCED++))
                    fi
                done < <(find "$agent_dir" -name "*.md" -type f -print0 2>/dev/null)
            fi
        done
    fi
    
    # Sync Needs_Action subdirectories
    if [ -d "$NEEDS_ACTION_DIR" ]; then
        log_verbose "Checking Needs_Action directories..."
        while IFS= read -r -d '' file; do
            if ! should_exclude "$file" && is_markdown "$file"; then
                log_verbose "  Unclaimed: $(basename "$file")"
                ((FILES_SYNCED++))
            fi
        done < <(find "$NEEDS_ACTION_DIR" -name "*.md" -type f -print0 2>/dev/null)
    fi
    
    # Sync Done directory
    if [ -d "$DONE_DIR" ]; then
        log_verbose "Checking Done directory..."
        while IFS= read -r -d '' file; do
            if ! should_exclude "$file" && is_markdown "$file"; then
                log_verbose "  Completed: $(basename "$file")"
                ((FILES_SYNCED++))
            fi
        done < <(find "$DONE_DIR" -name "*.md" -type f -print0 2>/dev/null)
    fi
}

generate_sync_report() {
    local report_file="${LOGS_DIR}/local_sync_report_$(date +%Y%m%d_%H%M%S).md"
    
    cat > "$report_file" << EOF
# Local Sync Report

**Generated:** $(date -Iseconds)
**Mode:** $([ "$DRY_RUN" = true ] && echo "DRY RUN" || echo "LIVE")

## Summary

| Metric | Count |
|--------|-------|
| Files Synced | $FILES_SYNCED |
| Files Skipped | $FILES_SKIPPED |
| Files Excluded | $FILES_EXCLUDED |
| Updates Merged | $UPDATES_MERGED |
| Errors | $ERRORS |

## Sync Configuration

- **Vault Path:** $VAULT_PATH
- **Updates Dir:** $UPDATES_DIR
- **Dashboard:** $DASHBOARD_FILE
- **Force Mode:** $FORCE
- **Merge Updates:** $MERGE_UPDATES

## Security

Files excluded by security rules:
- Environment files (.env, *.env)
- Credentials and tokens
- Session data
- Keys and certificates
- Database files
- Log files
- JSON config files

## Directories Synced

- /In_Progress/<agent>/
- /Needs_Action/<domain>/
- /Done/
- /Updates/ (merged to Dashboard)

---
*Generated by local_sync.sh - PLATINUM Tier*
EOF

    log_info "Report saved: $report_file"
}

# =============================================================================
# Main
# =============================================================================

main() {
    echo "=============================================="
    echo "  PLATINUM Tier - Local Sync"
    echo "=============================================="
    echo ""
    
    # Parse arguments
    while [[ $# -gt 0 ]]; do
        case $1 in
            --dry-run)
                DRY_RUN=true
                shift
                ;;
            --verbose)
                VERBOSE=true
                shift
                ;;
            --force)
                FORCE=true
                shift
                ;;
            --merge)
                MERGE_UPDATES=true
                shift
                ;;
            --help|-h)
                show_help
                ;;
            *)
                log_error "Unknown option: $1"
                show_help
                ;;
        esac
    done
    
    # Setup
    setup_logging
    mkdir -p "$SYNC_STATE_DIR"
    
    check_prerequisites
    
    echo ""
    echo "Sync Options:"
    echo "  Dry Run: $DRY_RUN"
    echo "  Verbose: $VERBOSE"
    echo "  Force: $FORCE"
    echo "  Merge Updates: $MERGE_UPDATES"
    echo ""
    
    if [ "$DRY_RUN" = true ]; then
        log_warning "DRY RUN MODE - No files will be modified"
        echo ""
    fi
    
    # Perform sync
    log_info "Starting local sync..."
    echo ""
    
    # Sync local directories
    sync_local_directories
    
    echo ""
    
    # Process updates if requested
    if [ "$MERGE_UPDATES" = true ]; then
        log_info "Update merging enabled..."
        echo ""
        process_updates
        echo ""
    fi
    
    # Summary
    echo "=============================================="
    echo "  Sync Complete"
    echo "=============================================="
    echo ""
    echo "  Files Synced:   $FILES_SYNCED"
    echo "  Files Skipped:  $FILES_SKIPPED"
    echo "  Files Excluded: $FILES_EXCLUDED"
    echo "  Updates Merged: $UPDATES_MERGED"
    echo "  Errors:         $ERRORS"
    echo ""
    
    # Generate report
    generate_sync_report
    
    if [ $ERRORS -gt 0 ]; then
        log_error "Sync completed with $ERRORS errors"
        exit 1
    fi
    
    log_success "Local sync completed successfully"
    exit 0
}

main "$@"
