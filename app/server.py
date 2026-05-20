from openapi import create_mcp_server
from utils import logger


def run_server_stdio(spec_url, name):
    logger.info("Iniciando modo STDIO")
    mcp = create_mcp_server(spec_url, name)
    mcp.run(transport="stdio")


def run_server_http(spec_url, name, host, port):
    """Modo Streamable HTTP (Moderno)"""
    logger.info(f"Iniciando modo HTTP em http://{host}:{port}/mcp")
    mcp = create_mcp_server(spec_url, name)
    mcp.run(transport="http", host=host, port=port)


def run_server_sse(spec_url, name, host, port):
    """Modo SSE (Legacy/Compatibilidade)"""
    logger.info(f"Iniciando modo SSE em http://{host}:{port}/sse")
    mcp = create_mcp_server(spec_url, name)
    # No FastMCP, o transporte SSE geralmente expõe /sse e /messages
    mcp.run(transport="sse", host=host, port=port)
