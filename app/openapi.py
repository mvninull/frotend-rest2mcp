import os
import sys
import subprocess
import httpx
import json
from urllib.parse import urlparse # Nativo, não precisa de pip
from fastmcp import FastMCP
from utils import logger

class DynamicAuth(httpx.Auth):
    """Porteiro dinâmico que injeta o token em cada requisição."""
    def __init__(self, manager):
        self.manager = manager

    def auth_flow(self, request):
        if self.manager.token:
            request.headers["Authorization"] = f"Bearer {self.manager.token}"
        yield request

class MCPServerManager:
    def __init__(self, spec_url: str, name: str):
        self.spec_url = spec_url
        self.name = name
        self.token = None

        # 1. Carrega a especificação
        self.spec = self.load_and_convert_spec(spec_url)

        # 2. Define a URL Base
        parsed = urlparse(spec_url)
        self.base_url = f"{parsed.scheme}://{parsed.netloc}"

        if "servers" in self.spec and self.spec["servers"]:
            server_url = self.spec["servers"][0]["url"]
            if server_url.startswith("/"):
                self.base_url = f"{self.base_url}{server_url.rstrip('/')}"
            else:
                self.base_url = server_url.rstrip("/")
        
        logger.info(f"Base URL configurada: {self.base_url}")

        # 3. Cria o cliente com o Auth Dinâmico
        self.client = httpx.AsyncClient(
            base_url=self.base_url, 
            auth=DynamicAuth(self), 
            timeout=30.0,
            follow_redirects=True
        )

        # 4. Cria o MCP a partir do OpenAPI
        self.mcp = FastMCP.from_openapi(
            openapi_spec=self.spec, 
            name=self.name, 
            client=self.client
        )

        # 5. Configura o login dinâmico
        self._setup_dynamic_login()

    def load_and_convert_spec(self, url: str) -> dict:
        logger.info(f"Baixando spec de: {url}")
        response = httpx.get(url, timeout=30.0)
        response.raise_for_status()
        spec = response.json()
        
        # Converte se for Swagger 2.0
        if spec.get("swagger") == "2.0":
            logger.info("Convertendo Swagger 2.0 → OpenAPI 3.0")
            return self._swagger2_to_openapi3(spec)
        return spec

    def _swagger2_to_openapi3(self, spec: dict) -> dict:
        temp_input, temp_output = "_temp_s2.json", "_temp_o3.json"
        try:
            with open(temp_input, "w", encoding="utf-8") as f:
                json.dump(spec, f)
            shell_val = sys.platform == "win32"
            subprocess.run(
                ["npx", "swagger2openapi", temp_input, "-o", temp_output],
                check=True, shell=shell_val, capture_output=True,
            )
            with open(temp_output, "r", encoding="utf-8") as f:
                return json.load(f)
        finally:
            for f in [temp_input, temp_output]:
                if os.path.exists(f): os.remove(f)

    def _setup_dynamic_login(self):
        login_path = None
        for path, methods in self.spec.get("paths", {}).items():
            if any(k in path.lower() for k in ["login", "token", "auth/"]):
                if "post" in methods:
                    login_path = path
                    break

        if login_path:
            @self.mcp.tool(name="login")
            async def smart_login(username: str, password: str) -> str:
                """Faz login na API e configura o token automaticamente."""
                payload = {"username": username, "password": password}
                url_to_call = login_path if login_path.startswith("/") else f"/{login_path}"
                
                async with httpx.AsyncClient(base_url=self.base_url) as auth_client:
                    resp = await auth_client.post(url_to_call, json=payload)
                    if resp.status_code == 422:
                        resp = await auth_client.post(url_to_call, data=payload)

                    if resp.status_code == 200:
                        data = resp.json()
                        token = data.get("access_token") or data.get("token") or data.get("jwt")
                        if token:
                            self.token = token
                            return f"✅ Login realizado com sucesso!"
                        return "⚠️ Login OK, mas token não encontrado."
                    return f"❌ Erro ({resp.status_code}): {resp.text}"

        @self.mcp.tool()
        async def session_status() -> str:
            """Verifica o estado atual da autenticação."""
            return f"Autenticado: {bool(self.token)} | API: {self.base_url}"

# ESTA FUNÇÃO PRECISA ESTAR FORA DA CLASSE (NA RAIZ DO ARQUIVO)
def create_mcp_server(spec_url: str, name: str) -> FastMCP:
    manager = MCPServerManager(spec_url, name)
    return manager.mcp