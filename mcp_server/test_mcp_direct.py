#!/usr/bin/env python3
"""Test the MCP server directly to see tool descriptions."""

import subprocess
import json
import sys

def test_list_tools():
    """Test listing tools from the MCP server."""
    # Start the server
    proc = subprocess.Popen(
        ["uv", "run", "news_server.py"],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        cwd="/home/amite/code/python/scraper_cleaner/mcp_server"
    )
    
    # Send a tools/list request
    request = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "tools/list"
    }
    
    try:
        proc.stdin.write(json.dumps(request) + "\n")
        proc.stdin.flush()
        
        # Read response
        response = proc.stdout.readline()
        print("Response:", response)
        
        if response:
            data = json.loads(response)
            print("\nTools available:")
            for tool in data.get("result", {}).get("tools", []):
                print(f"\n- {tool['name']}")
                print(f"  Description: {tool.get('description', 'N/A')}")
                print(f"  Input schema: {json.dumps(tool.get('inputSchema', {}), indent=2)}")
    finally:
        proc.terminate()
        proc.wait()

if __name__ == "__main__":
    test_list_tools()
