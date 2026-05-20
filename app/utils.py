import logging
import os
import socket
import subprocess
import sys
import threading
import time


# Configuração de Log Colorido
class ColoredFormatter(logging.Formatter):
    COLORS = {
        "DEBUG": "\033[36m",
        "INFO": "\033[32m",
        "WARNING": "\033[33m",
        "ERROR": "\033[31m",
        "CRITICAL": "\033[35m",
    }
    RESET = "\033[0m"

    def format(self, record):
        log_color = self.COLORS.get(record.levelname, self.RESET)
        record.levelname = f"{log_color}{record.levelname}{self.RESET}"
        return super().format(record)


handler = logging.StreamHandler(sys.stderr)
handler.setFormatter(ColoredFormatter("[%(levelname)s] %(message)s"))
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
logger.addHandler(handler)


def launch_inspector(url: str):
    """
    Lança o MCP Inspector conectando no servidor via URL.
    """
    logger.info(f"Lançando Inspector em: {url}")

    cmd = ["npx", "@modelcontextprotocol/inspector", "--url", url]

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
        logger.info("Lançando Inspector com servidor STDIO...")

        cmd = [
            "npx",
            "@modelcontextprotocol/inspector",
            sys.executable,
            os.path.join(os.path.dirname(__file__), "main.py"),
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

    from server import run_server_http, run_server_sse

    exc_info = []

    def start_server():
        try:
            if transport == "http":
                run_server_http(spec_url, name, host, port)
            elif transport == "sse":
                run_server_sse(spec_url, name, host, port)
        except Exception as e:
            exc_info.append(e)

    server_thread = threading.Thread(target=start_server, daemon=True)
    server_thread.start()

    # Aguarda servidor subir
    logger.info("Aguardando servidor iniciar...")
    deadline = time.time() + 10
    while time.time() < deadline:
        if exc_info:
            logger.error(f"Erro ao iniciar servidor: {exc_info[0]}")
            return 1
        if _is_port_open(host, port):
            logger.info("Servidor pronto!")
            break
        time.sleep(0.5)
    else:
        if exc_info:
            logger.error(f"Erro ao iniciar servidor: {exc_info[0]}")
        else:
            logger.error(f"Servidor não responde em {host}:{port} — verifique se o backend (porta 8000) está rodando")
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
