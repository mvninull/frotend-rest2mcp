import os
import sys
import argparse
from openapi import create_mcp_server
from server import run_server_stdio, run_server_http, run_server_sse
from utils import logger, run_with_inspector

# --- Main ---


def main():
    parser = argparse.ArgumentParser(description="rest2mcp")
    parser.add_argument("--transport", choices=["stdio", "http", "sse"], default="stdio")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8081)
    parser.add_argument("--inspect", action="store_true", help="Lança o MCP Inspector automaticamente")
    args = parser.parse_args()

    spec_url = os.getenv("MCP_SPEC_URL")
    server_name = os.getenv("MCP_SERVER_NAME", "UniversalAPI")

    if not spec_url:
        logger.error("Falta variável de ambiente MCP_SPEC_URL")
        sys.exit(1)

    if args.inspect:
        # Modo desenvolvimento: servidor + Inspector
        return run_with_inspector(args.transport, spec_url, server_name, args.host, args.port)

    # Modo normal: apenas servidor
    if args.transport == "http":
        run_server_http(spec_url, server_name, args.host, args.port)
    elif args.transport == "sse":
        run_server_sse(spec_url, server_name, args.host, args.port)
    else:
        run_server_stdio(spec_url, server_name)


if __name__ == "__main__":
    sys.exit(main())
