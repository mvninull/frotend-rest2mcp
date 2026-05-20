import json
import os
import subprocess
import sys
import time
from urllib.parse import urlparse

import httpx
from fastmcp import FastMCP

try:
    from .utils import logger
except ImportError:
    from utils import logger


class LoggedTransport(httpx.AsyncBaseTransport):
    def __init__(self, inner: httpx.AsyncBaseTransport, log_func=None, server_id=""):
        self.inner = inner
        self.log_func = log_func
        self.server_id = server_id

    def _truncate(self, data: bytes | None, max_len: int = 5000) -> str | None:
        if not data:
            return None
        try:
            text = data.decode("utf-8", errors="replace")
            if len(text) > max_len:
                text = text[:max_len] + f"\n... [truncated {len(text)} chars]"
            return text
        except Exception:
            return None

    async def handle_async_request(self, request):
        start = time.time()
        req_body = self._truncate(request.content)
        try:
            response = await self.inner.handle_async_request(request)
            duration = (time.time() - start) * 1000
            if self.log_func:
                resp_body = None
                try:
                    raw = await response.aread()
                    resp_body = self._truncate(raw)
                except Exception:
                    resp_body = None
                self.log_func(
                    self.server_id,
                    str(request.url),
                    response.status_code,
                    duration,
                    method=request.method,
                    request_body=req_body,
                    response_body=resp_body,
                )
            return response
        except Exception:
            duration = (time.time() - start) * 1000
            if self.log_func:
                self.log_func(
                    self.server_id, str(request.url), 0, duration, method=request.method, request_body=req_body
                )
            raise


class DynamicAuth(httpx.Auth):
    def __init__(self, manager):
        self.manager = manager

    def auth_flow(self, request):
        if self.manager.token:
            request.headers["Authorization"] = f"Bearer {self.manager.token}"
        yield request


