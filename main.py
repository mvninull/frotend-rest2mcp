from fastmcp import FastMCP
import httpx
import json
import subprocess
import os
import sys
import argparse


def load_and_convert_spec(url: str) -> dict:
    """
    Carrega uma spec OpenAPI/Swagger de uma URL e converte para v3 se necessário.
    Usa swagger2openapi via npx quando precisar converter.
    """
    
    print(f"📥 Baixando spec de {url}...")
    response = httpx.get(url, timeout=30.0)
    response.raise_for_status()
    data = response.json()
    
    # Detecta versão
    if "openapi" in data and str(data["openapi"]).startswith("3"):
        print(f"✅ OpenAPI {data['openapi']} detectado — usando diretamente")
        return data
    
    if "swagger" in data and str(data["swagger"]).startswith("2"):
        print(f"⚠️  Swagger {data['swagger']} detectado — convertendo para OpenAPI 3.0...")
        return _convert_with_npx(data)
    
    raise ValueError(
        f"Versão não suportada: {data.get('openapi') or data.get('swagger', 'desconhecida')}"
    )


def _convert_with_npx(original_data: dict) -> dict:
    """
    Converte Swagger 2.0 → OpenAPI 3.0 usando swagger2openapi via npx.
    """
    temp_input = "_temp_swagger2.json"
    temp_output = "_temp_openapi3.json"
    
    try:
        # Salva spec original em arquivo temporário
        with open(temp_input, "w", encoding="utf-8") as f:
            json.dump(original_data, f, indent=2)
        
        # Executa swagger2openapi via npx
        print(f"🔧 Executando: npx swagger2openapi {temp_input} -o {temp_output}")
        
        result = subprocess.run(
            ["npx", "swagger2openapi", temp_input, "-o", temp_output],
            capture_output=True,
            text=True,
            shell=(sys.platform == "win32")
        )
        
        # Se npx falhar, tenta global
        if result.returncode != 0:
            print(f"⚠️  npx falhou, tentando global...")
            result = subprocess.run(
                ["swagger2openapi", temp_input, "-o", temp_output],
                capture_output=True,
                text=True,
                shell=(sys.platform == "win32")
            )
            if result.returncode != 0:
                raise RuntimeError(f"Conversão falhou: {result.stderr}")
        
        # Carrega o resultado convertido
        with open(temp_output, "r", encoding="utf-8") as f:
            converted = json.load(f)
        
        print(f"✅ Conversão concluída!")
        return converted
        
    finally:
        # Limpa arquivos temporários
        for f in [temp_input, temp_output]:
            if os.path.exists(f):
                os.remove(f)


def extract_base_url(spec: dict, fallback_url: str) -> str:
    """
    Extrai a URL base da spec convertida.
    Prioridade: servers[0].url → host+basePath (Swagger legado) → URL original
    """
    # OpenAPI 3.0: servers
    if "servers" in spec and spec["servers"]:
        return spec["servers"][0]["url"].rstrip("/")
    
    # Swagger 2.0 legado (caso a spec original seja v2 e não convertida)
    if "host" in spec:
        scheme = spec.get("schemes", ["https"])[0]
        base = spec.get("basePath", "")
        return f"{scheme}://{spec['host']}{base}".rstrip("/")
    
    # Fallback: extrai do endpoint da spec
    return "/".join(fallback_url.split("/")[:3])


def create_mcp_server(spec_url: str, name: str = "API") -> FastMCP:
    """
    Factory genérica: cria um servidor MCP a partir de qualquer URL de spec.
    """
    spec = load_and_convert_spec(spec_url)
    base_url = extract_base_url(spec, spec_url)
    
    print(f"🌐 Base URL: {base_url}")
    
    client = httpx.AsyncClient(base_url=base_url)
    
    return FastMCP.from_openapi(
        openapi_spec=spec,
        name=name,
        client=client
    )


# ============ CONFIGURAÇÃO VIA VARIÁVEL DE AMBIENTE ============

def main():
    parser = argparse.ArgumentParser(description="MCP Server Universal")
    parser.add_argument(
        "--url",
        help="URL da spec OpenAPI/Swagger (ex: https://api.example.com/swagger.json)",
        default=os.getenv("MCP_SPEC_URL")
    )
    parser.add_argument(
        "--name",
        help="Nome do servidor MCP",
        default=os.getenv("MCP_SERVER_NAME", "Universal API")
    )
    args = parser.parse_args()
    
    if not args.url:
        print("❌ Erro: Especifique a URL com --url ou variável MCP_SPEC_URL")
        print("\nExemplos:")
        print('  python main.py --url https://petstore.swagger.io/v2/swagger.json --name "PetStore"')
        print('  set MCP_SPEC_URL=https://petstore.swagger.io/v2/swagger.json && python main.py')
        sys.exit(1)
    
    print(f"🚀 Iniciando MCP Server: {args.name}")
    print(f"📋 Source: {args.url}")
    print("-" * 50)
    
    mcp = create_mcp_server(args.url, name=args.name)
    
    print("-" * 50)
    print("✅ Servidor pronto!")
    
    mcp.run()


if __name__ == "__main__":
    main()