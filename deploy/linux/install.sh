#!/bin/bash
# =============================================================================
# Git-Fix One-Click Installation for Linux/Ubuntu
# =============================================================================
# Run this script to install Git-Fix on Ubuntu/Debian/Linux Mint/Pop!_OS/etc.
# Usage: bash <(curl -fsSL https://raw.githubusercontent.com/motherskitchenblr2/Code-Rabbit-Alternative/main/deploy/linux/install.sh)
# Or: wget -qO- https://raw.githubusercontent.com/motherskitchenblr2/Code-Rabbit-Alternative/main/deploy/linux/install.sh | bash
# =============================================================================

set -euo pipefail

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
MAGENTA='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m'

print_banner() {
    clear
    echo -e "${MAGENTA}"
    cat << 'EOF'
    ██████╗ ██████╗ ██████╗ ███████╗███████╗███████╗████████╗
    ██╔══██╗██╔══██╗██╔══██╗██╔════╝██╔════╝██╔════╝╚══██╔══╝
    ██████╔╝██████╔╝██████╔╝█████╗  ███████╗█████╗     ██║   
    ██╔══██╗██╔═══╝ ██╔═══╝ ██══╝  ╚════██║██╔══╝     ██║   
    ██║  ██║██║     ██║     ███████╗███████╗███████╗   ██║   
    ╚═╝  ╚═╝╚═╝     ╚═╝     ╚══════╝╚══════╝╚══════╝   ╚═╝   
EOF
    echo -e "${NC}"
    echo -e "${CYAN}    Git-Fix Linux Installer${NC}"
    echo -e "${CYAN}    Cyberpunk Code Review Engine${NC}"
    echo ""
}

print_step() {
    echo -e "${BLUE}[STEP]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[✓]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[!]${NC} $1"
}

print_error() {
    echo -e "${RED}[✗]${NC} $1"
}

print_info() {
    echo -e "${CYAN}[i]${NC} $1"
}

# Check if running as root
check_root() {
    if [[ $EUID -eq 0 ]]; then
        print_warning "Running as root. Some operations will use sudo automatically."
        SUDO=""
    else
        print_info "Running as user. Will use sudo when needed."
        SUDO="sudo"
    fi
}

# Detect OS
detect_os() {
    if [[ -f /etc/os-release ]]; then
        . /etc/os-release
        OS=$ID
        VERSION=$VERSION_ID
        print_info "Detected OS: $PRETTY_NAME"
    else
        print_error "Cannot detect OS. /etc/os-release not found."
        exit 1
    fi
}

# Update system
update_system() {
    print_step "Updating system packages..."
    
    case $OS in
        ubuntu|debian|linuxmint|pop|elementary|zorin)
            $SUDO apt-get update -y
            $SUDO apt-get upgrade -y
            $SUDO apt-get install -y curl wget git unzip software-properties-common apt-transport-https ca-certificates gnupg lsb-release
            ;;
        fedora|rhel|centos|rocky|almalinux)
            $SUDO dnf update -y
            $SUDO dnf install -y curl wget git unzip dnf-plugins-core
            ;;
        arch|manjaro|endeavouros)
            $SUDO pacman -Syu --noconfirm
            $SUDO pacman -S --noconfirm curl wget git unzip base-devel
            ;;
        opensuse*|sles)
            $SUDO zypper refresh
            $SUDO zypper update -y
            $SUDO zypper install -y curl wget git unzip
            ;;
        *)
            print_warning "Unsupported OS: $OS. Attempting generic installation..."
            ;;
    esac
    
    print_success "System packages updated"
}

# Install Docker
install_docker() {
    print_step "Installing Docker..."
    
    if command -v docker &> /dev/null; then
        print_info "Docker already installed: $(docker --version)"
        return 0
    fi
    
    # Install Docker using official script
    curl -fsSL https://get.docker.com | $SUDO bash
    
    # Add user to docker group
    $SUDO usermod -aG docker $USER
    
    # Enable and start Docker
    $SUDO systemctl enable docker
    $SUDO systemctl start docker
    
    # Configure Docker
    $SUDO mkdir -p /etc/docker
    $SUDO tee /etc/docker/daemon.json > /dev/null << 'EOF'
{
    "experimental": false,
    "features": {
        "buildkit": true
    },
    "log-driver": "json-file",
    "log-opts": {
        "max-size": "10m",
        "max-file": "3"
    },
    "storage-driver": "overlay2"
}
EOF
    
    $SUDO systemctl restart docker
    
    print_success "Docker installed and configured"
}