class MCPServerManager:
    def __init__(self, spec_url: str, name: str, spec: dict | None = None, server_id: str = "", log_func=None):
        self.spec_url = spec_url
        self.name = name
        self.server_id = server_id
        self.log_func = log_func
        self.token = None

        if spec is not None:
            self.spec = spec
        else:
            self.spec = self.load_and_convert_spec(spec_url)

        if self.spec.get("swagger") == "2.0":
            logger.info("Convertendo Swagger 2.0 to OpenAPI 3.0")
            self.spec = self._swagger2_to_openapi3(self.spec)

        parsed = urlparse(spec_url)
        self.base_url = f"{parsed.scheme}://{parsed.netloc}"

        if "servers" in self.spec and self.spec["servers"]:
            server_url = self.spec["servers"][0]["url"]
            if server_url.startswith("/"):
                self.base_url = f"{self.base_url}{server_url.rstrip('/')}"
            else:
                self.base_url = server_url.rstrip("/")

        logger.info(f"Base URL configurada: {self.base_url}")

        inner = httpx.AsyncHTTPTransport()
        transport = LoggedTransport(inner, log_func=log_func, server_id=server_id)
        self.client = httpx.AsyncClient(
            base_url=self.base_url,
            auth=DynamicAuth(self),
            timeout=30.0,
            follow_redirects=True,
            transport=transport,
        )

        self.mcp = FastMCP.from_openapi(
            openapi_spec=self.spec,
            name=self.name,
            client=self.client,
        )

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

    def _get_body_schema(self, path: str) -> dict | None:
        methods = self.spec.get("paths", {}).get(path, {})
        if not methods:
            return None
        post = methods.get("post", {})
        content = post.get("requestBody", {}).get("content", {})
        for ct in ("application/json", "application/x-www-form-urlencoded"):
            schema = content.get(ct, {}).get("schema", {})
            if schema:
                return schema
        return None

    def _setup_dynamic_login(self):
        email_login_path = None
        oauth_paths: dict[str, str] = {}
        spec_paths = self.spec.get("paths", {})
        for path, methods in spec_paths.items():
            if "post" not in methods:
                continue
            lower = path.lower()
            if any(k in lower for k in ["login", "token", "auth/"]):
                if email_login_path is None:
                    email_login_path = path
            for provider in ("google", "github", "apple"):
                if provider in lower:
                    oauth_paths[provider] = path

        _base_url = self.base_url
        _email_login_path = email_login_path
        _oauth_paths = oauth_paths
        _spec = self.spec

        @self.mcp.tool(name="login")
        async def smart_login(
            username: str | None = None,
            password: str | None = None,
            provider: str | None = None,
            provider_token: str | None = None,
        ) -> str:
            """Faz login na API e configura o token automaticamente.

            Suporta múltiplos fluxos:
            - Email/senha: informe username e password
            - OAuth (Google/GitHub/Apple): informe provider e provider_token
            """
            if provider and provider_token:
                provider_lower = provider.lower()
                oauth_path = _oauth_paths.get(provider_lower)
                if oauth_path:
                    url_to_call = oauth_path if oauth_path.startswith("/") else f"/{oauth_path}"
                elif _email_login_path:
                    url_to_call = _email_login_path if _email_login_path.startswith("/") else f"/{_email_login_path}"
                else:
                    url_to_call = f"/auth/{provider_lower}"

                payload_candidates = [
                    {"token": provider_token},
                    {"access_token": provider_token},
                    {"id_token": provider_token},
                    {"code": provider_token},
                    {"credential": provider_token},
                ]
                schema = self._get_body_schema(url_to_call)
                if schema:
                    props = schema.get("properties", {})
                    if props:
                        body_key = next(iter(props), None)
                        if body_key:
                            payload_candidates.insert(0, {body_key: provider_token})

                async with httpx.AsyncClient(base_url=_base_url) as auth_client:
                    for payload in payload_candidates:
                        for attempt in range(2):
                            if attempt == 0:
                                resp = await auth_client.post(url_to_call, json=payload)
                            else:
                                resp = await auth_client.post(url_to_call, data=payload)
                            if resp.status_code in (200, 201):
                                data = resp.json()
                                token = data.get("access_token") or data.get("token") or data.get("jwt") or data.get("id_token")
                                if token:
                                    self.token = token
                                    return "✅ Login realizado com sucesso!"
                                return "⚠️ Login OK, mas token não encontrado."
                            if resp.status_code not in (400, 401, 422):
                                return f"❌ Erro ({resp.status_code}): {resp.text}"
                    return f"❌ Erro (401): Nenhum formato de payload funcionou."
            elif username and password:
                if not _email_login_path:
                    return "⚠️ Nenhum endpoint de login encontrado na spec."
                url_to_call = _email_login_path if _email_login_path.startswith("/") else f"/{_email_login_path}"
                payload = {"username": username, "password": password}
                async with httpx.AsyncClient(base_url=_base_url) as auth_client:
                    resp = await auth_client.post(url_to_call, json=payload)
                    if resp.status_code == 422:
                        resp = await auth_client.post(url_to_call, data=payload)
                    if resp.status_code == 200:
                        data = resp.json()
                        token = data.get("access_token") or data.get("token") or data.get("jwt")
                        if token:
                            self.token = token
                            return "✅ Login realizado com sucesso!"
                        return "⚠️ Login OK, mas token não encontrado."
                    return f"❌ Erro ({resp.status_code}): {resp.text}"
            else:
                return "⚠️ Informe username+password (email/senha) ou provider+provider_token (OAuth)."

        @self.mcp.tool()
        async def set_token(token: str) -> str:
            """Define manualmente um token JWT para autenticação nas chamadas seguintes.
            Use esta ferramenta quando já possui um token (ex: obtido via OAuth Google/GitHub)."""
            self.token = token
            return "✅ Token configurado com sucesso!"

        @self.mcp.tool()
        async def session_status() -> str:
            """Verifica o estado atual da autenticação."""
            return f"Autenticado: {bool(self.token)} | API: {self.base_url}"


# ESTA FUNÇÃO PRECISA ESTAR FORA DA CLASSE (NA RAIZ DO ARQUIVO)
def create_mcp_server(spec_url: str, name: str) -> FastMCP:
    manager = MCPServerManager(spec_url, name)
    return manager.mcp
