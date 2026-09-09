<# 
.SYNOPSIS
    Git-Fix One-Click Installation for Windows PowerShell
    
.DESCRIPTION
    This script installs Git-Fix on Windows with all dependencies including
    Docker, PostgreSQL, Redis, Qdrant, Python, Node.js, and the Git-Fix application.
    
.USAGE
    PowerShell -ExecutionPolicy Bypass -File install.ps1
    Or run directly: irm https://raw.githubusercontent.com/motherskitchenblr2/Code-Rabbit-Alternative/main/deploy/windows/install.ps1 | iex

.NOTES
    Requires: Windows 10/11, Administrator privileges
    Author: Git-Fix Team
    Version: 1.0.0
#>

# =============================================================================
# Configuration
# =============================================================================
$ErrorActionPreference = "Stop"
$ProgressPreference = "SilentlyContinue"

# Colors
$RED = [ConsoleColor]::Red
$GREEN = [ConsoleColor]::Green
$YELLOW = [ConsoleColor]::Yellow
$BLUE = [ConsoleColor]::Blue
$MAGENTA = [ConsoleColor]::Magenta
$CYAN = [ConsoleColor]::Cyan
$WHITE = [ConsoleColor]::White

# =============================================================================
# Helper Functions
# =============================================================================
function Write-Banner {
    Clear-Host
    Write-Host @"
    ██████╗ ██████╗ ██████╗ ███████╗███████╗███████╗████████╗
    ██╔══██╗██╔══██╗██╔══██╗██╔════╝██╔════╝██╔════╝╚══██╔══╝
    ██████╔╝██████╔╝██████╔╝█████╗  ███████╗█████╗     ██║   
    ██══██╗██═══╝ ██╔═══╝ ██╔══╝  ╚════██║██╔══╝     ██║   
    ██║  ██║██║     ██║     ███████╗███████║███████╗   ██║   
    ╚═╝  ╚═╝╚═╝     ╚═╝     ╚══════╝╚══════╝╚══════╝   ╚═╝   
" -ForegroundColor $MAGENTA
    Write-Host "    Git-Fix Windows Installer" -ForegroundColor $CYAN
    Write-Host "    Cyberpunk Code Review Engine" -ForegroundColor $CYAN
    Write-Host ""
}

function Write-Step {
    param([string]$Message)
    Write-Host "[STEP] $Message" -ForegroundColor $BLUE
}

function Write-Success {
    param([string]$Message)
    Write-Host "[✓] $Message" -ForegroundColor $GREEN
}

function Write-Warning {
    param([string]$Message)
    Write-Host "[!] $Message" -ForegroundColor $YELLOW
}

function Write-Error {
    param([string]$Message)
    Write-Host "[✗] $Message" -ForegroundColor $RED
}

function Write-Info {
    param([string]$Message)
    Write-Host "[i] $Message" -ForegroundColor $CYAN
}

function Test-Admin {
    $currentUser = [Security.Principal.WindowsIdentity]::GetCurrent()
    $principal = New-Object Security.Principal.WindowsPrincipal($currentUser)
    return $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
}

function Check-Chocolatey {
    if (Get-Command choco -ErrorAction SilentlyContinue) {
        Write-Success "Chocolatey found: $(choco --version)"
        return $true
    }
    return $false
}

function Install-Chocolatey {
    Write-Step "Installing Chocolatey..."
    Set-ExecutionPolicy Bypass -Scope Process -Force
    [System.Net.ServicePointManager]::SecurityProtocol = [System.Net.ServicePointManager]::SecurityProtocol -bor 3072
    iex ((New-Object System.Net.WebClient).DownloadString('https://community.chocolatey.org/install.ps1'))
    refreshenv
    Write-Success "Chocolatey installed"
}

function Install-Packages {
    Write-Step "Installing required packages via Chocolatey..."
    
    $packages = @(
        "git",
        "docker-desktop",
        "docker-cli",
        "docker-compose",
        "python",
        "nodejs-lts",
        "rust",
        "git",
        "vscode",
        "postgresql",
        "redis-64",
        "qdrant",
        "openssl",
        "curl",
        "wget",
        "unzip",
        "7zip",
        "vim",
        "git-fix"
    )
    
    foreach ($pkg in $packages) {
        Write-Info "Installing $pkg..."
        try {
            choco install $pkg -y --no-progress
            Write-Success "Installed $pkg"
        }
        catch {
            Write-Warning "Failed to install $pkg: $_"
        }
    }
    
    refreshenv
}

function Install-Scoop {
    Write-Step "Installing Scoop (alternative package manager)..."
    Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser -Force
    iex (irm get.scoop.sh)
    Write-Success "Scoop installed"
}

