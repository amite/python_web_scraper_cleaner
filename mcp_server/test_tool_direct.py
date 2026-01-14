#!/usr/bin/env python3
"""
Directly test the ask_news tool via MCP protocol to see what's happening.
"""

import subprocess
import json
import time

def send_mcp_request(proc, request):
    """Send a JSON-RPC request and get response."""
    proc.stdin.write(json.dumps(request) + "\n")
    proc.stdin.flush()
    
    # Read response (may be multiple lines for logs)
    response_line = None
    for _ in range(10):  # Try reading a few lines
        line = proc.stdout.readline().strip()
        if line and line.startswith("{"):
            try:
                data = json.loads(line)
                if "result" in data or "error" in data:
                    response_line = line
                    break
            except:
                continue
    
    return response_line

def test_ask_news_tool():
    """Test the ask_news tool directly."""
    print("Starting MCP server...")
    proc = subprocess.Popen(
        ["uv", "run", "news_server.py"],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        bufsize=1,
        cwd="/home/amite/code/python/scraper_cleaner/mcp_server"
    )
    
    time.sleep(2)  # Give server time to start
    
    try:
        # Initialize
        init_request = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {"name": "test-client", "version": "1.0"}
            }
        }
        
        print("Sending initialize...")
        response = send_mcp_request(proc, init_request)
        print(f"Initialize response: {response}\n")
        
        # Call the tool
        tool_request = {
            "jsonrpc": "2.0",
            "id": 2,
            "method": "tools/call",
            "params": {
                "name": "ask_news",
                "arguments": {
                    "question": "What are danish officials saying?"
                }
            }
        }
        
        print("Calling ask_news tool...")
        response = send_mcp_request(proc, tool_request)
        print(f"Tool response: {response}\n")
        
        if response:
            data = json.loads(response)
            if "result" in data:
                print("SUCCESS! Tool executed.")
                print(f"Result content: {data['result']}")
            elif "error" in data:
                print(f"ERROR: {data['error']}")
        else:
            print("No response received")
            
    finally:
        proc.terminate()
        proc.wait()

if __name__ == "__main__":
    test_ask_news_tool()
