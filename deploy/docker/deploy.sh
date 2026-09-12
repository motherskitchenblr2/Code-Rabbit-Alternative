#!/bin/bash
# =============================================================================
# Git-Fix Docker One-Click Deployment
# =============================================================================
# This script deploys Git-Fix using Docker Compose with one command
# Usage: bash <(curl -fsSL https://raw.githubusercontent.com/motherskitchenblr2/Code-Rabbit-Alternative/main/deploy/docker/deploy.sh)
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
    ██╔══██╗██╔═══╝ ██╔═══╝ ██╔══╝  ╚════██║██╔══╝     ██║   
    ██║  ██║██║     ██║     ███████╗███████╗███████╗   ██║   
    ╚═╝  ╚═╝╚═╝     ╚═╝     ╚══════╝╚══════╝╚══════╝   ╚═╝   
EOF
    echo -e "${NC}"
    echo -e "${CYAN}    Git-Fix Docker Deployment${NC}"
    echo -e "${CYAN}    One-Click Container Deployment${NC}"
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

# Default options
PROFILE="core"
DETACHED=true
SKIP_BUILD=false
VERBOSE=false
PULL_LATEST=false

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --profile)
            PROFILE="$2"
            shift 2
            ;;
        --foreground)
            DETACHED=false
            shift
            ;;
        --skip-build)
            SKIP_BUILD=true
            shift
            ;;
        --pull)
            PULL_LATEST=true
            shift
            ;;
        --verbose)
            VERBOSE=true
            shift
            ;;
        --help|-h)
            cat << EOF
Usage: $0 [options]

Options:
    --profile NAME       Docker Compose profile (core, dev, worker, monitoring, full)
    --foreground         Run in foreground (see logs)
    --skip-build         Skip image build (use cached)
    --pull               Pull latest images before starting
    --verbose            Verbose output
    --help               Show this help

Profiles:
    core       - API, PostgreSQL, Redis, Qdrant (default)
    dev        - Core + Frontend dev server
    worker     - Core + Celery worker + Flower
    monitoring - Core + Prometheus + Grafana + Jaeger
    full       - All services including monitoring

Examples:
    ./docker-deploy.sh                    # Core services
    ./docker-deploy.sh --profile full     # Everything
    ./docker-deploy.sh --profile dev      # Development mode
    ./docker-deploy.sh --foreground       # See logs
EOF
            exit 0
            ;;
        *)
            print_error "Unknown option: $1"
            exit 1
            ;;
    esac
done

print_banner

print_step "Checking Docker..."
if ! command -v docker &> /dev/null; then
    print_error "Docker not installed. Please install Docker first."
    exit 1
fi
print_success "Docker: $(docker --version)"

if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null; then
    print_error "Docker Compose not installed."
    exit 1
fi
print_success "Docker Compose available"

# Check if .env exists
if [[ ! -f .env ]]; then
    print_warning ".env not found, creating from example..."
    if [[ -f .env.example ]]; then
        cp .env.example .env
        # Generate secrets
        SECRET_KEY=$(openssl rand -hex 32)
        WEBHOOK_SECRET=$(openssl rand -hex 32)
        sed -i "s/your-super-secret-key-change-in-production-min-32-chars/$(openssl rand -hex 32)/" .env
        sed -i "s/your-webhook-secret-min-32-chars/$(openssl rand -hex 32)/" .env
        print_success "Created .env with generated secrets"
    else
        print_error ".env.example not found"
        exit 1
    fi
else
    print_success ".env file found"
fi

# Pull latest images if requested
if [[ "$PULL_LATEST" == true ]]; then
    print_step "Pulling latest images..."
    docker compose pull
    print_success "Images pulled"
fi

# Build images
if [[ "$SKIP_BUILD" == false ]]; then
    print_step "Building images..."
    if [[ "$VERBOSE" == true ]]; then
        docker compose --profile "$PROFILE" build
    else
        docker compose --profile "$PROFILE" build > /dev/null 2>&1
    fi
    print_success "Images built"
