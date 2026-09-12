#!/data/data/com.termux/files/usr/glibc/bin/bash
# =============================================================================
# Git-Fix 1-Click Local Deployment Script
# =============================================================================
# This script sets up and deploys the entire Git-Fix stack locally with one command.
# Usage: ./deploy.sh [options]
# =============================================================================

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
MAGENTA='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Cyberpunk banner
print_banner() {
    echo -e "${MAGENTA}"
    cat << 'EOF'
    ██████╗ ██████╗ ██████╗ ███████╗███████╗███████╗████████╗
    ██╔══██╗██╔══██╗██╔══██╗██╔════╝██╔════╝██╔════╝╚══██╔══╝
    ██████╔╝██████╔╝██████╔╝█████╗  ███████╗█████╗     ██║   
    ██╔══██╗██╔═══╝ ██╔═══╝ ██╔══╝  ╚════██║██╔══╝     ██║   
    ██║  ██║██║     ██║     ███████╗███████║███████╗   ██║   
    ╚═╝  ╚═╝╚═╝     ╚═╝     ╚══════╝╚══════╝╚══════╝   ╚═╝   
    ███████╗ ██████╗  ██████╗ ████████╗██╗  ██╗███████╗██████╗ 
    ██╔════╝██╔═══██╗██╔═══██╗╚══██╔══╝██║  ██║██╔════╝██╔══██╗
    █████╗  ██║   ██║██║   ██║   ██║   ███████║█████╗  ██████╔╝
    ██╔══╝  ██║   ██║██║   ██║   ██║   ██╔══██║██╔══╝  ██╔══██╗
    ██║     ╚██████╔╝╚██████╔╝   ██║   ██║  ██║███████╗██║  ██╗
    ╚═╝      ╚═════╝  ╚═════╝    ╚═╝   ╚═╝  ╚═╝╚══════╝╚═╝  ╚═╝
EOF
    echo -e "${NC}"
    echo -e "${CYAN}    Git-Fix 1-Click Local Deployment${NC}"
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

# Configuration
COMPOSE_FILE="docker-compose.yml"
ENV_FILE=".env"
ENV_EXAMPLE=".env.example"
MIN_DOCKER_VERSION="20.10"
MIN_DOCKER_COMPOSE_VERSION="2.0"
MIN_NODE_VERSION="18"
MIN_PYTHON_VERSION="3.11"

# Default options
SKIP_PREREQS=false
SKIP_BUILD=false
DETACHED=true
VERBOSE=false
PROFILE=""

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --skip-prereqs)
            SKIP_PREREQS=true
            shift
            ;;
        --skip-build)
            SKIP_BUILD=true
            shift
            ;;
        --foreground|-f)
            DETACHED=false
            shift
            ;;
        --verbose|-v)
            VERBOSE=true
            shift
            ;;
        --profile)
            PROFILE="$2"
            shift 2
            ;;
        --help|-h)
            cat << EOF
Usage: ./deploy.sh [options]

Options:
    --skip-prereqs    Skip prerequisite checks
    --skip-build      Skip Docker image build (use cached)
    --foreground, -f  Run in foreground (not detached)
    --verbose, -v     Verbose output
    --profile NAME    Docker Compose profile to use (frontend, worker, etc.)
    --help, -h        Show this help

Examples:
    ./deploy.sh                    # Full deployment
    ./deploy.sh --foreground       # Run in foreground
    ./deploy.sh --skip-build       # Quick restart without rebuild
    ./deploy.sh --profile frontend # Only start frontend
EOF
            exit 0
            ;;
        *)
            print_error "Unknown option: $1"
            exit 1
            ;;
    esac
done

# Helper functions
run_cmd() {
    if [[ "$VERBOSE" == true ]]; then
        eval "$1"
    else
        eval "$1" > /dev/null 2>&1
    fi
}

check_command() {
    command -v "$1" > /dev/null 2>&1
}