# Install Docker Compose
install_docker_compose() {
    print_step "Installing Docker Compose..."
    
    if command -v docker-compose &> /dev/null || docker compose version &> /dev/null; then
        print_info "Docker Compose already installed"
        return 0
    fi
    
    # Install Docker Compose v2
    $SUDO curl -SL "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
    $SUDO chmod +x /usr/local/bin/docker-compose
    
    print_success "Docker Compose installed"
}

# Install Python
install_python() {
    print_step "Installing Python..."
    
    case $OS in
        ubuntu|debian|linuxmint|pop|elementary|zorin)
            $SUDO apt-get install -y python3 python3-pip python3-venv python3-dev
            ;;
        fedora|rhel|centos|rocky|almalinux)
            $SUDO dnf install -y python3 python3-pip python3-devel
            ;;
        arch|manjaro|endeavouros)
            $SUDO pacman -S --noconfirm python python-pip
            ;;
        opensuse*|sles)
            $SUDO zypper install -y python3 python3-pip python3-devel
            ;;
    esac
    
    # Upgrade pip
    python3 -m pip install --upgrade pip setuptools wheel
    
    print_success "Python installed"
}

# Install Node.js
install_node() {
    print_step "Installing Node.js..."
    
    if command -v node &> /dev/null; then
        print_info "Node.js already installed: $(node --version)"
        return 0
    fi
    
    # Install Node.js via NodeSource
    curl -fsSL https://deb.nodesource.com/setup_lts.x | $SUDO -E bash -
    
    case $OS in
        ubuntu|debian|linuxmint|pop|elementary|zorin)
            $SUDO apt-get install -y nodejs
            ;;
        fedora|rhel|centos|rocky|almalinux)
            $SUDO dnf install -y nodejs
            ;;
        arch|manjaro|endeavouros)
            $SUDO pacman -S --noconfirm nodejs npm
            ;;
    esac
    
    # Install global packages
    $SUDO npm install -g npm@latest yarn pnpm vite typescript ts-node nodemon pm2
    
    print_success "Node.js installed"
}

# Install Rust
install_rust() {
    print_step "Installing Rust..."
    
    if command -v cargo &> /dev/null; then
        print_info "Rust already installed: $(cargo --version)"
        return 0
    fi
    
    curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y
    source "$HOME/.cargo/env"
    
    # Add to PATH permanently
    echo 'source "$HOME/.cargo/env"' >> ~/.bashrc
    echo 'source "$HOME/.cargo/env"' >> ~/.zshrc 2>/dev/null || true
    
    # Install useful tools
    source "$HOME/.cargo/env"
    cargo install cargo-watch cargo-expand cargo-audit cargo-outdated cargo-tree
    
    print_success "Rust installed"
}

# Install PostgreSQL
install_postgresql() {
    print_step "Installing PostgreSQL..."
    
    case $OS in
        ubuntu|debian|linuxmint|pop|elementary|zorin)
            $SUDO apt-get install -y postgresql postgresql-contrib postgresql-client
            ;;
        fedora|rhel|centos|rocky|almalinux)
            $SUDO dnf install -y postgresql-server postgresql-contrib
            $SUDO postgresql-setup --initdb
            ;;
        arch|manjaro|endeavouros)
            $SUDO pacman -S --noconfirm postgresql
            $SUDO su - postgres -c "initdb -D /var/lib/postgres/data"
            ;;
    esac
    
    # Start and enable PostgreSQL
    $SUDO systemctl enable postgresql
    $SUDO systemctl start postgresql
    
    # Create database and user
    $SUDO -u postgres psql -c "CREATE USER gitfix WITH PASSWORD 'gitfix_dev_password';" 2>/dev/null || true
    $SUDO -u postgres psql -c "CREATE DATABASE gitfix OWNER gitfix;" 2>/dev/null || true
    $SUDO -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE gitfix TO gitfix;" 2>/dev/null || true
    $SUDO -u postgres psql -c "ALTER USER gitfix WITH SUPERUSER;" 2>/dev/null || true
    
    print_success "PostgreSQL installed and configured"
}

