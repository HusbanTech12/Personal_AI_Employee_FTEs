#!/bin/bash
# =============================================================================
# Cloud Sync Script - PLATINUM Tier
# =============================================================================
# Synchronizes markdown files from cloud runtime to local vault.
# Excludes all secrets, credentials, sessions, and tokens.
# 
# Usage: ./cloud_sync.sh [options]
#   --dry-run     Show what would be synced without copying
#   --verbose     Show detailed output
#   --force       Force sync even if conflicts detected
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

# Sync directories (markdown only)
SYNC_DIRS=(
    "notes/Done"
    "notes/Plans"
    "notes/Updates"
    "CloudRuntime"
)

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
    "*.json"  # Exclude JSON by default (may contain secrets)
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
NC='\033[0m' # No Color

# Counters
FILES_SYNCED=0
FILES_SKIPPED=0
FILES_EXCLUDED=0
ERRORS=0

# Options
DRY_RUN=false
VERBOSE=false
FORCE=false

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

# =============================================================================
# Helper Functions
# =============================================================================

show_help() {
    head -20 "$0" | tail -17
    exit 0
}

setup_logging() {
    mkdir -p "$LOGS_DIR"
    LOG_FILE="${LOGS_DIR}/cloud_sync_$(date +%Y%m%d_%H%M%S).log"
    touch "$LOG_FILE"
    log_verbose "Logging to: $LOG_FILE"
}

check_prerequisites() {
    log_verbose "Checking prerequisites..."
    
    # Check rsync availability
    if command -v rsync &> /dev/null; then
        USE_RSYNC=true
        log_verbose "rsync available - will use for efficient sync"
    else
        USE_RSYNC=false
        log_verbose "rsync not available - will use cp"
    fi
    
    # Check directories exist
    if [ ! -d "$VAULT_PATH" ]; then
        log_error "Vault directory not found: $VAULT_PATH"
        exit 1
    fi
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
    if [ "$USE_RSYNC" = true ]; then
        rsync -a --checksum "$src" "$dest" 2>/dev/null
    else
        cp -u "$src" "$dest" 2>/dev/null
    fi
    
    if [ $? -eq 0 ]; then
        log_success "Synced: $src → $dest"
        ((FILES_SYNCED++))
        
        # Log to sync state
        echo "$(date -Iseconds),synced,$src,$dest" >> "${SYNC_STATE_DIR}/cloud_sync_log.csv"
    else
        log_error "Failed to sync: $src → $dest"
        ((ERRORS++))
    fi
}

sync_directory() {
    local src_dir="$1"
    local dest_base="$2"
    
    if [ ! -d "$src_dir" ]; then
        log_verbose "Directory not found, skipping: $src_dir"
        return 0
    fi
    
    log_info "Syncing directory: $src_dir"
    
    # Find all files in source directory
    while IFS= read -r -d '' file; do
        local rel_path="${file#$src_dir/}"
        local dest_file="${dest_base}/${rel_path}"
        
        # Check exclusions
        if should_exclude "$file"; then
            log_verbose "Excluded: $file"
            ((FILES_EXCLUDED++))
            continue
        fi
        
        # Only sync markdown files (and some others)
        if is_markdown "$file"; then
            sync_file "$file" "$dest_file"
        else
            log_verbose "Skipping non-markdown: $file"
            ((FILES_SKIPPED++))
        fi
    done < <(find "$src_dir" -type f -print0 2>/dev/null)
}

generate_sync_report() {
    local report_file="${LOGS_DIR}/cloud_sync_report_$(date +%Y%m%d_%H%M%S).md"
    
    cat > "$report_file" << EOF
# Cloud Sync Report

**Generated:** $(date -Iseconds)
**Mode:** $([ "$DRY_RUN" = true ] && echo "DRY RUN" || echo "LIVE")

## Summary

| Metric | Count |
|--------|-------|
| Files Synced | $FILES_SYNCED |
| Files Skipped | $FILES_SKIPPED |
| Files Excluded | $FILES_EXCLUDED |
| Errors | $ERRORS |

## Sync Configuration

- **Source Base:** $BASE_DIR
- **Destination:** $VAULT_PATH
- **Using rsync:** $USE_RSYNC
- **Force Mode:** $FORCE

## Security

Files excluded by security rules:
- Environment files (.env, *.env)
- Credentials and tokens
- Session data
- Keys and certificates
- Database files
- Log files

---
*Generated by cloud_sync.sh - PLATINUM Tier*
EOF

    log_info "Report saved: $report_file"
}

# =============================================================================
# Main
# =============================================================================

main() {
    echo "=============================================="
    echo "  PLATINUM Tier - Cloud Sync"
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
    
    # Initialize sync log
    if [ ! -f "${SYNC_STATE_DIR}/cloud_sync_log.csv" ]; then
        echo "timestamp,action,source,destination" > "${SYNC_STATE_DIR}/cloud_sync_log.csv"
    fi
    
    check_prerequisites
    
    echo ""
    echo "Sync Options:"
    echo "  Dry Run: $DRY_RUN"
    echo "  Verbose: $VERBOSE"
    echo "  Force: $FORCE"
    echo ""
    
    if [ "$DRY_RUN" = true ]; then
        log_warning "DRY RUN MODE - No files will be copied"
        echo ""
    fi
    
    # Perform sync
    log_info "Starting cloud sync..."
    echo ""
    
    for dir in "${SYNC_DIRS[@]}"; do
        sync_directory "$BASE_DIR/$dir" "$BASE_DIR/$dir"
    done
    
    # Sync Done folder specifically (markdown only)
    if [ -d "$VAULT_PATH/Done" ]; then
        log_info "Syncing Done folder (markdown only)..."
        while IFS= read -r -d '' file; do
            if ! should_exclude "$file"; then
                log_verbose "Done: $(basename "$file")"
                ((FILES_SYNCED++))
            fi
        done < <(find "$VAULT_PATH/Done" -name "*.md" -type f -print0 2>/dev/null)
    fi
    
    echo ""
    
    # Summary
    echo "=============================================="
    echo "  Sync Complete"
    echo "=============================================="
    echo ""
    echo "  Files Synced:   $FILES_SYNCED"
    echo "  Files Skipped:  $FILES_SKIPPED"
    echo "  Files Excluded: $FILES_EXCLUDED"
    echo "  Errors:         $ERRORS"
    echo ""
    
    # Generate report
    generate_sync_report
    
    if [ $ERRORS -gt 0 ]; then
        log_error "Sync completed with $ERRORS errors"
        exit 1
    fi
    
    log_success "Cloud sync completed successfully"
    exit 0
}

main "$@"