version_ge() {
    # Returns 0 if $1 >= $2
    [ "$(printf '%s\n' "$2" "$1" | sort -V | head -n1)" = "$2" ]
}

# =============================================================================
# PREREQUISITE CHECKS
# =============================================================================
check_prerequisites() {
    print_step "Checking prerequisites..."
    
    local missing=0
    
    # Check Docker
    if check_command docker; then
        local docker_version=$(docker --version | grep -oE '[0-9]+\.[0-9]+\.[0-9]+' | head -1)
        if version_ge "$docker_version" "$MIN_DOCKER_VERSION"; then
            print_success "Docker $docker_version (>= $MIN_DOCKER_VERSION)"
        else
            print_error "Docker $docker_version < $MIN_DOCKER_VERSION"
            ((missing++))
        fi
    else
        print_error "Docker not installed"
        ((missing++))
    fi
    
    # Check Docker Compose
    if check_command docker-compose || docker compose version > /dev/null 2>&1; then
        local compose_version=""
        if check_command docker-compose; then
            compose_version=$(docker-compose --version | grep -oE '[0-9]+\.[0-9]+\.[0-9]+' | head -1)
        else
            compose_version=$(docker compose version | grep -oE '[0-9]+\.[0-9]+\.[0-9]+' | head -1)
        fi
        if version_ge "$compose_version" "$MIN_DOCKER_COMPOSE_VERSION"; then
            print_success "Docker Compose $compose_version (>= $MIN_DOCKER_COMPOSE_VERSION)"
        else
            print_error "Docker Compose $compose_version < $MIN_DOCKER_COMPOSE_VERSION"
            ((missing++))
        fi
    else
        print_error "Docker Compose not installed"
        ((missing++))
    fi
    
    # Check Node.js (for frontend)
    if check_command node; then
        local node_version=$(node --version | sed 's/v//')
        if version_ge "$node_version" "$MIN_NODE_VERSION"; then
            print_success "Node.js $node_version (>= $MIN_NODE_VERSION)"
        else
            print_warning "Node.js $node_version < $MIN_NODE_VERSION (frontend may not work)"
        fi
    else
        print_warning "Node.js not installed (frontend development unavailable)"
    fi
    
    # Check Python (for backend)
    if check_command python3; then
        local python_version=$(python3 --version | grep -oE '[0-9]+\.[0-9]+')
        if version_ge "$python_version" "$MIN_PYTHON_VERSION"; then
            print_success "Python $python_version (>= $MIN_PYTHON_VERSION)"
        else
            print_warning "Python $python_version < $MIN_PYTHON_VERSION (backend may not work)"
        fi
    else
        print_warning "Python 3 not installed (backend development unavailable)"
    fi
    
    # Check Git
    if check_command git; then
        print_success "Git $(git --version | cut -d' ' -f3)"
    else
        print_error "Git not installed"
        ((missing++))
    fi
    
    # Check available disk space (minimum 5GB)
    local available_space=$(df -BG . | awk 'NR==2 {print $4}' | sed 's/G//')
    if [[ $available_space -ge 5 ]]; then
        print_success "Disk space: ${available_space}GB available"
    else
        print_warning "Low disk space: ${available_space}GB (minimum 5GB recommended)"
    fi
    
    # Check ports
    local ports=(5000 5173 5432 6379 6333 5555)
    for port in "${ports[@]}"; do
        if lsof -i :$port > /dev/null 2>&1; then
            print_warning "Port $port already in use"
        fi
    done
    
    if [[ $missing -gt 0 ]]; then
        print_error "$missing critical prerequisite(s) missing"
        return 1
    fi
    
    print_success "All prerequisites satisfied!"
    return 0
}

