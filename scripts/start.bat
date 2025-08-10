@echo off
REM Windows startup script for Networth Tracker
REM Provides convenient commands for starting the application on Windows

setlocal enabledelayedexpansion

REM Script directory
set "SCRIPT_DIR=%~dp0"
set "PROJECT_DIR=%SCRIPT_DIR%.."

REM Default values
set "ENVIRONMENT=production"
set "HOST=127.0.0.1"
set "PORT=5000"
set "DEBUG=false"
set "VALIDATE_ONLY=false"
set "CREATE_DIRS=false"

REM Function to show usage
:show_usage
echo Usage: %~nx0 [OPTIONS]
echo.
echo Options:
echo     -e, --env ENV           Environment (development^|production^|testing) [default: production]
echo     -h, --host HOST         Host to bind to [default: 127.0.0.1]
echo     -p, --port PORT         Port to bind to [default: 5000]
echo     -D, --debug             Enable debug mode
echo     -v, --validate          Validate configuration only
echo     -c, --create-dirs       Create directories only
echo     --help                  Show this help message
echo.
echo Examples:
echo     %~nx0                   # Start in production mode
echo     %~nx0 -e development    # Start in development mode
echo     %~nx0 -v                # Validate configuration
echo     %~nx0 -c                # Create directories
echo.
goto :eof

