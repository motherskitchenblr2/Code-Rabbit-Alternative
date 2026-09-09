#!/data/data/com.termux/files/usr/bin/bash
# =============================================================================
# Git-Fix One-Click Installation for Android/Termux
# =============================================================================
# Run this script in Termux to install Git-Fix locally
# Usage: bash <(curl -fsSL https://raw.githubusercontent.com/motherskitchenblr2/Code-Rabbit-Alternative/main/deploy/termux/install.sh)
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
    echo -e "${MAGENTA}"
    cat << 'EOF'
    ██████╗ ██████╗ ██████╗ ███████╗███████╗███████╗████████╗
    ██╔══██╗██╔══██╗██╔══██╗██╔════╝██╔════╝██╔════╝╚══██╔══╝
    ██████╔╝██████╔╝██████╔╝█████╗  ███████╗█████╗     ██║   
    ██╔══██╗██╔═══╝ ██╔═══╝ ██╔══╝  ╚════██║██╔══╝     ██║   
    ██║  ██║██║     ██║     ███████╗███████║███████╗   ██║   
    ╚═╝  ╚═╝╚═╝     ╚═╝     ╚══════╝╚══════╝╚══════╝   ╚═╝   
EOF
    echo -e "${NC}"
    echo -e "${CYAN}    Git-Fix Termux Installer${NC}"
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

# Check if running in Termux
check_termux() {
    if [ ! -d "/data/data/com.termux" ]; then
        print_error "This script must be run in Termux on Android"
        exit 1
    fi
    print_success "Running in Termux environment"
}

# Update packages
update_packages() {
    print_step "Updating Termux packages..."
    pkg update -y && pkg upgrade -y
    print_success "Packages updated"
}

# Install dependencies
install_dependencies() {
    print_step "Installing dependencies..."
    
    # Core packages
    pkg install -y \
        git \
        python \
        nodejs-lts \
        rust \
        clang \
        make \
        cmake \
        pkg-config \
        libffi \
        openssl \
        libjpeg-turbo \
        libpng \
        freetype \
        zlib \
        postgresql \
        redis \
        qdrant \
        docker \
        docker-compose \
        vim \
        nano \
        htop \
        curl \
        wget \
        unzip \
        openssh \
        termux-api \
        proot-distro \
        tsu \
        openssl-tool
    
    print_success "Dependencies installed"
}

# Setup Python environment
setup_python() {
    print_step "Setting up Python environment..."
    
    # Upgrade pip
    pip install --upgrade pip setuptools wheel
    
    # Install Python packages
    pip install --no-cache-dir \
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
        pre-commit
    
    print_success "Python environment ready"
}

# Setup Node.js
setup_node() {
    print_step "Setting up Node.js..."
    
    # Install global packages
    npm install -g \
        npm@latest \
        yarn \
        pnpm \
        vite \
        typescript \
        ts-node \
        nodemon \
        pm2
    
    print_success "Node.js ready"
}

# Setup Rust
setup_rust() {
    print_step "Setting up Rust..."
    
    if ! command -v cargo &> /dev/null; then
        curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y
        source "$HOME/.cargo/env"
    fi
    
    # Install useful tools
    cargo install \
        cargo-watch \
        cargo-expand \
        cargo-audit \
        cargo-outdated \
        cargo-tree
    
    print_success "Rust ready"
}

# Setup PostgreSQL
setup_postgresql() {
    print_step "Setting up PostgreSQL..."
    
    # Initialize database
    if [ ! -d "$PREFIX/var/lib/postgresql" ]; then
        initdb "$PREFIX/var/lib/postgresql"
    fi
    
    # Start PostgreSQL
    pg_ctl -D "$PREFIX/var/lib/postgresql" -l logfile start
    
    # Create database and user
    createdb gitfix 2>/dev/null || true
    psql -d postgres -c "CREATE USER gitfix WITH PASSWORD 'gitfix_dev_password';" 2>/dev/null || true
    psql -d postgres -c "ALTER USER gitfix WITH SUPERUSER;" 2>/dev/null || true
    psql -d postgres -c "GRANT ALL PRIVILEGES ON DATABASE gitfix TO gitfix;" 2>/dev/null || true
    
    print_success "PostgreSQL ready"
}

# Setup Redis
setup_redis() {
    print_step "Setting up Redis..."
    
    # Start Redis
    redis-server --daemonize yes
    
    print_success "Redis ready"
}

# Setup Qdrant
setup_qdrant() {
    print_step "Setting up Qdrant..."
    
    # Create config directory
    mkdir -p "$HOME/.config/qdrant"
    
    # Create config
    cat > "$HOME/.config/qdrant/config.yaml" << 'EOF'
storage:
  storage_path: /data/data/com.termux/files/home/.local/share/qdrant/storage
  snapshots_path: /data/data/com.termux/files/home/.local/share/qdrant/snapshots

service:
  host: 0.0.0.0
  http_port: 6333
  grpc_port: 6334
  max_request_size_mb: 32
  enable_cors: true
  cors_allowed_origins: ["*"]

log_level: INFO
EOF
    
    print_success "Qdrant configured"
}

# Clone repository
clone_repo() {
    print_step "Cloning Git-Fix repository..."
    
    REPO_URL="https://github.com/motherskitchenblr2/Code-Rabbit-Alternative.git"
    INSTALL_DIR="$HOME/git-fix"
    
    if [ -d "$INSTALL_DIR" ]; then
        print_warning "Repository already exists, updating..."
        cd "$INSTALL_DIR"
        git pull
    else
        git clone "$REPO_URL" "$INSTALL_DIR"
        cd "$INSTALL_DIR"
    fi
    
    print_success "Repository cloned to $INSTALL_DIR"
}

