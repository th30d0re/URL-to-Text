#!/usr/bin/env python3
"""
MCP Wrapper Script for URL-to-Text Server
Redirects stdout to stderr and only outputs valid MCP JSON-RPC messages
"""

import sys
import json
import subprocess
import os
from typing import Dict, Any

def is_valid_json_rpc(line: str) -> bool:
    """
    Check if a line contains valid JSON-RPC message.
    """
    try:
        data = json.loads(line.strip())
        return isinstance(data, dict) and 'jsonrpc' in data
    except (json.JSONDecodeError, TypeError):
        return False

def run_mcp_server():
    """
    Run the MCP server and filter its output to ensure only valid JSON-RPC is returned.
    """
    try:
        # Run the original MCP server
        process = subprocess.Popen(
            [sys.executable, "url_to_text_server.py"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,
            universal_newlines=True
        )
        
        # Process output line by line
        while True:
            line = process.stdout.readline()
            if not line:
                break
                
            # Only output valid JSON-RPC messages
            if is_valid_json_rpc(line):
                print(line, end='', flush=True)
            else:
                # Redirect non-JSON output to stderr
                print(line, end='', file=sys.stderr, flush=True)
        
        # Wait for process to complete
        process.wait()
        
    except Exception as e:
        # Return error as JSON-RPC
        error_response = {
            "jsonrpc": "2.0",
            "id": None,
            "error": {
                "code": -32603,
                "message": f"Wrapper script error: {str(e)}"
            }
        }
        print(json.dumps(error_response), flush=True)

if __name__ == "__main__":
    run_mcp_server()