# Install Redis
install_redis() {
    print_step "Installing Redis..."
    
    case $OS in
        ubuntu|debian|linuxmint|pop|elementary|zorin)
            $SUDO apt-get install -y redis-server
            ;;
        fedora|rhel|centos|rocky|almalinux)
            $SUDO dnf install -y redis
            ;;
        arch|manjaro|endeavouros)
            $SUDO pacman -S --noconfirm redis
            ;;
    esac
    
    # Configure Redis
    $SUDO sed -i 's/^# maxmemory .*/maxmemory 256mb/' /etc/redis/redis.conf 2>/dev/null || true
    $SUDO sed -i 's/^# maxmemory-policy .*/maxmemory-policy allkeys-lru/' /etc/redis/redis.conf 2>/dev/null || true
    
    # Enable and start Redis
    $SUDO systemctl enable redis-server 2>/dev/null || $SUDO systemctl enable redis
    $SUDO systemctl start redis-server 2>/dev/null || $SUDO systemctl start redis
    
    print_success "Redis installed and configured"
}

# Install Qdrant
install_qdrant() {
    print_step "Installing Qdrant..."
    
    if command -v qdrant &> /dev/null; then
        print_info "Qdrant already installed"
        return 0
    fi
    
    # Download and install Qdrant
    $SUDO mkdir -p /opt/qdrant
    cd /tmp
    $SUDO wget -q https://github.com/qdrant/qdrant/releases/latest/download/qdrant-x86_64-unknown-linux-gnu.tar.gz
    $SUDO tar -xzf qdrant-*.tar.gz -C /opt/qdrant --strip-components=1
    $SUDO ln -sf /opt/qdrant/qdrant /usr/local/bin/qdrant
    
    # Create config directory
    $SUDO mkdir -p /etc/qdrant
    $SUDO mkdir -p /var/lib/qdrant
    
    # Create config
    $SUDO tee /etc/qdrant/config.yaml > /dev/null << 'EOF'
storage:
  storage_path: /var/lib/qdrant/storage
  snapshots_path: /var/lib/qdrant/snapshots

service:
  host: 0.0.0.0
  http_port: 6333
  grpc_port: 6334
  max_request_size_mb: 32
  enable_cors: true
  cors_allowed_origins: ["*"]

log_level: INFO
EOF
    
    # Create systemd service
    $SUDO tee /etc/systemd/system/qdrant.service > /dev/null << 'EOF'
[Unit]
Description=Qdrant Vector Database
After=network.target

[Service]
Type=simple
User=root
ExecStart=/usr/local/bin/qdrant --config /etc/qdrant/config.yaml
Restart=on-failure
RestartSec=5
LimitNOFILE=65536

[Install]
WantedBy=multi-user.target
EOF
    
    $SUDO systemctl daemon-reload
    $SUDO systemctl enable qdrant
    $SUDO systemctl start qdrant
    
    print_success "Qdrant installed and configured"
}

# Install Git
install_git() {
    print_step "Installing Git..."
    
    case $OS in
        ubuntu|debian|linuxmint|pop|elementary|zorin)
            $SUDO apt-get install -y git
            ;;
        fedora|rhel|centos|rocky|almalinux)
            $SUDO dnf install -y git
            ;;
        arch|manjaro|endeavouros)
            $SUDO pacman -S --noconfirm git
            ;;
    esac
    
    print_success "Git installed"
}

# Clone repository
clone_repo() {
    print_step "Cloning Git-Fix repository..."
    
    REPO_URL="https://github.com/motherskitchenblr2/Code-Rabbit-Alternative.git"
    INSTALL_DIR="$HOME/git-fix"
    
    if [[ -d "$INSTALL_DIR" ]]; then
        print_warning "Repository already exists, updating..."
        cd "$INSTALL_DIR"
        git pull
    else
        git clone "https://github.com/motherskitchenblr2/Code-Rabbit-Alternative.git" "$INSTALL_DIR"
        cd "$INSTALL_DIR"
    fi
    
    print_success "Repository cloned to $INSTALL_DIR"
}