# Setup environment
setup_environment() {
    print_step "Setting up environment..."
    
    cd "$HOME/git-fix"
    
    # Create .env from example
    if [ ! -f .env ]; then
        cp .env.example .env
        
        # Generate secure secrets
        SECRET_KEY=$(openssl rand -hex 32)
        WEBHOOK_SECRET=$(openssl rand -hex 32)
        
        sed -i "s/your-super-secret-key-change-in-production-min-32-chars/$SECRET_KEY/" .env
        sed -i "s/your-webhook-secret-min-32-chars/$WEBHOOK_SECRET/" .env
        
        # Update for local Termux
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

# Setup systemd-like services (using termux-services)
setup_services() {
    print_step "Setting up services..."
    
    # Create service directory
    mkdir -p "$HOME/.termux/boot"
    
    # Create startup script
    cat > "$HOME/.termux/boot/gitfix.sh" << 'EOF'
#!/data/data/com.termux/files/usr/bin/bash

# Start PostgreSQL
pg_ctl -D "$PREFIX/var/lib/postgresql" -l "$HOME/logs/postgresql.log" start

# Start Redis
redis-server --daemonize yes

# Start Qdrant
qdrant --config "$HOME/.config/qdrant/config.yaml" &

# Start API server
cd "$HOME/git-fix"
source "$HOME/.cargo/env" 2>/dev/null || true
export PATH="$HOME/.local/bin:$PATH"
python -m app &

# Start frontend dev server
cd "$HOME/git-fix/frontend"
npm run dev -- --host 0.0.0.0 --port 5173 &

echo "Git-Fix services started"
EOF
    chmod +x "$HOME/.termux/boot/gitfix.sh"
    
    # Create stop script
    cat > "$HOME/gitfix-stop.sh" << 'EOF'
#!/data/data/com.termux/files/usr/bin/bash

echo "Stopping Git-Fix services..."

# Kill processes
pkill -f "python -m app" 2>/dev/null || true
pkill -f "npm run dev" 2>/dev/null || true
pkill -f "qdrant" 2>/dev/null || true
redis-cli shutdown 2>/dev/null || true
pg_ctl -D "$PREFIX/var/lib/postgresql" stop 2>/dev/null || true

echo "Git-Fix services stopped"
EOF
    chmod +x "$HOME/gitfix-stop.sh"
    
    print_success "Services configured"
}

# Create launch script
create_launch_script() {
    print_step "Creating launch script..."
    
    cat > "$HOME/gitfix-start.sh" << 'EOF'
#!/data/data/com.termux/files/usr/bin/bash

echo "🚀 Starting Git-Fix..."

# Start services
/data/data/com.termux/files/usr/bin/bash "$HOME/.termux/boot/gitfix.sh"

echo ""
echo "🎉 Git-Fix is running!"
echo ""
echo "📱 Access points:"
echo "  📱 Frontend:  http://localhost:5173"
echo "  🔧 API:       http://localhost:5000"
echo "  🔧 API Health: http://localhost:5000/api/v1/health"
echo "  📊 Qdrant:    http://localhost:6333/dashboard"
echo ""
echo "🛑 To stop: bash ~/gitfix-stop.sh"
echo ""
echo "📋 Logs:"
echo "  tail -f ~/logs/app.log"
echo "  tail -f ~/logs/postgresql.log"
EOF
    chmod +x "$HOME/gitfix-start.sh"
    
    # Create alias
    echo 'alias gitfix-start="bash ~/gitfix-start.sh"' >> "$HOME/.bashrc"
    echo 'alias gitfix-stop="bash ~/gitfix-stop.sh"' >> "$HOME/.bashrc"
    echo 'alias gitfix-logs="tail -f ~/logs/app.log"' >> "$HOME/.bashrc"
    
    print_success "Launch scripts created"
}

# Main installation
main() {
    print_banner
    
    check_termux
    
    print_info "Starting Git-Fix installation for Termux..."
    echo ""
    
    # Update packages
    update_packages
    
    # Install dependencies
    install_dependencies
    
    # Setup languages
    setup_python
    setup_node
    setup_rust
    
    # Setup services
    setup_postgresql
    setup_redis
    setup_qdrant
    
    # Clone and setup
    clone_repo
    setup_environment
    install_frontend
    build_frontend
    
    # Setup services
    setup_services
    create_launch_script
    
    echo ""
    echo -e "${GREEN}═══════════════════════════════════════════${NC}"
    echo -e "${GREEN}✅ Git-Fix installation complete!${NC}"
    echo -e "${GREEN}═══════════════════════════════════════════${NC}"
    echo ""
    echo -e "${CYAN}🚀 To start Git-Fix:${NC}"
    echo -e "  ${CYAN}bash ~/gitfix-start.sh${NC}"
    echo ""
    echo -e "${CYAN}🛑 To stop Git-Fix:${NC}"
    echo -e "  ${CYAN}bash ~/gitfix-stop.sh${NC}"
    echo ""
    echo -e "${CYAN}🌐 Access points:${NC}"
    echo -e "  ${CYAN}📱 Dashboard: http://localhost:5173${NC}"
    echo -e "  ${CYAN}🔧 API:       http://localhost:5000${NC}"
    echo -e "  ${CYAN}📊 Qdrant:    http://localhost:6333/dashboard${NC}"
    echo ""
    echo -e "${YELLOW}Note: Restart Termux or run 'source ~/.bashrc' to use aliases${NC}"
}

# Run main
main "$@"
EOF
chmod +x /data/data/com.termux/files/home/Code-Rabbit-Alternative/deploy/termux/install.sh