# =============================================================================
# ENVIRONMENT SETUP
# =============================================================================
setup_environment() {
    print_step "Setting up environment..."
    
    # Create .env from example if it doesn't exist
    if [[ ! -f "$ENV_FILE" ]]; then
        if [[ -f "$ENV_EXAMPLE" ]]; then
            cp "$ENV_EXAMPLE" "$ENV_FILE"
            print_success "Created .env from .env.example"
        else
            # Create minimal .env
            cat > "$ENV_FILE" << 'EOF'
# Git-Fix Local Development Environment
# Generated by deploy.sh on $(date)

# Core
FLASK_DEBUG=true
SECRET_KEY=dev-secret-change-in-production-$(openssl rand -hex 16)
GITHUB_WEBHOOK_SECRET=dev-webhook-secret-$(openssl rand -hex 16)
PORT=5000

# Database
POSTGRES_DB=gitfix
POSTGRES_USER=gitfix
POSTGRES_PASSWORD=$(openssl rand -hex 16)
DATABASE_URL="postgresql://gitfix:${POSTGRES_PASSWORD}@postgres:5432/gitfix"

# Redis
REDIS_URL=redis://redis:6379/0

# Qdrant Vector DB
QDRANT_URL=http://qdrant:6333

# Frontend
VITE_API_URL=http://localhost:5000
VITE_WS_URL=ws://localhost:5000

# CORS
CORS_ORIGINS=http://localhost:3000,http://localhost:5173

# Security
FORCE_HTTPS=false

# GitHub (optional - for webhook integration)
# GITHUB_APP_ID=
# GITHUB_PRIVATE_KEY=
# GITHUB_WEBHOOK_SECRET=
EOF
            print_success "Created .env with generated secrets"
        fi
    else
        print_info ".env already exists, skipping generation"
    fi
    
    # Generate strong secrets if using defaults
    if grep -q "dev-secret-change-in-production" "$ENV_FILE"; then
        local new_secret=$(openssl rand -hex 32)
        sed -i "s/dev-secret-change-in-production.*/$new_secret/" "$ENV_FILE"
        print_success "Generated new SECRET_KEY"
    fi
    
    if grep -q "dev-webhook-secret" "$ENV_FILE"; then
        local new_webhook=$(openssl rand -hex 32)
        sed -i "s/dev-webhook-secret.*/$new_webhook/" "$ENV_FILE"
        print_success "Generated new GITHUB_WEBHOOK_SECRET"
    fi
}

# =============================================================================
# DOCKER COMPOSE MANAGEMENT
# =============================================================================
build_images() {
    if [[ "$SKIP_BUILD" == true ]]; then
        print_info "Skipping build (--skip-build flag)"
        return 0
    fi
    
    print_step "Building Docker images..."
    
    local compose_cmd="docker compose"
    if check_command docker-compose; then
        compose_cmd="docker-compose"
    fi
    
    local build_args=()
    if [[ -n "$PROFILE" ]]; then
        build_args+=(--profile "$PROFILE")
    fi
    
    if [[ "$VERBOSE" == true ]]; then
        $compose_cmd build "${build_args[@]}"
    else
        $compose_cmd build "${build_args[@]}" > /dev/null 2>&1
    fi
    
    print_success "Docker images built successfully"
}

start_services() {
    print_step "Starting services..."
    
    local compose_cmd="docker compose"
    if check_command docker-compose; then
        compose_cmd="docker-compose"
    fi
    
    local up_args=()
    if [[ "$DETACHED" == true ]]; then
        up_args+=(-d)
    fi
    if [[ -n "$PROFILE" ]]; then
        up_args+=(--profile "$PROFILE")
    fi
    
    $compose_cmd up "${up_args[@]}"
    
    print_success "Services started"
}

