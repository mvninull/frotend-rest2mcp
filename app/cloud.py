import os
import re
import json
import time
import asyncio
import socket
import secrets
import string
import threading
import uvicorn
from urllib.parse import urlparse
import httpx
from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, Response, JSONResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy import desc

try:
    from .cloud_models import ServerDB, LogDB, init_db, get_db, SessionLocal
    from .openapi import MCPServerManager, create_mcp_server
    from .utils import logger
except ImportError:
    from cloud_models import ServerDB, LogDB, init_db, get_db, SessionLocal
    from openapi import MCPServerManager, create_mcp_server
    from utils import logger


def _make_log_func(server_id: str):
    def log_func(sid: str, tool: str, status: int, duration: float):
        try:
            db = SessionLocal()
            log = LogDB(
                server_id=sid or server_id,
                tool_called=str(tool),
                status_code=status,
                duration_ms=duration,
            )
            db.add(log)
            db.commit()
            db.close()
        except Exception:
            pass

    return log_func


GATEWAY_HOST = os.getenv("GATEWAY_HOST", "0.0.0.0")
GATEWAY_PORT = int(os.getenv("GATEWAY_PORT", "8080"))
PUBLIC_URL = os.getenv("PUBLIC_URL", f"http://localhost:{GATEWAY_PORT}")


def _find_free_port():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def _generate_id(prefix="srv", length=8):
    chars = string.ascii_lowercase + string.digits
    return f"{prefix}_{''.join(secrets.choice(chars) for _ in range(length))}"


def _generate_apikey():
    chars = string.ascii_lowercase + string.digits
    return f"r2m_live_{''.join(secrets.choice(chars) for _ in range(16))}"


def _validate_server(server_id: str, apikey: str, db: Session):
    server = (
        db.query(ServerDB)
        .filter(
            ServerDB.server_id == server_id,
            ServerDB.apikey == apikey,
        )
        .first()
    )
    if not server:
        return None
    return server


class ActiveServer:
    def __init__(self, server: ServerDB, transport: str = "sse"):
        self.server_id = server.server_id
        self.apikey = server.apikey
        self.name = server.name
        self.spec_url = server.spec_url
        self.spec_data = server.spec_data
        self._transport = transport
        self.manager: MCPServerManager | None = None
        self.port: int | None = None
        self.uv_server = None
        self.sse_app = None

    async def ensure_running(self, transport: str | None = None):
        if self.uv_server is not None and not self.uv_server.should_exit:
            return
        spec_data = json.loads(self.spec_data) if self.spec_data else None
        self.manager = MCPServerManager(
            spec_url=self.spec_url,
            name=self.name,
            spec=spec_data,
            server_id=self.server_id,
            log_func=_make_log_func(self.server_id),
        )
        transport_type = transport or self._transport
        self.sse_app = self.manager.mcp.http_app(transport=transport_type)
        self.port = _find_free_port()

        config = uvicorn.Config(
            app=self.sse_app,
            host="127.0.0.1",
            port=self.port,
            log_level="error",
        )
        self.uv_server = uvicorn.Server(config)

        def _run_server():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(self.uv_server.serve())

        t = threading.Thread(target=_run_server, daemon=True)
        t.start()

        deadline = time.time() + 10
        while time.time() < deadline:
            if getattr(self.uv_server, "started", False):
                import socket as _socket

                try:
                    s = _socket.create_connection(("127.0.0.1", self.port), timeout=1)
                    s.close()
                    break
                except (ConnectionRefusedError, OSError):
                    await asyncio.sleep(0.2)
                    continue
            await asyncio.sleep(0.1)
        logger.info(f"MCP server {self.server_id} rodando em 127.0.0.1:{self.port}")

    async def stop(self):
        if self.uv_server:
            self.uv_server.should_exit = True
            self.uv_server = None
        self.sse_app = None


active_servers: dict[str, ActiveServer] = {}


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    logger.info("Cloud Gateway iniciado com banco de dados SQLite")
    yield
    for key in list(active_servers.keys()):
        await active_servers[key].stop()
    active_servers.clear()


