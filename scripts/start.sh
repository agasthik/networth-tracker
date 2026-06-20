#!/bin/bash
#
# Unix/Linux/macOS startup script for Networth Tracker.
# Provides convenient commands for starting the application.
#

set -e  # Exit on any error

# Script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
VENV_DIR="$PROJECT_DIR/venv"
VENV_PYTHON="$VENV_DIR/bin/python"

# Default values
ENVIRONMENT="production"
HOST="127.0.0.1"
PORT="5000"
DAEMON=false
VALIDATE_ONLY=false
CREATE_DIRS=false
DEBUG=false
RESTART_MODE=false

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

create_virtualenv() {
    print_info "Creating virtual environment..."
    python3 -m venv "$VENV_DIR"
}

is_virtualenv_usable() {
    [[ -x "$VENV_PYTHON" ]] || return 1
    "$VENV_PYTHON" -c "import sys" >/dev/null 2>&1
}

repair_virtualenv() {
    if [[ -d "$VENV_DIR" ]]; then
        local backup_dir="${TMPDIR:-/tmp}/networth-tracker-venv.broken.$(date +%Y%m%d%H%M%S)"
        print_warning "Virtual environment is invalid; moving it to $backup_dir"
        mv "$VENV_DIR" "$backup_dir"
    fi

    create_virtualenv
}

# Function to show usage
show_usage() {
    cat << EOF
Usage: $0 [OPTIONS]

Options:
    -e, --env ENV           Environment (development|production|testing) [default: production]
    -h, --host HOST         Host to bind to [default: 127.0.0.1]
    -p, --port PORT         Port to bind to [default: 5000]
    -d, --daemon            Run as daemon
    -D, --debug             Enable debug mode
    -v, --validate          Validate configuration only
    -c, --create-dirs       Create directories only
    --stop                  Stop the running application
    --restart               Restart the application
    --status                Check application status
    --help                  Show this help message

Examples:
    $0                      # Start in production mode
    $0 -e development       # Start in development mode
    $0 -d                   # Start as daemon
    $0 -v                   # Validate configuration
    $0 -c                   # Create directories
    $0 --restart            # Restart the application
    $0 --stop               # Stop the application
    $0 --status             # Check if running

EOF
}

