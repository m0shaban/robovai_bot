#!/usr/bin/env python
"""
RoboVAI Platform Launcher
Starts Backend (FastAPI) with HTMX Dashboard
"""
import os
import sys
import subprocess
import time
from pathlib import Path

# Colors for terminal output
class Colors:
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    END = '\033[0m'
    BOLD = '\033[1m'

def print_header():
    print(f"\n{Colors.CYAN}{Colors.BOLD}")
    print("=" * 60)
    print("  RoboVAI Multi-Tenant Chatbot Platform")
    print("  FastAPI Backend + HTMX Dashboard")
    print("=" * 60)
    print(f"{Colors.END}\n")

def check_env_file():
    """Check if .env file exists"""
    env_path = Path(".env")
    if not env_path.exists():
        print(f"{Colors.YELLOW}⚠️  Warning: .env file not found{Colors.END}")
        print(f"   Copy .env.example to .env and configure your settings")
        return False
    print(f"{Colors.GREEN}✓ .env file found{Colors.END}")
    return True

def check_database():
    """Check if DATABASE_URL is set"""
    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        print(f"{Colors.YELLOW}⚠️  DATABASE_URL not set in .env{Colors.END}")
        print(f"   Default: postgresql+asyncpg://postgres:postgres@localhost:5432/robovai")
        return False
    print(f"{Colors.GREEN}✓ Database configured{Colors.END}")
    return True

def start_backend():
    """Start FastAPI backend with Uvicorn"""
    print(f"\n{Colors.BLUE}Starting Backend (FastAPI + HTMX UI)...{Colors.END}")
    
    # Find Python in venv
    venv_python = Path(".venv/Scripts/python.exe") if sys.platform == "win32" else Path(".venv/bin/python")
    
    if not venv_python.exists():
        print(f"{Colors.RED}✗ Virtual environment not found at {venv_python}{Colors.END}")
        print(f"  Run: python -m venv .venv")
        print(f"  Then: .venv\\Scripts\\Activate.ps1  (Windows)")
        print(f"  Then: pip install -r requirements.txt")
        return None
    
    cmd = [
        str(venv_python),
        "-m", "uvicorn",
        "app.main:app",
        "--host", "0.0.0.0",
        "--port", "8000",
        "--reload"
    ]
    
    try:
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            universal_newlines=True,
            bufsize=1
        )
        
        # Wait for startup
        time.sleep(3)
        
        if process.poll() is None:
            print(f"{Colors.GREEN}✓ Backend started successfully{Colors.END}")
            print(f"\n{Colors.CYAN}Access URLs:{Colors.END}")
            print(f"  • Dashboard: {Colors.BOLD}http://localhost:8000/ui{Colors.END}")
            print(f"  • API Docs:   {Colors.BOLD}http://localhost:8000/docs{Colors.END}")
            print(f"  • Health:     {Colors.BOLD}http://localhost:8000/health{Colors.END}")
            return process
        else:
            print(f"{Colors.RED}✗ Backend failed to start{Colors.END}")
            return None
            
    except Exception as e:
        print(f"{Colors.RED}✗ Error starting backend: {e}{Colors.END}")
        return None

def main():
    print_header()
    
    # Pre-flight checks
    print(f"{Colors.BOLD}Pre-flight checks:{Colors.END}")
    check_env_file()
    check_database()
    
    # Start services
    backend_process = start_backend()
    
    if not backend_process:
        print(f"\n{Colors.RED}Failed to start platform{Colors.END}")
        sys.exit(1)
    
    print(f"\n{Colors.GREEN}{Colors.BOLD}Platform is running!{Colors.END}")
    print(f"\n{Colors.YELLOW}Press Ctrl+C to stop all services{Colors.END}\n")
    
    try:
        # Keep script running and show backend logs
        for line in backend_process.stdout:
            print(line, end='')
    except KeyboardInterrupt:
        print(f"\n\n{Colors.YELLOW}Shutting down...{Colors.END}")
        backend_process.terminate()
        backend_process.wait()
        print(f"{Colors.GREEN}All services stopped{Colors.END}\n")

if __name__ == "__main__":
    main()
