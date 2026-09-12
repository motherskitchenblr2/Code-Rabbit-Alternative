#!/usr/bin/env python3
# =============================================================================
# Git-Fix Prerequisite Checker
# =============================================================================
# Run this script to verify all prerequisites before deployment
# Usage: python scripts/check_prerequisites.py
# =============================================================================

import sys
import subprocess
import shutil
import platform
import os
from typing import Tuple, List, Dict

class Colors:
    RED = '\033[0;31m'
    GREEN = '\033[0;32m'
    YELLOW = '\033[1;33m'
    BLUE = '\033[0;34m'
    MAGENTA = '\033[0;35m'
    CYAN = '\033[0;36m'
    NC = '\033[0m'

def print_banner():
    print(f"{Colors.MAGENTA}")
    print("""
    ██████╗ ██████╗ ██████╗ ███████╗███████╗███████╗████████╗
    ██╔══██╗██╔══██╗██╔══██╗██╔════╝██╔════╝██╔════╝╚══██╔══╝
    ██████╔╝██████╔╝██████╔╝█████╗  ███████╗█████╗     ██║   
    ██╔══██╗██╔═══╝ ██╔═══╝ ██╔══╝  ╚════██║██╔══╝     ██║   
    ██║  ██║██║     ██║     ███████╗███████║███████╗   ██║   
    ╚═╝  ╚═╝╚═╝     ╚═╝     ╚══════╝╚══════╝╚══════╝   ╚═╝   
    """)
    print(f"{Colors.CYAN}    Git-Fix Prerequisite Checker{Colors.NC}")
    print(f"{Colors.CYAN}    Cyberpunk Code Review Engine{Colors.NC}")
    print()

def run_cmd(cmd: List[str]) -> Tuple[int, str, str]:
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
        return result.returncode, result.stdout.strip(), result.stderr.strip()
    except subprocess.TimeoutExpired:
        return -1, "", "Timeout"
    except FileNotFoundError:
        return -1, "", "Not found"
    except Exception as e:
        return -1, "", str(e)

def version_parse(version_str: str) -> tuple:
    """Parse version string to tuple for comparison."""
    parts = []
    for part in version_str.split('.'):
        try:
            parts.append(int(part))
        except ValueError:
            # Handle non-numeric parts
            parts.append(0)
    return tuple(parts)

def version_ge(version1: str, version2: str) -> bool:
    """Check if version1 >= version2."""
    return version_parse(version1) >= version_parse(version2)

def check_docker() -> Dict:
    """Check Docker installation and version."""
    result = {"name": "Docker", "required": ">= 20.10", "installed": False, "version": "", "status": "fail"}
    
    code, stdout, stderr = run_cmd(["docker", "--version"])
    if code == 0:
        # Parse version: "Docker version 24.0.5, build ..."
        import re
        match = re.search(r'(\d+\.\d+\.\d+)', stdout)
        if match:
            version = match.group(1)
            result["version"] = version
            result["installed"] = True
            if version_ge(version, "20.10"):
                result["status"] = "pass"
            else:
                result["status"] = "warn"
    return result

def check_docker_compose() -> Dict:
    """Check Docker Compose installation and version."""
    result = {"name": "Docker Compose", "required": ">= 2.0", "installed": False, "version": "", "status": "fail"}
    
    # Try docker compose (v2)
    code, stdout, stderr = run_cmd(["docker", "compose", "version"])
    if code != 0:
        # Try docker-compose (v1)
        code, stdout, stderr = run_cmd(["docker-compose", "--version"])
    
    if code == 0:
        import re
        match = re.search(r'(\d+\.\d+\.\d+)', stdout)
        if match:
            version = match.group(1)
            result["version"] = version
            result["installed"] = True
            if version_ge(version, "2.0"):
                result["status"] = "pass"
            else:
                result["status"] = "warn"
    return result

def check_node() -> Dict:
    """Check Node.js installation."""
    result = {"name": "Node.js", "required": ">= 18", "installed": False, "version": "", "status": "warn"}
    
    code, stdout, stderr = run_cmd(["node", "--version"])
    if code == 0:
        version = stdout.lstrip('v')
        result["version"] = version
        result["installed"] = True
        if version_ge(version, "18.0.0"):
            result["status"] = "pass"
        else:
            result["status"] = "warn"
    return result

def check_python() -> Dict:
    """Check Python installation."""
    result = {"name": "Python", "required": ">= 3.11", "installed": False, "version": "", "status": "warn"}
    
    for cmd in ["python3", "python"]:
        code, stdout, stderr = run_cmd([cmd, "--version"])
        if code == 0:
            import re
            match = re.search(r'(\d+\.\d+\.\d+)', stdout)
            if match:
                version = match.group(1)
                result["version"] = version
                result["installed"] = True
                if version_ge(version, "3.11.0"):
                    result["status"] = "pass"
                else:
                    result["status"] = "warn"
                break
    return result

