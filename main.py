from fastmcp import FastMCP
import httpx
import json
import subprocess
import os
import sys
import argparse
import logging



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


def load_and_convert_spec(url: str) -> dict:
    """Carrega spec e converte para v3 se necessario."""
    
    logger.info(f"Baixando spec de {url}...")
    response = httpx.get(url, timeout=30.0)
    response.raise_for_status()
    data = response.json()
    
    if "openapi" in data and str(data["openapi"]).startswith("3"):
        logger.info(f"OpenAPI {data['openapi']} detectado")
        return data
    
    if "swagger" in data and str(data["swagger"]).startswith("2"):
        logger.info(f"Swagger {data['swagger']} detectado - convertendo...")
        return _convert_with_npx(data)
    
    raise ValueError(
        f"Versao nao suportada: {data.get('openapi') or data.get('swagger', 'desconhecida')}"
    )


def _convert_with_npx(original_data: dict) -> dict:
    """Converte Swagger 2.0 -> OpenAPI 3.0 via npx."""
    temp_input = "_temp_swagger2.json"
    temp_output = "_temp_openapi3.json"
    
    try:
        with open(temp_input, "w", encoding="utf-8") as f:
            json.dump(original_data, f, indent=2)
        
        logger.info(f"Executando: npx swagger2openapi {temp_input} -o {temp_output}")
        
        result = subprocess.run(
            ["npx", "swagger2openapi", temp_input, "-o", temp_output],
            capture_output=True,
            text=True,
            shell=(sys.platform == "win32")
        )
        
        if result.returncode != 0:
            result = subprocess.run(
                ["swagger2openapi", temp_input, "-o", temp_output],
                capture_output=True,
                text=True,
                shell=(sys.platform == "win32")
            )
            if result.returncode != 0:
                raise RuntimeError(f"Conversao falhou: {result.stderr}")
        
        with open(temp_output, "r", encoding="utf-8") as f:
            converted = json.load(f)
        
        logger.info("Conversao concluida!")
        return converted
        
    finally:
        for f in [temp_input, temp_output]:
            if os.path.exists(f):
                os.remove(f)


def extract_base_url(spec: dict, fallback_url: str) -> str:
    """Extrai base URL da spec."""
    if "servers" in spec and spec["servers"]:
        return spec["servers"][0]["url"].rstrip("/")
    
    if "host" in spec:
        scheme = spec.get("schemes", ["https"])[0]
        base = spec.get("basePath", "")
        return f"{scheme}://{spec['host']}{base}".rstrip("/")
    
    return "/".join(fallback_url.split("/")[:3])


def create_mcp_server(spec_url: str, name: str = "API") -> FastMCP:
    """Factory generica."""
    spec = load_and_convert_spec(spec_url)
    base_url = extract_base_url(spec, spec_url)
    
    logger.info(f"Base URL: {base_url}")
    
    client = httpx.AsyncClient(base_url=base_url)
    
    return FastMCP.from_openapi(
        openapi_spec=spec,
        name=name,
        client=client
    )


def launch_inspector():
    """
    Modo desenvolvimento: lanca o MCP Inspector.
    As variaveis MCP_SPEC_URL e MCP_SERVER_NAME ja devem estar setadas no ambiente.
    """
    spec_url = os.getenv("MCP_SPEC_URL")
    server_name = os.getenv("MCP_SERVER_NAME", "Universal API")
    
    if not spec_url:
        logger.error("ERRO: MCP_SPEC_URL nao esta setada no ambiente")
        logger.error("Defina antes de rodar:")
        logger.error("  Windows: set MCP_SPEC_URL=https://...")
        logger.error("  Linux/Mac: export MCP_SPEC_URL=https://...")
        raise ValueError("MCP_SPEC_URL nao configurada no ambiente")
    
    logger.info(f"Lancando Inspector para: {server_name}")
    logger.info(f"URL: {spec_url}")
    
    cmd = [
        "npx",
        "@modelcontextprotocol/inspector",
        sys.executable,
        "main.py"
    ]
    
    logger.info(f"Executando: {' '.join(cmd)}")
    
    result = subprocess.run(cmd, shell=(sys.platform == "win32"))
    return result.returncode


def run_server():
    """
    Modo producao: roda o servidor MCP.
    Le MCP_SPEC_URL e MCP_SERVER_NAME do ambiente (setado pelo cliente MCP).
    """
    spec_url = os.getenv("MCP_SPEC_URL")
    server_name = os.getenv("MCP_SERVER_NAME", "Universal API")
    
    if not spec_url:
        logger.error("ERRO: MCP_SPEC_URL nao esta setada no ambiente")
        logger.error("O cliente MCP deve configurar esta variavel")
        raise ValueError("MCP_SPEC_URL nao configurada no ambiente")
    
    logger.info(f"Iniciando MCP Server: {server_name}")
    logger.info(f"Source: {spec_url}")
    
    mcp = create_mcp_server(spec_url, name=server_name)
    
    logger.info("Servidor pronto!")
    
    mcp.run()


# ============ MAIN ============

def main():
    parser = argparse.ArgumentParser(description="MCP Server Universal")
    parser.add_argument(
        "--inspect",
        action="store_true",
        help="Modo desenvolvimento: lanca o MCP Inspector (requer MCP_SPEC_URL setada)"
    )
    args = parser.parse_args()
    
    if args.inspect:
        logger.info("=" * 50)
        logger.info("MODO DESENVOLVIMENTO (Inspector)")
        logger.info("=" * 50)
        return launch_inspector()
    else:
        logger.info("=" * 50)
        logger.info("MODO PRODUCAO (Servidor MCP)")
        logger.info("=" * 50)
        run_server()


if __name__ == "__main__":
    sys.exit(main())