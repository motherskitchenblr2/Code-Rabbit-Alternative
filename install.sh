#!/bin/bash
# =============================================================================
# Git-Fix Universal Installer
# =============================================================================
# This script detects the platform and runs the appropriate installer
# Usage: bash <(curl -fsSL https://raw.githubusercontent.com/motherskitchenblr2/Code-Rabbit-Alternative/main/install.sh)
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

REPO_URL="https://github.com/motherskitchenblr2/Code-Rabbit-Alternative.git"
REPO_RAW="https://raw.githubusercontent.com/motherskitchenblr2/Code-Rabbit-Alternative/main"

print_banner() {
    clear
    echo -e "${MAGENTA}"
    cat << 'EOF'
    ██████╗ ██████╗ ██████╗ ███████╗███████╗███████╗████████╗
    ██╔══██╗██╔══██╗██╔══██╗██╔════╝██╔════╝██╔════╝╚══██╔══╝
    ██████╔╝██████╔╝██████╔╝█████╗  ███████╗█████╗     ██║   
    ██╔══██╗██╔═══╝ ██╔═══╝ ██══╝  ╚════██║██╔════╝╚══██╔══╝
    ██║  ██║██║     ██║     ███████╗███████╗███████╗   ██║   
    ╚═╝  ╚═╝╚═╝     ╚═╝     ╚══════╝╚══════╝╚══════╝   ╚═╝   
EOF
    echo -e "${NC}"
    echo -e "${CYAN}    Git-Fix Universal Installer${NC}"
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

detect_platform() {
    PLATFORM=""
    
    # Check for Termux (Android)
    if [[ -d "/data/data/com.termux" ]]; then
        PLATFORM="termux"
        return
    fi
    
    # Check for Windows (WSL, Git Bash, PowerShell)
    if [[ -n "${WINDIR:-}" ]] || [[ -n "${WINDIR:-}" ]] || [[ "$(uname -s)" =~ CYGWIN|MINGW|MSYS ]]; then
        PLATFORM="windows"
        return
    fi
    
    # Check for macOS
    if [[ "$(uname -s)" == "Darwin" ]]; then
        PLATFORM="macos"
        return
    fi
    
    # Check for Linux
    if [[ -f /etc/os-release ]]; then
        . /etc/os-release
        case $ID in
            ubuntu|debian|linuxmint|pop|elementary|zorin|fedora|rhel|centos|rocky|almalinux|arch|manjaro|endeavouros|opensuse*|sles)
                PLATFORM="linux"
                ;;
        esac
    fi
    
    if [[ -z "$PLATFORM" ]]; then
        PLATFORM="unknown"
    fi
}

download_and_run() {
    local url="$1"
    local name="$2"
    
    print_step "Downloading $name installer..."
    
    if command -v curl &> /dev/null; then
        curl -fsSL "$1" | bash
    elif command -v wget &> /dev/null; then
        wget -qO- "$1" | bash
    else
        print_error "Neither curl nor wget found. Please install curl or wget."
        exit 1
    fi
}

run_termux() {
    print_info "Detected Termux (Android)"
    download_and_run "$REPO_RAW/deploy/termux/install.sh" "Termux"
}

run_windows() {
    print_info "Detected Windows"
    print_info "Please run the following in PowerShell as Administrator:"
    echo ""
    echo -e "${CYAN}irm $REPO_RAW/deploy/windows/install.ps1 | iex${NC}"
    echo ""
    print_info "Or download and run manually:"
    echo -e "${CYAN}https://raw.githubusercontent.com/motherskitchenblr2/Code-Rabbit-Alternative/main/deploy/windows/install.ps1${NC}"
}

run_macos() {
    print_info "Detected macOS"
    print_warning "macOS installer not yet available."
    print_info "Please use Docker deployment instead:"
    echo ""
    echo -e "${CYAN}git clone https://github.com/motherskitchenblr2/Code-Rabbit-Alternative.git${NC}"
    echo -e "${CYAN}cd Code-Rabbit-Alternative${NC}"
    echo -e "${CYAN}./deploy/docker/deploy.sh${NC}"
}

run_linux() {
    print_info "Detected Linux"
    download_and_run "$REPO_RAW/deploy/linux/install.sh" "Linux"
}

run_docker() {
    print_info "Running Docker deployment..."
    download_and_run "$REPO_RAW/deploy/docker/deploy.sh" "Docker"
}

show_menu() {
    echo ""
    echo -e "${CYAN}Select installation method:${NC}"
    echo ""
    echo -e "  ${CYAN}1)${NC} Auto-detect and install (recommended)"
    echo -e "  ${CYAN}2)${NC} Docker deployment (all platforms)"
    echo -e "  ${CYAN}3)${NC} Linux/Ubuntu native installation"
    echo -e "  ${CYAN}4)${NC} Android/Termux installation"
    echo -e "  ${CYAN}5)${NC} Windows PowerShell installation"
    echo -e "  ${CYAN}6)${NC} Docker Compose deployment"
    echo -e "  ${CYAN}7)${NC} Exit"
    echo ""
    read -p "Enter choice [1-7]: " choice
    
    case $choice in
        1)
            case $PLATFORM in
                termux) run_termux ;;
                windows) run_windows ;;
                macos) run_macos ;;
                linux) run_linux ;;
                *) run_docker ;;
            esac
            ;;
        2) run_docker ;;
        3) run_linux ;;
        4) run_termux ;;
        5) run_windows ;;
        6) run_docker ;;
        7) exit 0 ;;
        *) print_error "Invalid choice"; exit 1 ;;
    esac
}

main() {
    print_banner
    
    detect_platform
    print_info "Detected platform: $PLATFORM"
    
    # If running with arguments, use them
    if [[ $# -gt 0 ]]; then
        case $1 in
            --termux) run_termux ;;
            --windows) run_windows ;;
            --macos) run_macos ;;
            --linux) run_linux ;;
            --docker) run_docker ;;
            --help|-h)
                cat << EOF
Git-Fix Universal Installer

Usage: $0 [options]

Options:
    --termux     Install on Android/Termux
    --windows    Install on Windows (shows PowerShell command)
    --macos      Install on macOS (shows Docker instructions)
    --linux      Install on Linux/Ubuntu
    --docker     Deploy with Docker Compose
    --help       Show this help

Examples:
    # Auto-detect and install
    curl -fsSL https://raw.githubusercontent.com/motherskitchenblr2/Code-Rabbit-Alternative/main/install.sh | bash

    # Install on Linux
    curl -fsSL https://raw.githubusercontent.com/motherskitchenblr2/Code-Rabbit-Alternative/main/install.sh | bash -s -- --linux

    # Deploy with Docker
    curl -fsSL https://raw.githubusercontent.com/motherskitchenblr2/Code-Rabbit-Alternative/main/install.sh | bash -s -- --docker
EOF
                exit 0
                ;;
            *) print_error "Unknown option: $1"; exit 1 ;;
        esac
    else
        show_menu
    fi
}

# Run main
main "$@"