def check_git() -> Dict:
    """Check Git installation."""
    result = {"name": "Git", "required": "any", "installed": False, "version": "", "status": "fail"}
    
    code, stdout, stderr = run_cmd(["git", "--version"])
    if code == 0:
        result["version"] = stdout.replace("git version ", "")
        result["installed"] = True
        result["status"] = "pass"
    return result

def check_docker_daemon() -> Dict:
    """Check if Docker daemon is running."""
    result = {"name": "Docker Daemon", "required": "running", "installed": True, "version": "", "status": "fail"}
    
    code, stdout, stderr = run_cmd(["docker", "info"])
    if code == 0:
        result["status"] = "pass"
    return result

def check_disk_space() -> Dict:
    """Check available disk space."""
    result = {"name": "Disk Space", "required": ">= 5GB", "installed": True, "version": "", "status": "fail"}
    
    try:
        stat = shutil.disk_usage(".")
        gb_free = stat.free / (1024**3)
        result["version"] = f"{gb_free:.1f} GB"
        if gb_free >= 5:
            result["status"] = "pass"
        elif gb_free >= 2:
            result["status"] = "warn"
    except Exception:
        result["version"] = "unknown"
    return result

def check_ports() -> Dict:
    """Check if required ports are available."""
    result = {"name": "Port Availability", "required": "free", "installed": True, "version": "", "status": "pass"}
    
    import socket
    ports = [5000, 5173, 5432, 6379, 6333, 5555]
    occupied = []
    
    for port in ports:
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(1)
                result_code = s.connect_ex(('127.0.0.1', port))
                if result_code == 0:
                    occupied.append(port)
        except Exception as exc:
            print(f"  ⚠️  Could not probe port {port}: {exc}", file=sys.stderr)
    
    if occupied:
        result["version"] = f"Occupied: {', '.join(map(str, occupied))}"
        result["status"] = "warn"
    else:
        result["version"] = "All free"
        result["status"] = "pass"
    return result

def check_env_file() -> Dict:
    """Check if .env file exists."""
    result = {"name": ".env File", "required": "exists", "installed": False, "version": "", "status": "fail"}
    
    if os.path.exists(".env"):
        result["installed"] = True
        result["status"] = "pass"
        result["version"] = "Found"
    else:
        result["version"] = "Missing (will be created)"
    return result

def check_env_example() -> Dict:
    """Check if .env.example exists."""
    result = {"name": ".env.example", "required": "exists", "installed": False, "version": "", "status": "fail"}
    
    if os.path.exists(".env.example"):
        result["installed"] = True
        result["status"] = "pass"
        result["version"] = "Found"
    return result

def print_result(result: Dict):
    """Print a single check result."""
    status_colors = {
        "pass": Colors.GREEN,
        "warn": Colors.YELLOW,
        "fail": Colors.RED
    }
    color = status_colors.get(result["status"], Colors.NC)
    status_symbol = {"pass": "✓", "warn": "!", "fail": "✗"}[result["status"]]
    
    print(f"  {color}{status_symbol}{Colors.NC} {result['name']:<25} {result['version']:<20} (req: {result['required']})")

def main():
    print_banner()
    
    checks = [
        check_docker(),
        check_docker_compose(),
        check_docker_daemon(),
        check_node(),
        check_python(),
        check_git(),
        check_disk_space(),
        check_ports(),
        check_env_example(),
        check_env_file(),
    ]
    
    print(f"{Colors.BLUE}Running prerequisite checks...{Colors.NC}\n")
    
    passed = 0
    warned = 0
    failed = 0
    
    for result in checks:
        print_result(result)
        if result["status"] == "pass":
            passed += 1
        elif result["status"] == "warn":
            warned += 1
        else:
            failed += 1
    
    print()
    print(f"{Colors.BLUE}Summary:{Colors.NC}")
    print(f"  {Colors.GREEN}Passed: {passed}{Colors.NC}")
    print(f"  {Colors.YELLOW}Warnings: {warned}{Colors.NC}")
    print(f"  {Colors.RED}Failed: {failed}{Colors.NC}")
    print()
    
    if failed > 0:
        print(f"{Colors.RED}✗ {failed} critical check(s) failed. Please resolve before deployment.{Colors.NC}")
        return 1
    elif warned > 0:
        print(f"{Colors.YELLOW}! {warned} warning(s). Deployment possible but may have issues.{Colors.NC}")
        return 0
    else:
        print(f"{Colors.GREEN}✓ All checks passed! Ready for deployment.{Colors.NC}")
        return 0

if __name__ == "__main__":
    sys.exit(main())