function Install-With-Scoop {
    Write-Step "Installing additional packages via Scoop..."
    
    $packages = @(
        "rust",
        "nodejs-lts",
        "python",
        "postgresql",
        "redis",
        "qdrant",
        "docker-cli",
        "docker-compose",
        "kubectl",
        "helm",
        "terraform",
        "awscli",
        "azure-cli"
    )
    
    foreach ($pkg in $packages) {
        Write-Info "Installing $pkg via Scoop..."
        try {
            scoop install $pkg
        }
        catch {
            Write-Warning "Failed to install $pkg via Scoop: $_"
        }
    }
}

function Install-Docker {
    Write-Step "Setting up Docker..."
    
    # Enable WSL 2
    Write-Step "Enabling WSL 2..."
    dism.exe /online /enable-feature /featurename:Microsoft-Windows-Subsystem-Linux /all /norestart
    dism.exe /online /enable-feature /featurename:VirtualMachinePlatform /all /norestart
    
    # Install Docker Desktop
    if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
        choco install docker-desktop -y --no-progress
    }
    
    # Configure Docker
    Write-Step "Configuring Docker..."
    $dockerConfig = @{
        "experimental" = "disabled"
        "features" = @{
            "buildkit" = $true
        }
        "log-driver" = "json-file"
        "log-opts" = @{
            "max-size" = "10m"
            "max-file" = "3"
        }
    }
    
    $configPath = "$env:USERPROFILE\.docker\config.json"
    if (-not (Test-Path $configPath)) {
        New-Item -ItemType Directory -Force -Path (Split-Path $configPath)
        $dockerConfig | ConvertTo-Json -Depth 5 | Out-File -FilePath $configPath -Encoding UTF8
    }
    
    Write-Success "Docker configured"
}

function Install-Python {
    Write-Step "Setting up Python..."
    
    if (-not (Get-Command python -ErrorAction SilentlyContinue)) {
        choco install python -y --no-progress
    }
    
    # Upgrade pip
    python -m pip install --upgrade pip setuptools wheel
    
    # Install Python packages
    $pythonPackages = @(
        "flask",
        "flask-cors",
        "flask-limiter",
        "flask-talisman",
        "pydantic",
        "pydantic-settings",
        "pyyaml",
        "sqlalchemy",
        "alembic",
        "psycopg2-binary",
        "redis",
        "celery",
        "flower",
        "qdrant-client",
        "python-jose",
        "passlib",
        "bcrypt",
        "httpx",
        "requests",
        "python-dotenv",
        "click",
        "rich",
        "pytest",
        "pytest-asyncio",
        "pytest-cov",
        "pytest-mock",
        "httpx",
        "ruff",
        "black",
        "mypy",
        "pre-commit",
        "gunicorn",
        "mangum"
    )
    
    foreach ($pkg in $pythonPackages) {
        pip install --no-cache-dir $pkg
    }
    
    Write-Success "Python environment ready"
}

function Install-Node {
    Write-Step "Setting up Node.js..."
    
    # Install nvm-windows
    if (-not (Get-Command nvm -ErrorAction SilentlyContinue)) {
        scoop install nvm
    }
    
    # Install Node.js LTS
    nvm install lts
    nvm use lts
    
    # Install global packages
    npm install -g npm@latest yarn pnpm vite typescript ts-node nodemon pm2
    
    Write-Success "Node.js ready"
}

function Install-Rust {
    Write-Step "Setting up Rust..."
    
    if (-not (Get-Command cargo -ErrorAction SilentlyContinue)) {
        $rustupUrl = "https://static.rust-lang.org/rustup/dist/x86_64-pc-windows-msvc/rustup-init.exe"
        $installer = "$env:TEMP\rustup-init.exe"
        Invoke-WebRequest -Uri $rustupUrl -OutFile $installer
        & $installer -y
        Remove-Item $installer
        refreshenv
    }
    
    # Install useful tools
    cargo install cargo-watch cargo-expand cargo-audit cargo-outdated cargo-tree
    
    Write-Success "Rust ready"
}

function Setup-PostgreSQL {
    Write-Step "Setting up PostgreSQL..."
    
    # Initialize database if needed
    $pgData = "$env:ProgramFiles\PostgreSQL\16\data"
    if (-not (Test-Path $pgData)) {
        & "$env:ProgramFiles\PostgreSQL\16\bin\initdb.exe" -D $pgData -U postgres -A scram-sha-256
    }
    
    # Start service
    Start-Service postgresql-x64-16 -ErrorAction SilentlyContinue
    
    # Create database and user
    $sql = @"
CREATE USER gitfix WITH PASSWORD 'gitfix_dev_password';
CREATE DATABASE gitfix OWNER gitfix;
GRANT ALL PRIVILEGES ON DATABASE gitfix TO gitfix;
ALTER USER gitfix WITH SUPERUSER;
"@
    
    & "C:\Program Files\PostgreSQL\16\bin\psql.exe" -U postgres -c $sql 2>$null
    
    Write-Success "PostgreSQL configured"
}