REM Function to print colored output (Windows doesn't support colors easily)
:print_info
echo [INFO] %~1
goto :eof

:print_success
echo [SUCCESS] %~1
goto :eof

:print_warning
echo [WARNING] %~1
goto :eof

:print_error
echo [ERROR] %~1
goto :eof

REM Function to check prerequisites
:check_prerequisites
call :print_info "Checking prerequisites..."

REM Check if Python 3 is available
python --version >nul 2>&1
if errorlevel 1 (
    call :print_error "Python 3 is required but not installed"
    exit /b 1
)

REM Check if virtual environment exists
if not exist "%PROJECT_DIR%\venv" (
    call :print_warning "Virtual environment not found at %PROJECT_DIR%\venv"
    call :print_info "Creating virtual environment..."
    python -m venv "%PROJECT_DIR%\venv"
)

REM Check if requirements are installed
if not exist "%PROJECT_DIR%\venv\Lib\site-packages\flask" (
    call :print_info "Installing requirements..."
    call "%PROJECT_DIR%\venv\Scripts\activate.bat"
    pip install -r "%PROJECT_DIR%\requirements.txt"
)

call :print_success "Prerequisites check completed"
goto :eof

REM Function to create directories
:create_directories
call :print_info "Creating necessary directories..."

if not exist "%PROJECT_DIR%\logs" mkdir "%PROJECT_DIR%\logs"
if not exist "%PROJECT_DIR%\backups" mkdir "%PROJECT_DIR%\backups"
if not exist "%PROJECT_DIR%\data" mkdir "%PROJECT_DIR%\data"
if not exist "%PROJECT_DIR%\temp" mkdir "%PROJECT_DIR%\temp"

call :print_success "Directories created"
goto :eof

REM Function to check if application is running
:check_running
set "PID_FILE=%PROJECT_DIR%\networth_tracker.pid"

if exist "%PID_FILE%" (
    set /p PID=<"%PID_FILE%"
    tasklist /FI "PID eq !PID!" 2>nul | find /I "!PID!" >nul
    if not errorlevel 1 (
        exit /b 0
    ) else (
        REM Stale PID file
        del "%PID_FILE%" 2>nul
        exit /b 1
    )
)

exit /b 1

REM Function to stop the application
:stop_application
set "PID_FILE=%PROJECT_DIR%\networth_tracker.pid"

if exist "%PID_FILE%" (
    set /p PID=<"%PID_FILE%"
    call :print_info "Stopping application (PID: !PID!)..."
    taskkill /PID !PID! /T /F >nul 2>&1
    del "%PID_FILE%" 2>nul
    call :print_success "Application stopped"
) else (
    call :print_info "Application is not running"
)
goto :eof

REM Parse command line arguments
:parse_args
if "%~1"=="" goto :end_parse

if "%~1"=="-e" (
    set "ENVIRONMENT=%~2"
    shift
    shift
    goto :parse_args
)
if "%~1"=="--env" (
    set "ENVIRONMENT=%~2"
    shift
    shift
    goto :parse_args
)
if "%~1"=="-h" (
    set "HOST=%~2"
    shift
    shift
    goto :parse_args
)
if "%~1"=="--host" (
    set "HOST=%~2"
    shift
    shift
    goto :parse_args
)
if "%~1"=="-p" (
    set "PORT=%~2"
    shift
    shift
    goto :parse_args
)
if "%~1"=="--port" (
    set "PORT=%~2"
    shift
    shift
    goto :parse_args
)
if "%~1"=="-D" (
    set "DEBUG=true"
    shift
    goto :parse_args
)
if "%~1"=="--debug" (
    set "DEBUG=true"
    shift
    goto :parse_args
)
if "%~1"=="-v" (
    set "VALIDATE_ONLY=true"
    shift
    goto :parse_args
)
if "%~1"=="--validate" (
    set "VALIDATE_ONLY=true"
    shift
    goto :parse_args
)
if "%~1"=="-c" (
    set "CREATE_DIRS=true"
    shift
    goto :parse_args
)
if "%~1"=="--create-dirs" (
    set "CREATE_DIRS=true"
    shift
    goto :parse_args
)
if "%~1"=="--stop" (
    call :stop_application
    exit /b 0
)
if "%~1"=="--status" (
    call :check_running
    if not errorlevel 1 (
        call :print_success "Application is running"
        exit /b 0
    ) else (
        call :print_info "Application is not running"
        exit /b 1
    )
)
if "%~1"=="--help" (
    call :show_usage
    exit /b 0
)

call :print_error "Unknown option: %~1"
call :show_usage
exit /b 1

:end_parse

REM Main execution starts here
call :parse_args %*

REM Validate environment
if not "%ENVIRONMENT%"=="development" if not "%ENVIRONMENT%"=="production" if not "%ENVIRONMENT%"=="testing" (
    call :print_error "Invalid environment: %ENVIRONMENT%"
    call :print_info "Valid environments: development, production, testing"
    exit /b 1
)

REM Change to project directory
cd /d "%PROJECT_DIR%"

REM Check prerequisites
call :check_prerequisites
if errorlevel 1 exit /b 1

REM Create directories
call :create_directories

REM Activate virtual environment
call "%PROJECT_DIR%\venv\Scripts\activate.bat"

REM Set environment variables
set "FLASK_ENV=%ENVIRONMENT%"
set "FLASK_APP=app.py"

REM Build Python command
set "PYTHON_CMD=python "%SCRIPT_DIR%start.py""
set "PYTHON_CMD=%PYTHON_CMD% --env %ENVIRONMENT%"
set "PYTHON_CMD=%PYTHON_CMD% --host %HOST%"
set "PYTHON_CMD=%PYTHON_CMD% --port %PORT%"

if "%DEBUG%"=="true" (
    set "PYTHON_CMD=%PYTHON_CMD% --debug"
)

if "%VALIDATE_ONLY%"=="true" (
    set "PYTHON_CMD=%PYTHON_CMD% --validate-only"
)

if "%CREATE_DIRS%"=="true" (
    set "PYTHON_CMD=%PYTHON_CMD% --create-dirs"
)

REM Check if already running (unless validating or creating dirs)
if "%VALIDATE_ONLY%"=="false" if "%CREATE_DIRS%"=="false" (
    call :check_running
    if not errorlevel 1 (
        call :print_error "Application is already running"
        call :print_info "Use --stop to stop the application first"
        exit /b 1
    )
)

REM Execute the command
call :print_info "Executing: %PYTHON_CMD%"
%PYTHON_CMD%