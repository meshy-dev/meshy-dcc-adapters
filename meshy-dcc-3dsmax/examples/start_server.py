r"""Example: Start meshy-dcc-3dsmax server inside 3ds Max.

Run this script in the 3ds Max MAXScript Listener:

    python.ExecuteFile @"G:\PycharmProjects\github\meshy-dcc-3dsmax\examples\start_server.py"
"""

# Import future modules
from __future__ import annotations

# Import local modules
import meshy_dcc_3dsmax

# Start the MCP server
print("Starting meshy-dcc-3dsmax server...")
server = meshy_dcc_3dsmax.start_server()

print(f"Server started on port {server.port}")
print("MCP gateway: http://127.0.0.1:19765/mcp")

# Discover available skills
print("\nDiscovering skills...")
count = server.discover_skills()
print(f"Discovered {count} skills")

print("\nServer is running. Press Ctrl+C to stop.")

# Keep the server running (in real usage, 3ds Max will keep the process alive)
try:
    import time

    while True:
        time.sleep(1)
except KeyboardInterrupt:
    print("\nStopping server...")
    meshy_dcc_3dsmax.stop_server()
    print("Server stopped.")
