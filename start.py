#!/usr/bin/env python3
"""
LiveTalk - Start All Services
Starts the backend API, LiveKit agent, and frontend concurrently
"""

import subprocess
import sys
import signal
import time
import os
from pathlib import Path

# Colors for terminal output
class Colors:
    GREEN = '\033[0;32m'
    BLUE = '\033[0;34m'
    YELLOW = '\033[1;33m'
    RED = '\033[0;31m'
    NC = '\033[0m'  # No Color

processes = []

def cleanup(signum=None, frame=None):
    """Cleanup function to stop all processes"""
    print(f"\n{Colors.YELLOW}🛑 Shutting down services...{Colors.NC}")
    for process in processes:
        try:
            process.terminate()
            process.wait(timeout=5)
        except:
            try:
                process.kill()
            except:
                pass
    sys.exit(0)

# Register signal handlers
signal.signal(signal.SIGINT, cleanup)
signal.signal(signal.SIGTERM, cleanup)

def main():
    # Check if we're in the right directory
    if not Path("Backend").exists() or not Path("Frontend").exists():
        print(f"{Colors.RED}❌ Error: Please run this script from the LiveTalk root directory{Colors.NC}")
        sys.exit(1)
    
    print(f"{Colors.BLUE}🚀 Starting LiveTalk Services...{Colors.NC}\n")
    
    # Start Backend API Server
    print(f"{Colors.GREEN}📡 Starting Backend API Server (port 8000)...{Colors.NC}")
    api_process = subprocess.Popen(
        ["python", "-m", "uvicorn", "api:app", "--host", "0.0.0.0", "--port", "8000"],
        cwd="Backend",
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )
    processes.append(api_process)
    time.sleep(2)
    
    # Start LiveKit Agent
    print(f"{Colors.GREEN}🤖 Starting LiveKit Agent...{Colors.NC}")
    agent_process = subprocess.Popen(
        ["python", "main.py"],
        cwd="Backend",
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )
    processes.append(agent_process)
    time.sleep(2)
    
    # Start Frontend
    print(f"{Colors.GREEN}🌐 Starting Frontend (port 3000)...{Colors.NC}")
    frontend_process = subprocess.Popen(
        ["npm", "run", "dev"],
        cwd="Frontend",
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )
    processes.append(frontend_process)
    
    print(f"\n{Colors.BLUE}✅ All services started!{Colors.NC}")
    print(f"{Colors.BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━{Colors.NC}")
    print(f"{Colors.GREEN}Backend API:{Colors.NC}    http://localhost:8000")
    print(f"{Colors.GREEN}Frontend:{Colors.NC}       http://localhost:3000")
    print(f"{Colors.GREEN}API Health:{Colors.NC}     http://localhost:8000/health")
    print(f"{Colors.BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━{Colors.NC}")
    print(f"\n{Colors.YELLOW}Press Ctrl+C to stop all services{Colors.NC}\n")
    
    # Wait for all processes
    try:
        for process in processes:
            process.wait()
    except KeyboardInterrupt:
        cleanup()

if __name__ == "__main__":
    main()