function Setup-Redis {
    Write-Step "Setting up Redis..."
    
    # Start Redis service
    Start-Service redis -ErrorAction SilentlyContinue
    
    Write-Success "Redis configured"
}

function Setup-Qdrant {
    Write-Step "Setting up Qdrant..."
    
    $qdrantDir = "$env:USERPROFILE\.config\qdrant"
    New-Item -ItemType Directory -Force -Path $qdrantDir
    
    $config = @"
storage:
  storage_path: $env:USERPROFILE\.local\share\qdrant\storage
  snapshots_path: $env:USERPROFILE\.local\share\qdrant\snapshots

service:
  host: 0.0.0.0
  http_port: 6333
  grpc_port: 6334
  max_request_size_mb: 32
  enable_cors: true
  cors_allowed_origins: ["*"]

log_level: INFO
"@
    
    $configPath = "$env:USERPROFILE\.config\qdrant\config.yaml"
    $config | Out-File -FilePath $configPath -Encoding UTF8
    
    Write-Success "Qdrant configured"
}

function CloneRepository {
    Write-Step "Cloning Git-Fix repository..."
    
    $repoUrl = "https://github.com/motherskitchenblr2/Code-Rabbit-Alternative.git"
    $installDir = "$env:USERPROFILE\git-fix"
    
    if (Test-Path $installDir) {
        Write-Warning "Repository already exists, updating..."
        Set-Location $installDir
        git pull
    }
    else {
        git clone "https://github.com/motherskitchenblr2/Code-Rabbit-Alternative.git" $installDir
        Set-Location $installDir
    }
    
    Write-Success "Repository cloned to $installDir"
}

function SetupEnvironment {
    Write-Step "Setting up environment..."
    
    Set-Location $installDir
    
    if (-not (Test-Path ".env")) {
        Copy-Item ".env.example" ".env"
        
        # Generate secure secrets
        $secretKey = [System.Convert]::ToBase64String((1..32 | ForEach-Object { Get-Random -Maximum 256 }))
        $webhookSecret = [System.Convert]::ToBase64String((1..32 | ForEach-Object { Get-Random -Maximum 256 }))
        
        (Get-Content .env) -replace 'your-super-secret-key-change-in-production-min-32-chars', $secretKey | Set-Content .env
        (Get-Content .env) -replace 'your-webhook-secret-min-32-chars', $webhookSecret | Set-Content .env
        
        # Update for local Windows
        (Get-Content .env) -replace 'postgresql://gitfix:gitfix_dev_password@postgres:5432/gitfix', 'postgresql://gitfix:gitfix_dev_password@localhost:5432/gitfix' | Set-Content .env
        (Get-Content .env) -replace 'redis://redis:6379/0', 'redis://localhost:6379/0' | Set-Content .env
        (Get-Content .env) -replace 'http://qdrant:6333', 'http://localhost:6333' | Set-Content .env
        (Get-Content .env) -replace 'redis://redis:6379/1', 'redis://localhost:6379/1' | Set-Content .env
        (Get-Content .env) -replace 'redis://redis:6379/2', 'redis://localhost:6379/2' | Set-Content .env
        
        Write-Success "Environment configured"
    }
    else {
        Write-Info ".env already exists"
    }
}

function InstallFrontend {
    Write-Step "Installing frontend dependencies..."
    
    Set-Location "$installDir/frontend"
    npm ci --prefer-offline --no-audit --no-fund
    
    Write-Success "Frontend dependencies installed"
}

function BuildFrontend {
    Write-Step "Building frontend..."
    
    Set-Location "$installDir/frontend"
    npm run build
    
    Write-Success "Frontend built"
}