app = FastAPI(
    title="rest2mcp Cloud Gateway",
    description="API de Gestão e Gateway de Conexão para servidores MCP persistentes na nuvem",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─── Schemas ───────────────────────────────────────────────────────────────────


class CreateServerRequest(BaseModel):
    name: str
    spec_url: str
    transport: str = "sse"


class ServerResponse(BaseModel):
    server_id: str
    apikey: str
    name: str
    status: str
    spec_url: str
    transport: str
    url_sse: str
    created_at: str


class ServerListItem(BaseModel):
    server_id: str
    name: str
    status: str
    url_sse: str
    created_at: str


class UpdateServerRequest(BaseModel):
    name: str | None = None
    status: str | None = None
    transport: str | None = None


class LogEntry(BaseModel):
    timestamp: str
    tool_called: str
    status_code: int
    duration_ms: float


# ─── Management API ────────────────────────────────────────────────────────────


@app.post("/v1/servers", status_code=201)
async def create_server(req: CreateServerRequest, db: Session = Depends(get_db)):
    logger.info(f"Criando servidor: {req.name} ({req.spec_url})")

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(req.spec_url)
            response.raise_for_status()
            spec_data = response.json()
    except httpx.HTTPError as e:
        raise HTTPException(status_code=400, detail=f"Erro ao baixar spec: {e}")
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Spec não é um JSON válido")

    if spec_data.get("swagger") == "2.0":
        logger.info("Convertendo Swagger 2.0 → OpenAPI 3.0")
        try:
            temp = MCPServerManager(spec_url=req.spec_url, name=req.name)
            spec_data = temp.spec
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Erro ao converter Swagger 2.0: {e}")

    server_id = _generate_id()
    apikey = _generate_apikey()

    parsed_url = urlparse(req.spec_url)
    target_url = f"{parsed_url.scheme}://{parsed_url.netloc}"
    if "servers" in spec_data and spec_data["servers"]:
        first = spec_data["servers"][0]["url"]
        if first.startswith("/"):
            target_url = target_url + first.rstrip("/")
        else:
            target_url = first.rstrip("/")

    transport = req.transport if hasattr(req, "transport") and req.transport in ("sse", "http") else "sse"

    record = ServerDB(
        server_id=server_id,
        apikey=apikey,
        name=req.name,
        spec_url=req.spec_url,
        spec_data=json.dumps(spec_data),
        target_url=target_url,
        transport=transport,
        is_active=True,
    )
    db.add(record)
    db.commit()

    suffix = "sse" if transport == "sse" else "mcp"
    url_sse = f"{PUBLIC_URL}/v1/{server_id}/{apikey}/{suffix}"
    logger.info(f"Servidor criado: {server_id} ({transport}) -> {url_sse}")

    return ServerResponse(
        server_id=server_id,
        apikey=apikey,
        name=req.name,
        status="active",
        spec_url=req.spec_url,
        transport=transport,
        url_sse=url_sse,
        created_at=record.created_at.isoformat(),
    )


@app.get("/v1/servers")
async def list_servers(db: Session = Depends(get_db)):
    servers = db.query(ServerDB).order_by(desc(ServerDB.created_at)).all()
    result = []
    for s in servers:
        t = s.transport or "http"
        suffix = "sse" if t == "sse" else "mcp"
        url = f"{PUBLIC_URL}/v1/{s.server_id}/{s.apikey}/{suffix}"
        result.append(
            ServerListItem(
                server_id=s.server_id,
                name=s.name,
                status="active" if s.is_active else "inactive",
                url_sse=url,
                created_at=s.created_at.isoformat(),
            )
        )
    return result


@app.patch("/v1/servers/{server_id}")
async def update_server(server_id: str, req: UpdateServerRequest, db: Session = Depends(get_db)):
    record = db.query(ServerDB).filter(ServerDB.server_id == server_id).first()
    if not record:
        raise HTTPException(status_code=404, detail="Servidor não encontrado")

    if req.name is not None:
        record.name = req.name
    if req.status is not None:
        if req.status not in ("active", "inactive"):
            raise HTTPException(status_code=422, detail="status deve ser 'active' ou 'inactive'")
        record.is_active = req.status == "active"
        if not record.is_active:
            key = f"{record.server_id}:{record.apikey}"
            if key in active_servers:
                await active_servers[key].stop()
                del active_servers[key]
    if req.transport is not None:
        if req.transport not in ("sse", "http"):
            raise HTTPException(status_code=422, detail="transport deve ser 'sse' ou 'http'")
        record.transport = req.transport
        key = f"{record.server_id}:{record.apikey}"
        if key in active_servers:
            await active_servers[key].stop()
            del active_servers[key]

    db.commit()

    t = record.transport or "http"
    suffix = "sse" if t == "sse" else "mcp"
    url = f"{PUBLIC_URL}/v1/{record.server_id}/{record.apikey}/{suffix}"
    return ServerListItem(
        server_id=record.server_id,
        name=record.name,
        status="active" if record.is_active else "inactive",
        url_sse=url,
        created_at=record.created_at.isoformat(),
    )


@app.delete("/v1/servers/{server_id}", status_code=204)
async def delete_server(server_id: str, db: Session = Depends(get_db)):
    record = db.query(ServerDB).filter(ServerDB.server_id == server_id).first()
    if not record:
        raise HTTPException(status_code=404, detail="Servidor não encontrado")

    key = f"{record.server_id}:{record.apikey}"
    if key in active_servers:
        await active_servers[key].stop()
        del active_servers[key]

    db.delete(record)
    db.commit()


# ─── Logs Endpoint ─────────────────────────────────────────────────────────────


@app.get("/v1/servers/{server_id}/logs")
async def get_logs(server_id: str, limit: int = 50, offset: int = 0, db: Session = Depends(get_db)):
    server = db.query(ServerDB).filter(ServerDB.server_id == server_id).first()
    if not server:
        raise HTTPException(status_code=404, detail="Servidor não encontrado")

    logs = (
        db.query(LogDB)
        .filter(LogDB.server_id == server_id)
        .order_by(desc(LogDB.timestamp))
        .offset(offset)
        .limit(limit)
        .all()
    )

    return [
        LogEntry(
            timestamp=log.timestamp.isoformat(),
            tool_called=log.tool_called,
            status_code=log.status_code,
            duration_ms=log.duration_ms,
        )
        for log in logs
    ]


# ─── Gateway SSE / MCP Routes ─────────────────────────────────────────────────


@app.get("/v1/{server_id}/{apikey}/sse")
async def sse_connection(server_id: str, apikey: str, request: Request):
    db = SessionLocal()
    try:
        server = _validate_server(server_id, apikey, db)
        if not server:
            return Response(status_code=404, content="Servidor não encontrado")
        if not server.is_active:
            return Response(status_code=403, content="Servidor inativo")
    finally:
        db.close()

    key = f"{server_id}:{apikey}"
    if key not in active_servers:
        active_servers[key] = ActiveServer(server)

    active = active_servers[key]
    await active.ensure_running(transport="sse")

    internal_sse_url = f"http://127.0.0.1:{active.port}/sse"

    async def event_stream():
        try:
            for attempt in range(60):
                try:
                    async with httpx.AsyncClient(timeout=2.0) as client:
                        async with client.stream("GET", internal_sse_url) as resp:
                            if resp.status_code != 200:
                                yield f"event: error\ndata: Internal server error ({resp.status_code})\n\n"
                                return
                            async for line in resp.aiter_lines():
                                if line.startswith("data: /messages"):
                                    query = line.split("?", 1)[1].rstrip() if "?" in line else ""
                                    sep = "?" if query else ""
                                    yield f"data: /v1/{server_id}/{apikey}/messages{sep}{query}\n"
                                else:
                                    yield line + "\n"
                            return
                except httpx.ConnectError:
                    if attempt < 59:
                        await asyncio.sleep(0.5)
                        continue
                    return
                except httpx.ReadTimeout:
                    continue
                except Exception:
                    continue
        except Exception as e:
            logger.error(f"Erro no proxy SSE ({server_id}): {e}")
        finally:
            logger.info(f"Cliente SSE desconectado: {server_id}")

    return StreamingResponse(event_stream(), media_type="text/event-stream")


@app.post("/v1/{server_id}/{apikey}/messages")
async def messages_endpoint(server_id: str, apikey: str, request: Request):
    key = f"{server_id}:{apikey}"
    if key not in active_servers:
        return Response(status_code=404, content="Nenhuma sessão ativa para este servidor")

    active = active_servers[key]
    if not active.uv_server or active.uv_server.should_exit:
        return Response(status_code=503, content="Servidor MCP não está rodando")

    body = await request.body()
    ct = request.headers.get("content-type", "application/json")

    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.post(
            f"http://127.0.0.1:{active.port}/messages",
            content=body,
            headers={"content-type": ct},
        )

    return Response(
        content=resp.content,
        status_code=resp.status_code,
        media_type=resp.headers.get("content-type", "application/json"),
    )


async def _get_or_start_mcp(server_id: str, apikey: str):
    key = f"{server_id}:{apikey}"
    db = SessionLocal()
    try:
        server = _validate_server(server_id, apikey, db)
        if not server:
            return None, Response(status_code=404, content="Servidor não encontrado")
        if not server.is_active:
            return None, Response(status_code=403, content="Servidor inativo")
    finally:
        db.close()

    if key not in active_servers:
        active_servers[key] = ActiveServer(server)

    active = active_servers[key]
    await active.ensure_running(transport="http")
    return active, None


@app.post("/v1/{server_id}/{apikey}/mcp")
async def mcp_endpoint(server_id: str, apikey: str, request: Request):
    active, err = await _get_or_start_mcp(server_id, apikey)
    if err:
        return err

    body = await request.body()
    sess = request.headers.get("Mcp-Session-Id", "")
    query = request.scope.get("query_string", b"").decode()

    url = f"http://127.0.0.1:{active.port}/mcp"
    if query:
        url += "?" + query

    headers = {
        "content-type": request.headers.get("content-type", "application/json"),
        "accept": request.headers.get("accept", "application/json, text/event-stream"),
    }
    if sess:
        headers["Mcp-Session-Id"] = sess

    async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
        resp = await client.post(url, content=body, headers=headers)

    resp_headers = {}
    for h in ("content-type", "mcp-session-id"):
        val = resp.headers.get(h)
        if val:
            resp_headers[h] = val

    return Response(content=resp.content, status_code=resp.status_code, headers=resp_headers)


@app.get("/v1/{server_id}/{apikey}/mcp")
async def mcp_get_stream(server_id: str, apikey: str, request: Request):
    active, err = await _get_or_start_mcp(server_id, apikey)
    if err:
        return err

    query = request.scope.get("query_string", b"").decode()
    url = f"http://127.0.0.1:{active.port}/mcp"
    if query:
        url += "?" + query

    headers = {
        "accept": request.headers.get("accept", "text/event-stream"),
    }
    sess = request.headers.get("Mcp-Session-Id", "")
    if sess:
        headers["Mcp-Session-Id"] = sess

    async def proxy_stream():
        async with httpx.AsyncClient(timeout=None) as client:
            async with client.stream("GET", url, headers=headers) as resp:
                async for chunk in resp.aiter_bytes():
                    yield chunk

    return StreamingResponse(proxy_stream(), media_type="text/event-stream")


# ─── Health Check ──────────────────────────────────────────────────────────────


@app.get("/health")
async def health():
    return {"status": "ok", "active_servers": len(active_servers)}


# ─── Entrypoint ────────────────────────────────────────────────────────────────


def main():
    logger.info(f"Iniciando Cloud Gateway em {GATEWAY_HOST}:{GATEWAY_PORT}")
    uvicorn.run(
        "app.cloud:app",
        host=GATEWAY_HOST,
        port=GATEWAY_PORT,
        reload=bool(os.getenv("GATEWAY_RELOAD", "0") == "1"),
    )


if __name__ == "__main__":
    main()