# Setup environment
setup_environment() {
    print_step "Setting up environment..."
    
    cd "$HOME/git-fix"
    
    if [[ ! -f .env ]]; then
        cp .env.example .env
        
        # Generate secure secrets
        SECRET_KEY=$(openssl rand -hex 32)
        WEBHOOK_SECRET=$(openssl rand -hex 32)
        
        sed -i "s/your-super-secret-key-change-in-production-min-32-chars/$SECRET_KEY/" .env
        sed -i "s/your-webhook-secret-min-32-chars/$WEBHOOK_SECRET/" .env
        
        # Update for local
        sed -i 's|postgresql://gitfix:gitfix_dev_password@postgres:5432/gitfix|postgresql://gitfix:gitfix_dev_password@localhost:5432/gitfix|' .env
        sed -i 's|redis://redis:6379/0|redis://localhost:6379/0|' .env
        sed -i 's|http://qdrant:6333|http://localhost:6333|' .env
        sed -i 's|redis://redis:6379/1|redis://localhost:6379/1|' .env
        sed -i 's|redis://redis:6379/2|redis://localhost:6379/2|' .env
        
        print_success "Environment configured"
    else
        print_info ".env already exists"
    fi
}

# Install frontend
install_frontend() {
    print_step "Installing frontend dependencies..."
    
    cd "$HOME/git-fix/frontend"
    npm ci --prefer-offline --no-audit --no-fund
    
    print_success "Frontend dependencies installed"
}

# Build frontend
build_frontend() {
    print_step "Building frontend..."
    
    cd "$HOME/git-fix/frontend"
    npm run build
    
    print_success "Frontend built"
}

# Install Python dependencies
install_python_deps() {
    print_step "Installing Python dependencies..."
    
    cd "$HOME/git-fix"
    
    # Upgrade pip
    python3 -m pip install --upgrade pip setuptools wheel
    
    # Install dependencies
    pip3 install --no-cache-dir \
        flask \
        flask-cors \
        flask-limiter \
        flask-talisman \
        pydantic \
        pydantic-settings \
        pyyaml \
        sqlalchemy \
        alembic \
        psycopg2-binary \
        redis \
        celery \
        flower \
        qdrant-client \
        python-jose \
        passlib \
        bcrypt \
        httpx \
        requests \
        python-dotenv \
        click \
        rich \
        pytest \
        pytest-asyncio \
        pytest-cov \
        pytest-mock \
        httpx \
        ruff \
        black \
        mypy \
        pre-commit \
        gunicorn \
        mangum
    
    print_success "Python dependencies installed"
}

# Create systemd services
create_systemd_services() {
    print_step "Creating systemd services..."
    
    # API service
    $SUDO tee /etc/systemd/system/gitfix-api.service > /dev/null << EOF
[Unit]
Description=Git-Fix API Server
After=network.target postgresql.service redis.service qdrant.service
Requires=postgresql.service redis.service qdrant.service

[Service]
Type=simple
User=$USER
WorkingDirectory=$HOME/git-fix
Environment=PATH=/home/$USER/.local/bin:/usr/local/bin:/usr/bin:/bin
EnvironmentFile=$HOME/git-fix/.env
ExecStart=/home/$USER/.local/bin/gunicorn --bind 0.0.0.0:5000 --workers 4 --worker-class gthread --threads 2 --timeout 120 --keep-alive 5 --max-requests 1000 --max-requests-jitter 100 --preload --access-logfile - --error-logfile - --log-level info app:app
Restart=on-failure
RestartSec=5
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF

    # Worker service
    $SUDO tee /etc/systemd/system/gitfix-worker.service > /dev/null << EOF
[Unit]
Description=Git-Fix Celery Worker
After=network.target redis.service qdrant.service
Requires=redis.service qdrant.service

[Service]
Type=simple
User=$USER
WorkingDirectory=$HOME/git-fix
Environment=PATH=/home/$USER/.local/bin:/usr/local/bin:/usr/bin:/bin
EnvironmentFile=$HOME/git-fix/.env
ExecStart=/home/$USER/.local/bin/celery -A app.celery worker --loglevel=info --concurrency=4 --pool=prefork --autoscale=4,1 --max-tasks-per-child=100
Restart=on-failure
RestartSec=5
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF

    # Scheduler service
    $SUDO tee /etc/systemd/system/gitfix-scheduler.service > /dev/null << EOF
[Unit]
Description=Git-Fix Celery Beat Scheduler
After=network.target redis.service
Requires=redis.service

[Service]
Type=simple
User=$USER
WorkingDirectory=$HOME/git-fix
Environment=PATH=/home/$USER/.local/bin:/usr/local/bin:/usr/bin:/bin
EnvironmentFile=$HOME/git-fix/.env
ExecStart=/home/$USER/.local/bin/celery -A app.celery beat --loglevel=info --scheduler celery.beat.PersistentScheduler
Restart=on-failure
RestartSec=5
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF

    # Frontend service
    $SUDO tee /etc/systemd/system/gitfix-frontend.service > /dev/null << EOF
[Unit]
Description=Git-Fix Frontend (Vite Dev Server)
After=network.target

[Service]
Type=simple
User=$USER
WorkingDirectory=$HOME/git-fix/frontend
ExecStart=/usr/bin/npm run dev -- --host 0.0.0.0 --port 5173
Restart=on-failure
RestartSec=5
StandardOutput=journal
StandardError=journal
Environment=NODE_ENV=development

[Install]
WantedBy=multi-user.target
EOF

    # Reload systemd
    $SUDO systemctl daemon-reload
    
    # Enable services
    $SUDO systemctl enable gitfix-api gitfix-worker gitfix-scheduler gitfix-frontend
    
    print_success "Systemd services created and enabled"
}

