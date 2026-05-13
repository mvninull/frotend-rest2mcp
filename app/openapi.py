import os
import sys
import subprocess
import httpx
import json
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

        # 1. Carrega a especificação primeiro
        self.spec = self.load_and_convert_spec(spec_url)

        # 2. Define a URL Base
        if "servers" in self.spec and self.spec["servers"]:
            self.base_url = self.spec["servers"][0]["url"]
        else:
            self.base_url = spec_url.rsplit("/", 1)[0]

        # 3. Cria o cliente com o Auth Dinâmico
        self.client = httpx.AsyncClient(base_url=self.base_url, auth=DynamicAuth(self), timeout=30.0)

        # 4. CRUCIAL: Cria o MCP a partir do OpenAPI (Isso carrega todas as ferramentas da API)
        self.mcp = FastMCP.from_openapi(openapi_spec=self.spec, name=self.name, client=self.client)

        # 5. Agora adicionamos/sobrescrevemos o login e status
        self._setup_dynamic_login()

    def load_and_convert_spec(self, url: str) -> dict:
        response = httpx.get(url, timeout=30.0)
        response.raise_for_status()
        spec = response.json()
        if spec.get("swagger") == "2.0":
            logger.info("Convertendo Swagger 2.0 → OpenAPI 3.0")
            spec = self._swagger2_to_openapi3(spec)
        return spec

    def _swagger2_to_openapi3(self, spec: dict) -> dict:
        temp_input, temp_output = "_temp_s2.json", "_temp_o3.json"
        try:
            with open(temp_input, "w", encoding="utf-8") as f:
                json.dump(spec, f)
            shell_val = sys.platform == "win32"
            subprocess.run(
                ["npx", "swagger2openapi", temp_input, "-o", temp_output],
                check=True,
                shell=shell_val,
                capture_output=True,
            )
            with open(temp_output, "r", encoding="utf-8") as f:
                return json.load(f)
        finally:
            for f in [temp_input, temp_output]:
                if os.path.exists(f):
                    os.remove(f)

    def _setup_dynamic_login(self):
        login_path = None
        login_op_id = None

        # Busca o endpoint de login no spec
        for path, methods in self.spec.get("paths", {}).items():
            if any(k in path.lower() for k in ["login", "token", "auth/"]):
                if "post" in methods:
                    login_path = path
                    login_op_id = methods["post"].get("operationId")
                    break

        # Se encontrou o login, vamos sobrescrever a ferramenta automática pela nossa
        if login_op_id:
            logger.info(f"Substituindo ferramenta: {login_op_id}")

            @self.mcp.tool(name=login_op_id)
            async def smart_login(username: str, password: str) -> str:
                """Faz login e ativa o token globalmente para todas as outras ferramentas."""
                payload = {"username": username, "password": password}

                # Usamos um cliente limpo para o login
                async with httpx.AsyncClient(base_url=self.base_url) as auth_client:
                    resp = await auth_client.post(login_path, json=payload)
                    if resp.status_code == 422:
                        resp = await auth_client.post(login_path, data=payload)

                    if resp.status_code == 200:
                        data = resp.json()
                        new_token = data.get("access_token") or data.get("token") or data.get("jwt")
                        if new_token:
                            self.token = new_token
                            return f"Login realizado em '{login_path}'. Token configurado."
                        return "Login OK, mas o token não foi encontrado na resposta."
                    return f"Erro no login: {resp.text}"

        # Ferramenta extra para conferir se estamos logados
        @self.mcp.tool()
        async def session_status() -> str:
            """Verifica o estado atual da autenticação."""
            return f"Autenticado: {bool(self.token)} | URL: {self.base_url}"


def create_mcp_server(spec_url: str, name: str) -> FastMCP:
    manager = MCPServerManager(spec_url, name)
    return manager.mcp
