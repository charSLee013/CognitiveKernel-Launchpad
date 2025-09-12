#!/bin/bash
# ============================================================================
# CognitiveKernel-Pro Web Server Entrypoint
# ============================================================================
# Professional container startup script with health checks and graceful shutdown
# ============================================================================

set -euo pipefail

# Color definitions
readonly RED='\033[0;31m'
readonly GREEN='\033[0;32m'
readonly YELLOW='\033[1;33m'
readonly BLUE='\033[0;34m'
readonly NC='\033[0m' # No Color

# Logging functions
log_info() {
    echo -e "${GREEN}[INFO]${NC} $(date '+%Y-%m-%d %H:%M:%S') - $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $(date '+%Y-%m-%d %H:%M:%S') - $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $(date '+%Y-%m-%d %H:%M:%S') - $1"
}

log_debug() {
    if [[ "${DEBUG:-false}" == "true" ]]; then
        echo -e "${BLUE}[DEBUG]${NC} $(date '+%Y-%m-%d %H:%M:%S') - $1"
    fi
}

# Signal handling function
cleanup() {
    log_info "Received termination signal, starting graceful shutdown..."
    
    # If Node.js process is running, send SIGTERM
    if [[ -n "${NODE_PID:-}" ]]; then
        log_info "Terminating Node.js process (PID: $NODE_PID)"
        kill -TERM "$NODE_PID" 2>/dev/null || true
        
        # Wait for graceful exit
        local count=0
        while kill -0 "$NODE_PID" 2>/dev/null && [[ $count -lt 30 ]]; do
            sleep 1
            ((count++))
        done
        
        # Force kill if still running
        if kill -0 "$NODE_PID" 2>/dev/null; then
            log_warn "Force killing Node.js process"
            kill -KILL "$NODE_PID" 2>/dev/null || true
        fi
    fi
    
    log_info "Cleanup completed, exiting container"
    exit 0
}

# Register signal handlers
trap cleanup SIGTERM SIGINT SIGQUIT

# Environment variable validation
validate_environment() {
    log_info "Validating environment variables..."
    
    # Set default values
    export LISTEN_PORT="${LISTEN_PORT:-9000}"
    export MAX_BROWSERS="${MAX_BROWSERS:-16}"
    export NODE_ENV="${NODE_ENV:-production}"
    export DOCKER_CONTAINER="${DOCKER_CONTAINER:-false}"
    
    # Validate port number
    if ! [[ "$LISTEN_PORT" =~ ^[0-9]+$ ]] || [[ "$LISTEN_PORT" -lt 1 ]] || [[ "$LISTEN_PORT" -gt 65535 ]]; then
        log_error "Invalid port number: $LISTEN_PORT"
        exit 1
    fi
    
    # Validate browser count
    if ! [[ "$MAX_BROWSERS" =~ ^[0-9]+$ ]] || [[ "$MAX_BROWSERS" -lt 1 ]] || [[ "$MAX_BROWSERS" -gt 100 ]]; then
        log_error "Invalid browser count: $MAX_BROWSERS"
        exit 1
    fi
    
    log_info "Environment variable validation passed"
    log_debug "LISTEN_PORT=$LISTEN_PORT"
    log_debug "MAX_BROWSERS=$MAX_BROWSERS"
    log_debug "NODE_ENV=$NODE_ENV"
    log_debug "DOCKER_CONTAINER=$DOCKER_CONTAINER"

    # Log container mode status
    if [[ "$DOCKER_CONTAINER" == "true" ]]; then
        log_info "Running in Docker container mode - browser sandbox will be disabled"
    else
        log_info "Running in host mode - browser sandbox will be enabled"
    fi
}

# System check
system_check() {
    log_info "Performing system check..."
    
    # Check Node.js
    if ! command -v node >/dev/null 2>&1; then
        log_error "Node.js not installed"
        exit 1
    fi
    
    local node_version
    node_version=$(node --version)
    log_info "Node.js version: $node_version"
    
    # Check npm
    if ! command -v npm >/dev/null 2>&1; then
        log_error "npm not installed"
        exit 1
    fi
    
    local npm_version
    npm_version=$(npm --version)
    log_info "npm version: $npm_version"
    
    # Check required files
    if [[ ! -f "server.js" ]]; then
        log_error "server.js file does not exist"
        exit 1
    fi
    
    if [[ ! -f "package.json" ]]; then
        log_error "package.json file does not exist"
        exit 1
    fi
    
    # Check directory permissions
    if [[ ! -w "./DownloadedFiles" ]]; then
        log_error "DownloadedFiles directory is not writable"
        exit 1
    fi
    
    if [[ ! -w "./screenshots" ]]; then
        log_error "screenshots directory is not writable"
        exit 1
    fi
    
    log_info "System check passed"
}

# Dependency check
dependency_check() {
    log_info "Checking dependencies..."
    
    if [[ ! -d "node_modules" ]]; then
        log_error "node_modules directory does not exist, please run npm install first"
        exit 1
    fi
    
    # Check critical dependencies
    local required_deps=("express" "playwright" "uuid")
    for dep in "${required_deps[@]}"; do
        if [[ ! -d "node_modules/$dep" ]]; then
            log_error "Missing dependency: $dep"
            exit 1
        fi
    done
    
    log_info "Dependency check passed"
}

# Pre-start preparation
pre_start() {
    log_info "Pre-start preparation..."
    
    # Clean old screenshot files (optional)
    if [[ "${CLEAN_SCREENSHOTS:-false}" == "true" ]]; then
        log_info "Cleaning old screenshot files..."
        find ./screenshots -name "*.png" -mtime +1 -delete 2>/dev/null || true
    fi
    
    # Clean old download files (optional)
    if [[ "${CLEAN_DOWNLOADS:-false}" == "true" ]]; then
        log_info "Cleaning old download files..."
        find ./DownloadedFiles -type f -mtime +1 -delete 2>/dev/null || true
    fi
    
    log_info "Pre-start preparation completed"
}

# Start application
start_application() {
    log_info "Starting CognitiveKernel-Pro Web Server..."
    log_info "Listen port: $LISTEN_PORT"
    log_info "Max browsers: $MAX_BROWSERS"
    
    # Start Node.js application
    exec node server.js &
    NODE_PID=$!
    
    log_info "Web server started (PID: $NODE_PID)"
    log_info "Access URL: http://localhost:$LISTEN_PORT"
    
    # Wait for process to end
    wait "$NODE_PID"
}

# Main function
main() {
    log_info "============================================"
    log_info "CognitiveKernel-Pro Web Server Starting..."
    log_info "============================================"
    
    validate_environment
    system_check
    dependency_check
    pre_start
    start_application
}

# If this script is executed directly
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi
