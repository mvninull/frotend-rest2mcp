from fastmcp import FastMCP
import httpx
import json
import subprocess
import os
import sys
import argparse
import logging
import threading
import time
import socket

# Configuração de Log Colorido
class ColoredFormatter(logging.Formatter):
    COLORS = {
        'DEBUG': '\033[36m',
        'INFO': '\033[32m',
        'WARNING': '\033[33m',
        'ERROR': '\033[31m',
        'CRITICAL': '\033[35m',
    }
    RESET = '\033[0m'

    def format(self, record):
        log_color = self.COLORS.get(record.levelname, self.RESET)
        record.levelname = f"{log_color}{record.levelname}{self.RESET}"
        return super().format(record)

handler = logging.StreamHandler(sys.stderr)
handler.setFormatter(ColoredFormatter('[%(levelname)s] %(message)s'))
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
logger.addHandler(handler)

# --- Funções de Utilitário OpenAPI ---

def load_and_convert_spec(url: str) -> dict:
    logger.info(f"Baixando spec de {url}...")
    response = httpx.get(url, timeout=30.0)
    response.raise_for_status()
    data = response.json()

    if "openapi" in data and str(data["openapi"]).startswith("3"):
        return data

    if "swagger" in data and str(data["swagger"]).startswith("2"):
        logger.info(f"Swagger 2.0 detectado - convertendo para OpenAPI 3...")
        return _convert_with_npx(data)

    raise ValueError("Versão OpenAPI/Swagger não suportada.")

def _convert_with_npx(original_data: dict) -> dict:
    temp_input, temp_output = "_temp_s2.json", "_temp_o3.json"
    try:
        with open(temp_input, "w", encoding="utf-8") as f:
            json.dump(original_data, f)
        
        shell_val = (sys.platform == "win32")
        subprocess.run(["npx", "swagger2openapi", temp_input, "-o", temp_output], 
                       check=True, shell=shell_val, capture_output=True)
        
        with open(temp_output, "r", encoding="utf-8") as f:
            return json.load(f)
    finally:
        for f in [temp_input, temp_output]:
            if os.path.exists(f): os.remove(f)

def create_mcp_server(spec_url: str, name: str) -> FastMCP:
    spec = load_and_convert_spec(spec_url)
    # Extrai base URL simples
    base_url = spec["servers"][0]["url"] if "servers" in spec else spec_url.rsplit('/', 1)[0]
    
    logger.info(f"Criando servidor FastMCP: {name} | Base API: {base_url}")
    return FastMCP.from_openapi(openapi_spec=spec, name=name, client=httpx.AsyncClient(base_url=base_url))

# --- Modos de Execução ---

def run_server_stdio(spec_url, name):
    logger.info(f"Iniciando modo STDIO")
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

# --- Inspector ---

def launch_inspector(url: str):
    """
    Lança o MCP Inspector conectando no servidor via URL.
    """
    logger.info(f"Lançando Inspector em: {url}")
    
    cmd = [
        "npx",
        "@modelcontextprotocol/inspector",
        "--url",
        url
    ]
    
    logger.info(f"Executando: {' '.join(cmd)}")
    
    try:
        result = subprocess.run(cmd, shell=(sys.platform == "win32"))
        return result.returncode
    except KeyboardInterrupt:
        logger.info("Inspector encerrado pelo usuário")
        return 0

def run_with_inspector(transport: str, spec_url: str, name: str, host: str, port: int):
    """
    Inicia o servidor em background e lança o Inspector conectando nele.
    Funciona com qualquer transporte (stdio, http, sse).
    """
    # Determina a URL do endpoint baseado no transporte
    if transport == "stdio":
        # STDIO: O Inspector spawna o processo diretamente
        logger.info("=" * 50)
        logger.info("MODO DESENVOLVIMENTO (Inspector + STDIO)")
        logger.info("=" * 50)
        logger.info(f"Lançando Inspector com servidor STDIO...")
        
        cmd = [
            "npx",
            "@modelcontextprotocol/inspector",
            sys.executable,
            __file__  # arquivo atual
        ]
        
        # Passa variáveis de ambiente para o processo filho
        env = os.environ.copy()
        
        logger.info(f"Executando: {' '.join(cmd)}")
        result = subprocess.run(cmd, env=env, shell=(sys.platform == "win32"))
        return result.returncode
    
    elif transport == "http":
        endpoint = f"http://{host}:{port}/mcp"
        logger.info("=" * 50)
        logger.info("MODO DESENVOLVIMENTO (Inspector + HTTP)")
        logger.info("=" * 50)
        
    elif transport == "sse":
        endpoint = f"http://{host}:{port}/sse"
        logger.info("=" * 50)
        logger.info("MODO DESENVOLVIMENTO (Inspector + SSE)")
        logger.info("=" * 50)
    
    else:
        logger.error(f"Transporte desconhecido: {transport}")
        return 1
    
    # Para HTTP e SSE: inicia servidor em thread e conecta Inspector
    logger.info(f"Servidor: {name}")
    logger.info(f"Spec: {spec_url}")
    
    def start_server():
        if transport == "http":
            run_server_http(spec_url, name, host, port)
        elif transport == "sse":
            run_server_sse(spec_url, name, host, port)
    
    server_thread = threading.Thread(target=start_server, daemon=True)
    server_thread.start()
    
    # Aguarda servidor subir
    logger.info("Aguardando servidor iniciar...")
    time.sleep(3)
    
    # Verifica se porta está aberta
    if not _is_port_open(host, port):
        logger.error(f"Servidor não responde em {host}:{port}")
        return 1
    
    # Lança Inspector
    return launch_inspector(endpoint)

def _is_port_open(host: str, port: int) -> bool:
    """Verifica se uma porta está aberta (servidor rodando)."""
    try:
        with socket.create_connection((host, port), timeout=2):
            return True
    except (OSError, ConnectionRefusedError):
        return False

# --- Main ---

def main():
    parser = argparse.ArgumentParser(description="rest2mcp Server")
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