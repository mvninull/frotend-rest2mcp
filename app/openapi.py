from fastmcp import FastMCP
import httpx
import json
import subprocess
import os
import sys
from utils import logger


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

        shell_val = sys.platform == "win32"
        subprocess.run(
            ["npx", "swagger2openapi", temp_input, "-o", temp_output], check=True, shell=shell_val, capture_output=True
        )

        with open(temp_output, "r", encoding="utf-8") as f:
            return json.load(f)
    finally:
        for f in [temp_input, temp_output]:
            if os.path.exists(f):
                os.remove(f)


def create_mcp_server(spec_url: str, name: str) -> FastMCP:
    spec = load_and_convert_spec(spec_url)
    # Extrai base URL simples
    base_url = spec["servers"][0]["url"] if "servers" in spec else spec_url.rsplit("/", 1)[0]

    logger.info(f"Criando servidor FastMCP: {name} | Base API: {base_url}")
    return FastMCP.from_openapi(openapi_spec=spec, name=name, client=httpx.AsyncClient(base_url=base_url))