fi

# Start services
print_step "Starting services (profile: $PROFILE)..."
UP_ARGS=()
if [[ "$DETACHED" == true ]]; then
    UP_ARGS+=(-d)
fi

if [[ "$VERBOSE" == true ]]; then
    docker compose --profile "$PROFILE" up "${UP_ARGS[@]}"
else
    docker compose --profile "$PROFILE" up "${UP_ARGS[@]}" > /dev/null 2>&1
fi

print_success "Services started"

# Wait for health
print_step "Waiting for services to be healthy..."
sleep 5

# Check health
MAX_ATTEMPTS=30
ATTEMPT=0
while [[ $ATTEMPT -lt $MAX_ATTEMPTS ]]; do
    HEALTHY=true
    for service in postgres redis qdrant api; do
        STATUS=$(docker inspect --format='{{.State.Health.Status}}' "gitfix-$service" 2>/dev/null || echo "no-healthcheck")
        if [[ "$STATUS" != "healthy" && "$STATUS" != "no-healthcheck" ]]; then
            HEALTHY=false
            break
        fi
    done
    
    if [[ "$HEALTHY" == true ]]; then
        print_success "All services healthy!"
        break
    fi
    
    sleep 2
    ((ATTEMPT++))
done

# Show status
echo ""
print_step "Deployment Status"
docker compose ps --format "table {{.Name}}\t{{.Status}}\t{{.Ports}}"

echo ""
echo -e "${GREEN}🎉 Git-Fix deployed successfully!${NC}"
echo ""
echo -e "${CYAN}🌐 Access Points:${NC}"
echo -e "  ${CYAN}Frontend Dashboard:${NC}  http://localhost:5173"
echo -e "  ${CYAN}API Server:${NC}          http://localhost:5000"
echo -e "  ${CYAN}API Health:${NC}          http://localhost:5000/api/v1/health"
echo -e "  ${CYAN}API Metrics:${NC}         http://localhost:5000/api/v1/metrics"
echo -e "  ${CYAN}Flower (Celery):${NC}     http://localhost:5555"
echo -e "  ${CYAN}Qdrant Dashboard:${NC}    http://localhost:6333/dashboard"
echo -e "  ${CYAN}PostgreSQL:${NC}          localhost:5432"
echo -e "  ${CYAN}Redis:${NC}               localhost:6379"
echo -e "  ${CYAN}Qdrant:${NC}              localhost:6333"

if [[ "$PROFILE" == "monitoring" || "$PROFILE" == "full" ]]; then
    echo -e "  ${CYAN}Prometheus:${NC}         http://localhost:9090"
    echo -e "  ${CYAN}Grafana:${NC}            http://localhost:3000"
    echo -e "  ${CYAN}Jaeger:${NC}             http://localhost:16686"
fi

echo ""
echo -e "${GREEN}📋 Useful Commands:${NC}"
echo -e "  ${CYAN}View logs:${NC}           docker compose logs -f [service]"
echo -e "  ${CYAN}Stop services:${NC}       docker compose down"
echo -e "  ${CYAN}Restart:${NC}             $0 --skip-build"
echo -e "  ${CYAN}Rebuild:${NC}             $0"
echo -e "  ${CYAN}Shell into API:${NC}      docker compose exec api bash"
echo -e "  ${CYAN}DB shell:${NC}            docker compose exec postgres psql -U gitfix -d gitfix"
echo ""

if [[ "$DETACHED" == true ]]; then
    echo -e "${MAGENTA}🎉 Git-Fix is running in background!${NC}"
    echo -e "${CYAN}Run 'docker compose logs -f' to see logs${NC}"
else
    echo -e "${MAGENTA}🎉 Git-Fix is running in foreground!${NC}"
    echo -e "${CYAN}Press Ctrl+C to stop${NC}"
fi