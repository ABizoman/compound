#!/usr/bin/env python3
"""
Helper script to stop all MCP servers.
Kills any running server processes.
"""
import os
import subprocess
import sys
import signal
import time


def stop_all_servers():
    """Stop all MCP server processes."""
    print("Stopping all MCP servers...")
    
    # Find all server processes
    server_patterns = [
        "math_server.py",
        "search_server.py", 
        "trade_server.py",
        "stock_server.py"
    ]
    
    killed_count = 0
    
    for pattern in server_patterns:
        try:
            # Find processes matching the pattern
            result = subprocess.run(
                ["pgrep", "-f", pattern],
                capture_output=True,
                text=True
            )
            
            if result.returncode == 0:
                pids = result.stdout.strip().split('\n')
                for pid in pids:
                    if pid:
                        try:
                            pid_int = int(pid)
                            print(f"  Killing process {pid_int} ({pattern})...")
                            # Try graceful termination first
                            try:
                                os.kill(pid_int, signal.SIGTERM)
                                time.sleep(0.5)
                                # Check if still running
                                try:
                                    os.kill(pid_int, 0)  # Check if process exists
                                    # Still running, force kill
                                    print(f"    Force killing {pid_int}...")
                                    os.kill(pid_int, signal.SIGKILL)
                                except ProcessLookupError:
                                    pass  # Process already dead
                            except ProcessLookupError:
                                pass  # Process already dead
                            except PermissionError:
                                print(f"    Permission denied for PID {pid_int}")
                            killed_count += 1
                        except ValueError:
                            pass
        except FileNotFoundError:
            # pgrep not available, try alternative method
            print("  pgrep not available, trying alternative method...")
            break
    
    # Alternative: kill by port
    ports = [8001, 8002, 8003, 8004]
    for port in ports:
        try:
            result = subprocess.run(
                ["lsof", "-ti", f":{port}"],
                capture_output=True,
                text=True
            )
            if result.returncode == 0:
                pids = result.stdout.strip().split('\n')
                for pid in pids:
                    if pid:
                        try:
                            pid_int = int(pid)
                            print(f"  Killing process on port {port} (PID {pid_int})...")
                            try:
                                os.kill(pid_int, signal.SIGTERM)
                                time.sleep(0.5)
                                try:
                                    os.kill(pid_int, 0)
                                    os.kill(pid_int, signal.SIGKILL)
                                except ProcessLookupError:
                                    pass
                            except ProcessLookupError:
                                pass
                            killed_count += 1
                        except ValueError:
                            pass
        except FileNotFoundError:
            pass
    
    if killed_count > 0:
        print(f"\n✓ Stopped {killed_count} server process(es)")
    else:
        print("\n✓ No server processes found running")
    
    # Also kill start_servers.py if running
    try:
        result = subprocess.run(
            ["pgrep", "-f", "start_servers.py"],
            capture_output=True,
            text=True
        )
        if result.returncode == 0:
            pids = result.stdout.strip().split('\n')
            for pid in pids:
                if pid:
                    try:
                        os.kill(int(pid), signal.SIGTERM)
                    except:
                        pass
    except:
        pass


if __name__ == "__main__":
    import os
    stop_all_servers()