# Function to check prerequisites
check_prerequisites() {
    print_info "Checking prerequisites..."

    # Check if Python 3 is available
    if ! command -v python3 &> /dev/null; then
        print_error "Python 3 is required but not installed"
        exit 1
    fi

    # Check Python version (3.8+)
    python_version=$(python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
    major_version=$(echo "$python_version" | cut -d. -f1)
    minor_version=$(echo "$python_version" | cut -d. -f2)

    if [[ $major_version -lt 3 ]] || [[ $major_version -eq 3 && $minor_version -lt 8 ]]; then
        print_error "Python 3.8 or higher is required (found: $python_version)"
        exit 1
    fi

    # Check if virtual environment exists
    if [[ ! -d "$VENV_DIR" ]]; then
        print_warning "Virtual environment not found at $VENV_DIR"
        create_virtualenv
    elif ! is_virtualenv_usable; then
        repair_virtualenv
    fi

    # Check if requirements are installed
    if ! "$VENV_PYTHON" -c "import flask" &>/dev/null; then
        print_info "Installing requirements..."
        "$VENV_PYTHON" -m pip install -r "$PROJECT_DIR/requirements.txt"
    fi

    print_success "Prerequisites check completed"
}

# Function to set file permissions
set_permissions() {
    print_info "Setting file permissions..."

    # Make scripts executable
    chmod +x "$SCRIPT_DIR"/*.sh 2>/dev/null || true
    chmod +x "$SCRIPT_DIR"/*.py 2>/dev/null || true

    # Set database file permissions (if they exist)
    for db_file in "$PROJECT_DIR/networth.db" "$PROJECT_DIR/networth_demo.db"; do
        if [[ -f "$db_file" ]]; then
            chmod 600 "$db_file"
            print_info "Set permissions for $db_file"
        fi
    done

    # Create and set permissions for log directory
    mkdir -p "$PROJECT_DIR/logs"
    chmod 755 "$PROJECT_DIR/logs"

    # Create and set permissions for backup directory
    mkdir -p "$PROJECT_DIR/backups"
    chmod 700 "$PROJECT_DIR/backups"

    print_success "File permissions set"
}

# Function to check if application is running
check_running() {
    local pid_file="$PROJECT_DIR/networth_tracker.pid"

    if [[ -f "$pid_file" ]]; then
        local pid=$(cat "$pid_file")
        if kill -0 "$pid" 2>/dev/null; then
            return 0  # Running
        else
            # Stale PID file
            rm -f "$pid_file"
            return 1  # Not running
        fi
    fi

    return 1  # Not running
}

# Function to stop the application
stop_application() {
    local pid_file="$PROJECT_DIR/networth_tracker.pid"

    if [[ -f "$pid_file" ]]; then
        local pid=$(cat "$pid_file")
        if kill -0 "$pid" 2>/dev/null; then
            print_info "Stopping application (PID: $pid)..."
            kill -TERM "$pid"

            # Wait for graceful shutdown
            local count=0
            while kill -0 "$pid" 2>/dev/null && [[ $count -lt 30 ]]; do
                sleep 1
                ((count++))
            done

            if kill -0 "$pid" 2>/dev/null; then
                print_warning "Graceful shutdown failed, forcing termination..."
                kill -KILL "$pid"
            fi

            rm -f "$pid_file"
            print_success "Application stopped"
        else
            print_warning "PID file exists but process not running"
            rm -f "$pid_file"
        fi
    else
        print_info "Application is not running"
    fi
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -e|--env)
            ENVIRONMENT="$2"
            shift 2
            ;;
        -h|--host)
            HOST="$2"
            shift 2
            ;;
        -p|--port)
            PORT="$2"
            shift 2
            ;;
        -d|--daemon)
            DAEMON=true
            shift
            ;;
        -D|--debug)
            DEBUG=true
            shift
            ;;
        -v|--validate)
            VALIDATE_ONLY=true
            shift
            ;;
        -c|--create-dirs)
            CREATE_DIRS=true
            shift
            ;;
        --stop)
            stop_application
            exit 0
            ;;
        --restart)
            RESTART_MODE=true
            print_info "Restarting application..."
            if check_running; then
                stop_application
                sleep 2
            fi
            print_info "Starting application..."
            # Continue with normal startup
            shift
            ;;
        --status)
            if check_running; then
                print_success "Application is running"
                exit 0
            else
                print_info "Application is not running"
                exit 1
            fi
            ;;
        --help)
            show_usage
            exit 0
            ;;
        *)
            print_error "Unknown option: $1"
            show_usage
            exit 1
            ;;
    esac
done

# Validate environment
if [[ ! "$ENVIRONMENT" =~ ^(development|production|testing)$ ]]; then
    print_error "Invalid environment: $ENVIRONMENT"
    print_info "Valid environments: development, production, testing"
    exit 1
fi

# Change to project directory
cd "$PROJECT_DIR"

# Check prerequisites
check_prerequisites

# Set file permissions
set_permissions

# Set environment variables
export FLASK_ENV="$ENVIRONMENT"
export FLASK_APP="app.py"

# Build Python command
PYTHON_CMD=("$VENV_PYTHON" "$SCRIPT_DIR/start.py" "--env" "$ENVIRONMENT" "--host" "$HOST" "--port" "$PORT")

if [[ "$DEBUG" == "true" ]]; then
    PYTHON_CMD+=("--debug")
fi

if [[ "$DAEMON" == "true" ]]; then
    PYTHON_CMD+=("--daemon")
fi

if [[ "$VALIDATE_ONLY" == "true" ]]; then
    PYTHON_CMD+=("--validate-only")
fi

if [[ "$CREATE_DIRS" == "true" ]]; then
    PYTHON_CMD+=("--create-dirs")
fi

# Check if already running (unless validating, creating dirs, or restarting)
if [[ "$VALIDATE_ONLY" == "false" && "$CREATE_DIRS" == "false" && "$RESTART_MODE" == "false" ]]; then
    if check_running; then
        print_error "Application is already running"
        print_info "Use --stop to stop the application first, or --restart to restart it"
        exit 1
    fi
fi

# Execute the command
print_info "Executing: ${PYTHON_CMD[*]}"
exec "${PYTHON_CMD[@]}"