# Create management scripts
create_management_scripts() {
    print_step "Creating management scripts..."
    
    # Start script
    cat > "$HOME/gitfix-start.sh" << 'EOF'
#!/bin/bash

echo "🚀 Starting Git-Fix services..."

# Start services
$SUDO systemctl start postgresql redis qdrant
$SUDO systemctl start gitfix-api gitfix-worker gitfix-scheduler gitfix-frontend

echo ""
echo "🎉 Git-Fix services started!"
echo ""
echo "📱 Access points:"
echo "  📱 Dashboard: http://localhost:5173"
echo "  🔧 API:       http://localhost:5000"
echo "  🔧 API Health: http://localhost:5000/api/v1/health"
echo "  📊 Qdrant:    http://localhost:6333/dashboard"
echo "  🌸 Flower:    http://localhost:5555"
echo ""
echo "🛑 To stop: bash ~/gitfix-stop.sh"
echo ""
echo "📋 Logs:"
echo "  sudo journalctl -u gitfix-api -f"
echo "  sudo journalctl -u gitfix-worker -f"
echo "  sudo journalctl -u gitfix-frontend -f"
EOF
    chmod +x "$HOME/gitfix-start.sh"
    
    # Stop script
    cat > "$HOME/gitfix-stop.sh" << 'EOF'
#!/bin/bash

echo "Stopping Git-Fix services..."

sudo systemctl stop gitfix-frontend gitfix-scheduler gitfix-worker gitfix-api
sudo systemctl stop qdrant redis postgresql

echo "Git-Fix services stopped"
EOF
    chmod +x "$HOME/gitfix-stop.sh"
    
    # Status script
    cat > "$HOME/gitfix-status.sh" << 'EOF'
#!/bin/bash

echo "🔍 Git-Fix Service Status"
echo "========================="

services=("postgresql" "redis" "qdrant" "gitfix-api" "gitfix-worker" "gitfix-scheduler" "gitfix-frontend")

for service in "${services[@]}"; do
    if systemctl is-active --quiet "$service"; then
        echo -e "\033[0;32m[✓]\033[0m $service: \033[0;32mACTIVE\033[0m"
    else
        echo -e "\033[0;31m[✗]\033[0m $service: \033[0;31mINACTIVE\033[0m"
    fi
done

echo ""
echo "📊 Resource Usage:"
docker stats --no-stream --format "table {{.Container}}\t{{.CPUPerc}}\t{{.MemUsage}}\t{{.NetIO}}" 2>/dev/null || true
EOF
    chmod +x "$HOME/gitfix-status.sh"
    
    # Add aliases
    echo 'alias gitfix-start="bash ~/gitfix-start.sh"' >> ~/.bashrc
    echo 'alias gitfix-stop="bash ~/gitfix-stop.sh"' >> ~/.bashrc
    echo 'alias gitfix-status="bash ~/gitfix-status.sh"' >> ~/.bashrc
    echo 'alias gitfix-logs="sudo journalctl -u gitfix-api -f"' >> ~/.bashrc
    
    # Add to zshrc if exists
    [[ -f ~/.zshrc ]] && {
        echo 'alias gitfix-start="bash ~/gitfix-start.sh"' >> ~/.zshrc
        echo 'alias gitfix-stop="bash ~/gitfix-stop.sh"' >> ~/.zshrc
        echo 'alias gitfix-status="bash ~/gitfix-status.sh"' >> ~/.zshrc
        echo 'alias gitfix-logs="sudo journalctl -u gitfix-api -f"' >> ~/.zshrc
    }
    
    print_success "Management scripts created"
}