function SetupServices {
    Write-Step "Setting up Windows services..."
    
    # Create startup script
    $startupScript = @"
@echo off
echo Starting Git-Fix services...

REM Start PostgreSQL
net start postgresql-x64-16

REM Start Redis
net start redis

REM Start Qdrant
start /b qdrant.exe --config "%USERPROFILE%\.config\qdrant\config.yaml"

REM Start API server
cd %USERPROFILE%\git-fix
python -m app

REM Start frontend dev server
cd %USERPROFILE%\git-fix\frontend
npm run dev -- --host 0.0.0.0 --port 5173

echo Git-Fix services started
"@
    
    $startupPath = "$env:USERPROFILE\gitfix-start.bat"
    $startupScript | Out-File -FilePath $startupPath -Encoding UTF8
    
    # Create stop script
    $stopScript = @"
@echo off
echo Stopping Git-Fix services...

taskkill /F /IM python.exe 2>nul
taskkill /F /IM node.exe 2>nul
taskkill /IM qdrant.exe 2>nul
net stop redis
net stop postgresql-x64-16

echo Git-Fix services stopped
"@
    
    $stopPath = "$env:USERPROFILE\gitfix-stop.bat"
    $stopScript | Out-File -FilePath $stopPath -Encoding UTF8
    
    Write-Success "Service scripts created"
}

function CreateShortcuts {
    Write-Step "Creating desktop shortcuts..."
    
    $shell = New-Object -ComObject WScript.Shell
    
    # Start shortcut
    $shortcut = $shell.CreateShortcut("$env:USERPROFILE\Desktop\Git-Fix Start.lnk")
    $shortcut.TargetPath = "$env:USERPROFILE\gitfix-start.bat"
    $shortcut.WorkingDirectory = "$env:USERPROFILE\git-fix"
    $shortcut.IconLocation = "$env:USERPROFILE\git-fix\assets\icon.ico"
    $shortcut.Save()
    
    $shortcut = $shell.CreateShortcut("$env:USERPROFILE\Desktop\Git-Fix Stop.lnk")
    $shortcut.TargetPath = "$env:USERPROFILE\gitfix-stop.bat"
    $shortcut.WorkingDirectory = "$env:USERPROFILE\git-fix"
    $shortcut.Save()
    
    Write-Success "Desktop shortcuts created"
}

# =============================================================================
# Main Installation
# =============================================================================
function Main {
    Write-Banner
    
    # Check admin
    if (-not (Test-Admin)) {
        Write-Error "This script requires Administrator privileges. Please run PowerShell as Administrator."
        exit 1
    }
    
    Write-Info "Starting Git-Fix installation for Windows..."
    
    # Install Chocolatey
    if (-not (Check-Chocolatey)) {
        Install-Chocolatey
    }
    
    # Install Scoop
    if (-not (Get-Command scoop -ErrorAction SilentlyContinue)) {
        Install-Scoop
    }
    
    # Install packages
    Install-Packages
    Install-With-Scoop
    
    # Install components
    Install-Docker
    Install-Python
    Install-Node
    Install-Rust
    
    # Setup services
    Setup-PostgreSQL
    Setup-Redis
    Setup-Qdrant
    
    # Clone and setup
    CloneRepository
    SetupEnvironment
    InstallFrontend
    
    # Build frontend
    Write-Step "Building frontend..."
    Set-Location "$installDir/frontend"
    npm run build
    
    # Setup services
    SetupServices
    CreateShortcuts
    
    # Final message
    Write-Host ""
    Write-Host "═══════════════════════════════════════════" -ForegroundColor $GREEN
    Write-Host "✅ Git-Fix installation complete!" -ForegroundColor $GREEN
    Write-Host "═══════════════════════════════════════════" -ForegroundColor $GREEN
    Write-Host ""
    Write-Host "🚀 To start Git-Fix:" -ForegroundColor $CYAN
    Write-Host "  Double-click 'Git-Fix Start' on Desktop" -ForegroundColor $CYAN
    Write-Host "  Or run: .\gitfix-start.bat" -ForegroundColor $CYAN
    Write-Host ""
    Write-Host "🛑 To stop Git-Fix:" -ForegroundColor $CYAN
    Write-Host "  Double-click 'Git-Fix Stop' on Desktop" -ForegroundColor $CYAN
    Write-Host ""
    Write-Host "🌐 Access points:" -ForegroundColor $CYAN
    Write-Host "  📱 Dashboard: http://localhost:5173" -ForegroundColor $CYAN
    Write-Host "  🔧 API:       http://localhost:5000" -ForegroundColor $CYAN
    Write-Host "  📊 Qdrant:    http://localhost:6333/dashboard" -ForegroundColor $CYAN
    Write-Host ""
    Write-Host "🔧 Default credentials:" -ForegroundColor $YELLOW
    Write-Host "  Admin:    admin@gitfix.io / gitfix2024!" -ForegroundColor $YELLOW
    Write-Host "  Reviewer: reviewer@gitfix.io / gitfix2024!" -ForegroundColor $YELLOW
}

# Run main
try {
    Main
}
catch {
    Write-Error "Installation failed: $_"
    exit 1
}