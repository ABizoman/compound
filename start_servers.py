#!/usr/bin/env python3
"""
Convenience script to start all MCP servers in separate processes.
Run this script to start all MCP servers, then run the trading agent in another terminal.
"""
import subprocess
import sys
import time
import signal
from pathlib import Path


def main():
    """Start all MCP servers."""
    base_dir = Path(__file__).parent
    
    servers = [
        ("src/mcp_servers/math_server.py", 8001, "Math"),
        ("src/mcp_servers/search_server.py", 8002, "Search"),
        ("src/mcp_servers/trade_server.py", 8003, "Trade"),
        ("src/mcp_servers/stock_server.py", 8004, "Stock"),
    ]
    
    processes = []
    _shutting_down = False
    
    def signal_handler(sig, frame):
        """Handle Ctrl+C gracefully."""
        nonlocal _shutting_down
        if _shutting_down:
            # Force kill if already shutting down
            print("\nForce killing servers...")
            for process, script, port, name in processes:
                try:
                    process.kill()
                except:
                    pass
            sys.exit(1)
        
        _shutting_down = True
        print("\n\nStopping all servers...")
        for process, script, port, name in processes:
            print(f"  Stopping {name} server (port {port})...")
            try:
                process.terminate()
            except:
                pass
        
        # Wait for all to terminate (with timeout)
        for process, script, port, name in processes:
            try:
                process.wait(timeout=3)
            except subprocess.TimeoutExpired:
                print(f"  Force killing {name} server...")
                process.kill()
                process.wait()
        
        print("✓ All servers stopped")
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    
    try:
        print("Starting MCP servers...\n")
        for script, port, name in servers:
            script_path = base_dir / script
            if not script_path.exists():
                print(f"✗ Script not found: {script_path}")
                continue
            
            print(f"Starting {name} server on port {port}...")
            process = subprocess.Popen(
                [sys.executable, str(script_path)],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            processes.append((process, script, port, name))
            time.sleep(1.5)  # Give each server time to start
        
        print("\n" + "="*60)
        print("✓ All MCP servers started!")
        print("="*60)
        print("\nServers running:")
        for _, _, port, name in processes:
            print(f"  - {name}: http://localhost:{port}")
        print("\nPress Ctrl+C to stop all servers\n")
        
        # Wait for all processes
        for process, script, port, name in processes:
            process.wait()
    
    except KeyboardInterrupt:
        signal_handler(None, None)
    except Exception as e:
        print(f"\n✗ Error: {e}")
        signal_handler(None, None)


if __name__ == "__main__":
    main()