# Create desktop entry (for GUI environments)
create_desktop_entry() {
    print_step "Creating desktop entry..."
    
    mkdir -p "$HOME/.local/share/applications"
    
    cat > "$HOME/.local/share/applications/gitfix.desktop" << EOF
[Desktop Entry]
Version=1.0
Type=Application
Name=Git-Fix
Comment=Cyberpunk Code Review Engine
Exec=bash $HOME/gitfix-start.sh
Icon=$HOME/git-fix/assets/icon.png
Terminal=true
Categories=Development;
StartupNotify=true
Categories=Development;IDE;
EOF
    
    print_success "Desktop entry created"
}

# Main installation
main() {
    print_banner
    
    check_root
    detect_os
    
    print_info "Starting Git-Fix installation for Linux..."
    echo ""
    
    # Update system
    update_system
    
    # Install dependencies
    install_docker
    install_docker_compose
    install_python
    install_node
    install_rust
    install_postgresql
    install_redis
    install_qdrant
    install_git
    
    # Clone and setup
    clone_repo
    setup_environment
    install_frontend
    build_frontend
    install_python_deps
    
    # Create services
    create_systemd_services
    create_management_scripts
    create_desktop_entry
    
    # Final message
    echo ""
    echo -e "${GREEN}═══════════════════════════════════════════${NC}"
    echo -e "${GREEN}✅ Git-Fix installation complete!${NC}"
    echo -e "${GREEN}═══════════════════════════════════════════${NC}"
    echo ""
    echo -e "${CYAN}🚀 To start Git-Fix:${NC}"
    echo -e "  ${CYAN}bash ~/gitfix-start.sh${NC}"
    echo -e "  Or: ${CYAN}sudo systemctl start gitfix-api gitfix-worker gitfix-scheduler gitfix-frontend${NC}"
    echo ""
    echo -e "${CYAN}🛑 To stop Git-Fix:${NC}"
    echo -e "  ${CYAN}bash ~/gitfix-stop.sh${NC}"
    echo -e "  Or: ${CYAN}sudo systemctl stop gitfix-frontend gitfix-scheduler gitfix-worker gitfix-api${NC}"
    echo ""
    echo -e "${CYAN}📊 Status: ${CYAN}bash ~/gitfix-status.sh${NC}"
    echo -e "${CYAN}📋 Logs: ${CYAN}sudo journalctl -u gitfix-api -f${NC}"
    echo ""
    echo -e "${CYAN}🌐 Access points:${NC}"
    echo -e "  ${CYAN}📱 Dashboard: http://localhost:5173${NC}"
    echo -e "  ${CYAN}🔧 API:       http://localhost:5000${NC}"
    echo -e "  🔧 API Health: http://localhost:5000/api/v1/health${NC}"
    echo -e "  📊 Qdrant:    http://localhost:6333/dashboard${NC}"
    echo -e "  🌸 Flower:    http://localhost:5555${NC}"
    echo ""
    echo -e "${YELLOW}Note: You may need to log out and back in for group changes to take effect${NC}"
    echo -e "${YELLOW}Or run: newgrp docker${NC}"
}

# Run main
main "$@"
EOF
chmod +x /data/data/com.termux/files/home/Code-Rabbit-Alternative/deploy/linux/install.sh