wait_for_health() {
    print_step "Waiting for services to be healthy..."
    
    local max_attempts=60
    local attempt=0
    local services=("postgres" "redis" "qdrant" "api")
    
    while [[ $attempt -lt $max_attempts ]]; do
        local all_healthy=true
        
        for service in "${services[@]}"; do
            local status=$(docker inspect --format='{{.State.Health.Status}}' "gitfix-$service" 2>/dev/null || echo "no-healthcheck")
            if [[ "$status" != "healthy" && "$status" != "no-healthcheck" ]]; then
                all_healthy=false
                break
            fi
        done
        
        if [[ "$all_healthy" == true ]]; then
            print_success "All services healthy!"
            return 0
        fi
        
        sleep 2
        ((attempt++))
        
        if [[ $((attempt % 10)) -eq 0 ]]; then
            print_info "Waiting for services... (${attempt}s / ${max_attempts}s)"
        fi
    done
    
    print_warning "Some services may not be fully healthy yet"
    return 1
}

show_status() {
    print_step "Deployment Status"
    echo ""
    
    # Show running containers
    docker compose ps --format "table {{.Name}}\t{{.Status}}\t{{.Ports}}"
    echo ""
    
    # Show URLs
    echo -e "${GREEN}🌐 Access Points:${NC}"
    echo -e "  ${CYAN}Frontend Dashboard:${NC}  http://localhost:5173"
    echo -e "  ${CYAN}API Server:${NC}          http://localhost:5000"
    echo -e "  ${CYAN}API Health:${NC}          http://localhost:5000/api/v1/health"
    echo -e "  ${CYAN}API Metrics:${NC}         http://localhost:5000/api/v1/metrics"
    echo -e "  ${CYAN}Flower (Celery):${NC}     http://localhost:5555"
    echo -e "  ${CYAN}Qdrant Dashboard:${NC}    http://localhost:6333/dashboard"
    local _db_pass
    _db_pass="$(grep -m1 '^POSTGRES_PASSWORD=' "$(dirname "$0")/.env" 2>/dev/null | cut -d= -f2-)"
    if [[ -n "${_db_pass}" ]]; then
        echo -e "  ${CYAN}PostgreSQL:${NC}          localhost:5432 (gitfix/${_db_pass})"
    else
        echo -e "  ${CYAN}PostgreSQL:${NC}          localhost:5432"
    fi
    echo -e "  ${CYAN}Redis:${NC}               localhost:6379"
    echo -e "  ${CYAN}Qdrant:${NC}              localhost:6333"
    echo ""
    
    # Show useful commands
    echo -e "${GREEN}📋 Useful Commands:${NC}"
    echo -e "  ${CYAN}View logs:${NC}           docker compose logs -f [service]"
    echo -e "  ${CYAN}Stop services:${NC}       docker compose down"
    echo -e "  ${CYAN}Restart:${NC}             ./deploy.sh --skip-build"
    echo -e "  ${CYAN}Rebuild:${NC}             ./deploy.sh"
    echo -e "  ${CYAN}Shell into API:${NC}      docker compose exec api bash"
    echo -e "  ${CYAN}DB shell:${NC}            docker compose exec postgres psql -U gitfix -d gitfix"
    echo ""
}

# =============================================================================
# MAIN DEPLOYMENT FLOW
# =============================================================================
main() {
    print_banner
    
    local start_time=$(date +%s)
    
    # Change to script directory
    cd "$(dirname "$0")"
    
    # Check prerequisites
    if [[ "$SKIP_PREREQS" == false ]]; then
        if ! check_prerequisites; then
            print_error "Prerequisite check failed. Use --skip-prereqs to bypass."
            exit 1
        fi
    else
        print_warning "Skipping prerequisite checks"
    fi
    
    # Setup environment
    setup_environment
    
    # Build images
    build_images
    
    # Start services
    start_services
    
    # Wait for health
    wait_for_health
    
    # Show status
    show_status
    
    local end_time=$(date +%s)
    local duration=$((end_time - start_time))
    
    print_success "Deployment completed in ${duration}s!"
    echo ""
    echo -e "${MAGENTA}🎉 Git-Fix is now running!${NC}"
    echo -e "${CYAN}Open http://localhost:5173 to access the dashboard${NC}"
}

# Run main
main "$@"