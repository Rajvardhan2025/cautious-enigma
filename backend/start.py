#!/usr/bin/env python3
"""
Startup script for the Voice Appointment Agent system.
This script can start the agent, API server, or both.
"""

import os
import sys
import asyncio
import argparse
import subprocess
import signal
from pathlib import Path

def run_agent(mode="dev"):
    """Run the LiveKit agent"""
    print(f"🤖 Starting LiveKit Agent in {mode} mode...")
    cmd = [sys.executable, "-u", "-m", "agent.main", mode]
    env = os.environ.copy()
    env["PYTHONUNBUFFERED"] = "1"
    return subprocess.Popen(
        cmd, 
        cwd=Path(__file__).parent,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
        env=env
    )

def run_api():
    """Run the FastAPI server"""
    print("🚀 Starting FastAPI server...")
    cmd = [sys.executable, "-u", "-m", "uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
    env = os.environ.copy()
    env["PYTHONUNBUFFERED"] = "1"
    return subprocess.Popen(
        cmd, 
        cwd=Path(__file__).parent,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
        env=env
    )

def run_both(agent_mode="dev"):
    """Run both agent and API server"""
    print("🚀 Starting both Agent and API server...")
    
    processes = []
    
    try:
        # Start API server
        api_process = run_api()
        processes.append(("API", api_process))
        
        # Wait a moment for API to start
        import time
        time.sleep(1)
        
        # Start agent
        agent_process = run_agent(agent_mode)
        processes.append(("Agent", agent_process))
        
        print("✅ Both services started!")
        print("📡 API Server: http://localhost:8000")
        print("🤖 Agent: Running in LiveKit Cloud")
        print("📖 API Docs: http://localhost:8000/docs")
        print("\n" + "="*60)
        print("Logs from both services (press Ctrl+C to stop):")
        print("="*60 + "\n")
        
        # Monitor processes and show output in real-time
        import select
        while True:
            for name, process in processes:
                # Check if process has exited
                if process.poll() is not None:
                    print(f"\n❌ {name} process exited with code {process.returncode}")
                    # Read any remaining output
                    if process.stdout:
                        remaining = process.stdout.read()
                        if remaining:
                            for line in remaining.splitlines():
                                print(f"[{name}] {line}")
                    raise RuntimeError(f"{name} process crashed")
                
                # Read and display output (non-blocking)
                if process.stdout:
                    try:
                        # Use select on Unix systems for non-blocking read
                        import sys
                        if sys.platform != 'win32':
                            import select
                            ready, _, _ = select.select([process.stdout], [], [], 0)
                            if ready:
                                line = process.stdout.readline()
                                if line:
                                    print(f"[{name}] {line.rstrip()}", flush=True)
                        else:
                            # Windows fallback
                            line = process.stdout.readline()
                            if line:
                                print(f"[{name}] {line.rstrip()}", flush=True)
                    except Exception as e:
                        pass
            
            time.sleep(0.05)  # Reduced sleep for more responsive output
            
    except KeyboardInterrupt:
        print("\n🛑 Stopping services...")
        for name, process in processes:
            process.terminate()
        
        # Wait for graceful shutdown
        for name, process in processes:
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                print(f"⚠️  Force killing {name}...")
                process.kill()
        
        print("✅ All services stopped")
    except RuntimeError as e:
        print(f"\n❌ Error: {e}")
        print("🛑 Stopping remaining services...")
        for name, process in processes:
            if process.poll() is None:
                process.terminate()
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    process.kill()

def check_environment():
    """Check if required environment variables are set"""
    required_vars = [
        "LIVEKIT_URL",
        "LIVEKIT_API_KEY", 
        "LIVEKIT_API_SECRET",
        "DEEPGRAM_API_KEY",
        "GEMINI_API_KEY"
    ]
    
    missing_vars = []
    for var in required_vars:
        if not os.getenv(var):
            missing_vars.append(var)
    
    if missing_vars:
        print("❌ Missing required environment variables:")
        for var in missing_vars:
            print(f"   - {var}")
        print("\n💡 Please check your .env.local file")
        return False
    
    print("✅ Environment variables configured")
    return True

def check_dependencies():
    """Check if required dependencies are installed"""
    try:
        import livekit
        import fastapi
        import motor
        print("✅ Dependencies installed")
        return True
    except ImportError as e:
        print(f"❌ Missing dependency: {e}")
        print("💡 Run: pip install -r requirements.txt")
        return False

def main():
    parser = argparse.ArgumentParser(description="Voice Appointment Agent Startup Script")
    parser.add_argument(
        "command", 
        choices=["agent", "api", "both", "check"],
        help="What to run: agent, api, both, or check environment"
    )
    parser.add_argument(
        "--mode",
        choices=["dev", "console", "start"],
        default="dev",
        help="Agent mode (dev, console, or start)"
    )
    
    args = parser.parse_args()
    
    # Load environment variables
    from dotenv import load_dotenv
    load_dotenv(".env.local")
    
    if args.command == "check":
        print("🔍 Checking system requirements...")
        env_ok = check_environment()
        deps_ok = check_dependencies()
        
        if env_ok and deps_ok:
            print("✅ System ready!")
            return 0
        else:
            print("❌ System not ready")
            return 1
    
    # Check environment before starting services
    if not check_environment() or not check_dependencies():
        return 1
    
    if args.command == "agent":
        process = run_agent(args.mode)
        try:
            print("✅ Agent starting... (logs below)\n")
            # Stream output in real-time
            for line in iter(process.stdout.readline, ''):
                if not line:
                    break
                print(line.rstrip())
            
            # Wait for process to complete
            return_code = process.wait()
            if return_code != 0:
                print(f"\n❌ Agent exited with code {return_code}")
                return 1
        except KeyboardInterrupt:
            print("\n🛑 Stopping agent...")
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait()
    
    elif args.command == "api":
        process = run_api()
        try:
            print("✅ API server starting... (logs below)\n")
            # Stream output in real-time
            for line in iter(process.stdout.readline, ''):
                if not line:
                    break
                print(line.rstrip())
            
            # Wait for process to complete
            return_code = process.wait()
            if return_code != 0:
                print(f"\n❌ API server exited with code {return_code}")
                return 1
        except KeyboardInterrupt:
            print("\n🛑 Stopping API server...")
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait()
    
    elif args.command == "both":
        run_both(args.mode)
    
    return 0

if __name__ == "__main__":
    sys.exit(main())