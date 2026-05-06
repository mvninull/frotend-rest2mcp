# rest2mcp

**Converta QUALQUER API em um Servidor MCP — sem escrever código.**

Servidor MCP genérico que converte automaticamente qualquer API OpenAPI/Swagger em um servidor MCP, permitindo que LLMs interajam com sua API através do protocolo Model Context Protocol (MCP).

## ✨ Destaques Fundamentais

- **🚀 Zero Código**: Apenas configure a URL da especificação (`MCP_SPEC_URL`) — sem desenvolver servidores MCP individuais
- **⚡ Conversão em Segundos**: Sua API vira servidor MCP instantaneamente, pronta para uso
- **🔗 Múltiplas APIs**: Configure várias APIs no mesmo cliente MCP, cada uma com seu próprio servidor
- **🔄 Conversão Automática**: Swagger2.0 desatualizado? Convertido automaticamente para OpenAPI 3.0
- **🌐 Três Transportes**: Suporte completo a STDIO, HTTP e SSE para diferentes cenários

## 🚀 Canais de Transporte (STDIO, HTTP, SSE)

O rest2mcp suporta três modos de transporte, cada um ideal para diferentes cenários:

| Transporte | Uso Principal                              | Ciclo de Vida                    | Inspector (`--inspect`)               |
| ---------- | ------------------------------------------ | -------------------------------- | ------------------------------------- |
| **STDIO**  | Produção com cliente MCP (VS Code, Claude) | Cliente spawna/killa processo    | Inspector spawna processo diretamente |
| **HTTP**   | Servidor independente / Host remoto        | Contínuo (até parar manualmente) | Servidor HTTP + Inspector no browser  |
| **SSE**    | Server-Sent Events / Tempo real            | Contínuo (até parar manualmente) | Servidor SSE + Inspector no browser   |

### STDIO (Padrão - Mais Comum)

Ideal para integração direta com clientes MCP locais:

```bash
# Sem inspect (produção - cliente MCP spawna)
python main.py

# Com inspect (desenvolvimento - Inspector spawna diretamente)
python main.py --inspect --transport stdio
```

### HTTP (Servidor Independente)

Ideal quando o servidor precisa rodar de forma contínua:

```bash
# Sem inspect (produção - servidor contínuo)
python main.py --transport http --port 8081

# Com inspect (desenvolvimento - servidor + Inspector)
python main.py --inspect --transport http --port 8081
```

### SSE (Server-Sent Events)

Ideal para comunicação em tempo real via SSE:

```bash
# Sem inspect (produção - servidor contínuo)
python main.py --transport sse --port 8081

# Com inspect (desenvolvimento - servidor + Inspector)
python main.py --inspect --transport sse --port 8081
```

---

## ⚠️ IMPORTANTE: Entenda o Fluxo

### Transporte stdio (padrão - mais comum)

O servidor é **passivo** e fica subordinado ao ciclo de vida do cliente:

- **O cliente MCP** (VS Code, Claude Desktop, Cursor) **spawna o servidor** como processo filho quando necessário
- **O servidor processa a requisição** e **morre** quando o cliente desconecta
- **Você não precisa rodar `python main.py` manualmente** em produção

```
┌─────────────────┐     spawna     ┌──────────────────┐
│   Cliente MCP   │ ──────────────► │  Seu Servidor    │
│  (VS Code/etc)  │   (stdio)      │  (main.py)       │
│                 │                 │                  │
│                 │ ◄────────────── │  • Lê env vars   │
│                 │   responde e    │  • Carrega spec  │
│                 │   morre         │  • Converte v2→v3│
└─────────────────┘                 │  • Responde MCP  │
                                   └──────────────────┘
```

### Transporte SSE/HTTP

O servidor roda de forma **independente**:

- O servidor pode rodar continuamente em um host remoto ou local
- O cliente conecta via HTTP/SSE sem controlar o ciclo de vida
- Você precisa iniciar o servidor manualmente antes do cliente conectar

---

## Sumário

- [Visão Geral](#visão-geral)
- [Requisitos](#requisitos)
- [Instalação](#instalação)
- [Fluxo de Produção vs Desenvolvimento](#fluxo-de-produção-vs-desenvolvimento)
- [Configuração no Cliente MCP](#configuração-no-cliente-mcp)
  - [VS Code / OpenCode](#vs-code--opencode)
  - [Claude Desktop](#claude-desktop)
  - [Cursor](#cursor)
- [Modo Desenvolvimento (Inspector)](#modo-desenvolvimento-inspector)
- [Variáveis de Ambiente](#variáveis-de-ambiente)
- [Conversão de OpenAPI](#conversão-de-openapi)
- [Estrutura do Projeto](#estrutura-do-projeto)
- [Solução de Problemas](#solução-de-problemas)

---

## Visão Geral

O rest2mcp é uma solução que permite expor qualquer API REST (documentada com OpenAPI/Swagger) como um servidor MCP. Isso significa que qualquer LLM compatível com MCP pode:

- Listar as tools/endpoints disponíveis
- Chamar endpoints da API como tools MCP
- Receber resultados formatados para o contexto do LLM

### Recursos Principais

- **Suporte universal**: Aceita OpenAPI 3.0+ nativamente
- **Conversão automática**: Converte Swagger 2.0 para OpenAPI 3.0 automaticamente
- **Modo desenvolvimento**: Inspector integrado para testes
- **Logging colorido**: Logs informativos no terminal
- **Zero configuração no código**: Toda configuração via variáveis de ambiente

---

## Requisitos

### Sistema

- Python 3.10+
- Node.js 18+ (apenas para modo Inspector e conversão de specs)
- npm/npx (instalado com Node.js)

### Python Packages

```bash
pip install fastmcp httpx
```

### Node.js Packages (opcional, para conversão e Inspector)

```bash
npm install -g swagger2openapi
```

---

## Instalação

### 1. Clone ou crie o projeto

```bash
mkdir mcp-server-universal
cd mcp-server-universal
```

### 2. Crie o ambiente virtual

```bash
# Windows
python -m venv venv
.\venv\Scripts\activate

# Linux/Mac
python -m venv venv
source venv/bin/activate
```

### 3. Instale as dependências

```bash
pip install fastmcp httpx
```

### 4. Salve o código principal

Salve o arquivo `main.py` na raiz do projeto.

### ✅ Pronto! Não precisa rodar nada.

O servidor será ativado automaticamente pelo cliente MCP quando necessário.

---

## Configurando Múltiplas APIs

Uma das maiores vantagens do rest2mcp é poder configurar **várias APIs diferentes** no mesmo cliente MCP. Cada API é um servidor independente que aponta para uma especificação diferente.

### Exemplo: PetStore API (Externa) vs Loja API (Local)

|                 | PetStore API                   | Loja API (Local)         |
| --------------- | ------------------------------ | ------------------------ |
| **Origem**      | Externa (swagger.io)           | Local (localhost:8000)   |
| **Versão Spec** | Swagger 2.0 (desatualizado)    | OpenAPI 3.0 (atualizado) |
| **Conversão**   | Automática via swagger2openapi | Nativa (sem conversão)   |
| **Velocidade**  | Mais lenta (precisa converter) | Rápida (usa diretamente) |

### Configuração no VS Code (Múltiplas APIs)

```json
{
  "mcp.servers": {
    "petstore": {
      "command": "/caminho/para/venv/Scripts/python.exe",
      "args": ["/caminho/para/main.py"],
      "env": {
        "MCP_SPEC_URL": "https://petstore.swagger.io/v2/swagger.json",
        "MCP_SERVER_NAME": "PetStore API (Swagger 2.0)"
      }
    },
    "loja-local": {
      "command": "/caminho/para/venv/Scripts/python.exe",
      "args": ["/caminho/para/main.py"],
      "env": {
        "MCP_SPEC_URL": "http://localhost:8000/openapi.json",
        "MCP_SERVER_NAME": "Loja API (OpenAPI 3.0)"
      }
    }
  }
}
```

> **Resultado**: O LLM terá acesso às tools de **ambas as APIs simultaneamente**, podendo listar pets da PetStore e produtos da Loja API no mesmo contexto.

---

## Scripts de Instalação

O projeto inclui scripts de instalação para diferentes sistemas operativos:

### Makefile (Cross-platform)

Ficheiro: `Makefile`

Fornece comandos rápidos para instalar dependências:

```bash
make install          # Instala tudo (Python + Node.js)
make install-python   # Apenas dependências Python
make install-node     # Apenas dependências Node.js
make clean            # Remove venv e ficheiros temporários
make inspect          # Lança o MCP Inspector (requer MCP_SPEC_URL)
```

> **Nota**: No Windows, o Makefile funciona via Git Bash, WSL ou Cygwin.

### setup.sh (Linux / macOS)

Ficheiro: `setup.sh`

Script Bash para sistemas Unix:

```bash
chmod +x setup.sh
./setup.sh
```

O script:

1. Cria o ambiente virtual Python (`venv`)
2. Instala os pacotes `fastmcp`, `httpx` e `pydantic>=2.10`
3. Instala o `swagger2openapi` globalmente via npm

### setup.ps1 (Windows / PowerShell)

Ficheiro: `setup.ps1`

Script PowerShell para Windows:

```powershell
.\setup.ps1
```

O script:

1. Cria o ambiente virtual Python (`venv`)
2. Instala os pacotes `fastmcp`, `httpx` e `pydantic>=2.10`
3. Instala o `swagger2openapi` globalmente via npm

---

## Fluxo de Produção vs Desenvolvimento

### 🟢 Produção (Uso Real)

**STDIO (Padrão - Cliente spawna)**

O servidor é ativado automaticamente pelo cliente MCP:

```
Você: Configura o settings.json do VS Code
  │
  ▼
VS Code: "Preciso de tools da API"
  │
  ▼
VS Code: Spawna python main.py --transport stdio (com env vars)
  │
  ▼
Servidor: Carrega spec, converte se necessário, responde
  │
  ▼
VS Code: Recebe tools, mostra para o LLM usar
  │
  ▼
[Quando desconectar, o servidor morre automaticamente]
```

**HTTP/SSE (Servidor Independente)**

O servidor roda continuamente, você inicia manualmente:

```bash
# Terminal: iniciar servidor (HTTP)
$env:MCP_SPEC_URL = "https://petstore.swagger.io/v2/swagger.json"
$env:MCP_SERVER_NAME = "PetStore API"
python main.py --transport http --port 8081

# Ou para SSE:
python main.py --transport sse --port 8081
```

O cliente MCP conecta no servidor via HTTP/SSE em `http://localhost:8081`.

### 🔵 Desenvolvimento (Testes)

**Você RODA manualmente** para testar e inspecionar as tools com `--inspect`.

#### STDIO + Inspector

```powershell
$env:MCP_SPEC_URL = "https://petstore.swagger.io/v2/swagger.json"
$env:MCP_SERVER_NAME = "PetStore API"
python main.py --inspect --transport stdio
```

#### HTTP + Inspector

```powershell
$env:MCP_SPEC_URL = "https://petstore.swagger.io/v2/swagger.json"
$env:MCP_SERVER_NAME = "PetStore API"
python main.py --inspect --transport http --port 8081
```

#### SSE + Inspector

```powershell
$env:MCP_SPEC_URL = "https://petstore.swagger.io/v2/swagger.json"
$env:MCP_SERVER_NAME = "PetStore API"
python main.py --inspect --transport sse --port 8081
```

> O Inspector abrirá em `http://localhost:6274` em todos os casos.

### Comparação: Produção vs Desenvolvimento

|                | Produção STDIO       | Produção HTTP/SSE                        | Desenvolvimento (Inspector)                               |
| -------------- | -------------------- | ---------------------------------------- | --------------------------------------------------------- |
| **Quem ativa** | Cliente MCP (auto)   | Você (manual)                            | Você (manual)                                             |
| **Comando**    | Nenhum (cliente faz) | `python main.py --transport [http\|sse]` | `python main.py --inspect --transport [stdio\|http\|sse]` |
| **Propósito**  | LLM usar a API       | LLM usar a API                           | Você ver/debugar as tools                                 |
| **Duração**    | Vivo durante uso     | Contínuo até parar                       | Vivo até fechar o Inspector                               |

---

## Configuração no Cliente MCP

### VS Code / OpenCode

Edite o arquivo `settings.json`:

**Windows:**

```
%APPDATA%\Code\User\settings.json
```

**Mac:**

```
~/Library/Application Support/Code/User/settings.json
```

**Linux:**

```
~/.config/Code/User/settings.json
```

#### Configuração mínima (produção)

```json
{
  "mcp.servers": {
    "petstore-api": {
      "command": "/caminho/para/venv/Scripts/python.exe",
      "args": ["/caminho/para/main.py"],
      "env": {
        "MCP_SPEC_URL": "https://petstore.swagger.io/v2/swagger.json",
        "MCP_SERVER_NAME": "PetStore API"
      }
    }
  }
}
```

> **Nota**: O VS Code vai spawnar `python main.py` automaticamente quando o LLM precisar das tools. Você não precisa rodar nada manualmente.

#### Configuração com caminho relativo (workspace)

```json
{
  "mcp.servers": {
    "petstore-api": {
      "command": "${workspaceFolder}/venv/Scripts/python.exe",
      "args": ["${workspaceFolder}/main.py"],
      "env": {
        "MCP_SPEC_URL": "https://petstore.swagger.io/v2/swagger.json",
        "MCP_SERVER_NAME": "PetStore API"
      }
    }
  }
}
```

#### Configuração HTTP/SSE (Servidor Independente)

Para usar HTTP ou SSE, inicie o servidor manualmente e configure o cliente para conectar:

**Terminal: Iniciar servidor HTTP**

```bash
$env:MCP_SPEC_URL = "https://petstore.swagger.io/v2/swagger.json"
$env:MCP_SERVER_NAME = "PetStore API"
python main.py --transport http --port 8081
```

**VS Code settings.json (HTTP)**

```json
{
  "mcp.servers": {
    "petstore-http": {
      "url": "http://localhost:8081"
    }
  }
}
```

**VS Code settings.json (SSE)**

```json
{
  "mcp.servers": {
    "petstore-sse": {
      "url": "http://localhost:8081"
    }
  }
}
```

> **Nota**: Para HTTP/SSE, o servidor deve estar rodando antes do cliente conectar.

### Claude Desktop

Edite o arquivo de configuração:

**Windows:**

```
%APPDATA%\Claude\claude_desktop_config.json
```

**Mac:**

```
~/Library/Application Support/Claude/claude_desktop_config.json
```

```json
{
  "mcpServers": {
    "petstore-api": {
      "command": "/caminho/para/venv/Scripts/python.exe",
      "args": ["/caminho/para/main.py"],
      "env": {
        "MCP_SPEC_URL": "https://petstore.swagger.io/v2/swagger.json",
        "MCP_SERVER_NAME": "PetStore API"
      }
    }
  }
}
```

### Claude Desktop

Edite o arquivo de configuração:

**Windows:**

```
%APPDATA%\Claude\claude_desktop_config.json
```

**Mac:**

```
~/Library/Application Support/Claude/claude_desktop_config.json
```

```json
{
  "mcpServers": {
    "petstore-api": {
      "command": "C:\\Users\\matias.fernando\\Documents\\case\\venv\\Scripts\\python.exe",
      "args": ["C:\\Users\\matias.fernando\\Documents\\case\\main.py"],
      "env": {
        "MCP_SPEC_URL": "https://petstore.swagger.io/v2/swagger.json",
        "MCP_SERVER_NAME": "PetStore API"
      }
    }
  }
}
```

> **Nota**: O Claude Desktop vai spawnar o servidor quando o usuário fizer uma pergunta que precise da API. O servidor morre após responder.

#### Claude Desktop HTTP/SSE (Servidor Independente)

Para HTTP/SSE, inicie o servidor manualmente:

**Terminal: Iniciar servidor HTTP**

```bash
$env:MCP_SPEC_URL = "https://petstore.swagger.io/v2/swagger.json"
$env:MCP_SERVER_NAME = "PetStore API"
python main.py --transport http --port 8081
```

**Claude config (HTTP)**

```json
{
  "mcpServers": {
    "petstore-http": {
      "url": "http://localhost:8081"
    }
  }
}
```

**Claude config (SSE)**

```json
{
  "mcpServers": {
    "petstore-sse": {
      "url": "http://localhost:8081"
    }
  }
}
```

> **Nota**: Para HTTP/SSE, o servidor deve estar rodando antes do Claude Desktop conectar.

### Cursor

Edite o arquivo `~/.cursor/mcp.json`:

```json
{
  "mcpServers": {
    "petstore-api": {
      "command": "python",
      "args": ["/caminho/para/main.py"],
      "env": {
        "MCP_SPEC_URL": "https://petstore.swagger.io/v2/swagger.json",
        "MCP_SERVER_NAME": "PetStore API"
      }
    }
  }
}
```

---

## Modo Desenvolvimento (Inspector)

Use o modo Inspector para **testar e visualizar** as tools antes de configurar no cliente MCP.

### Quando usar

- Quer ver quais tools foram geradas da sua API
- Quer testar uma chamada manualmente
- Quer debugar problemas na spec
- Está desenvolvendo uma nova API e quer ver como fica no MCP

### Como usar com `--inspect`

O flag `--inspect` lança o MCP Inspector integrado, permitindo testar as ferramentas no browser.

#### STDIO (Inspector spawna processo diretamente)

No modo STDIO com `--inspect`, o Inspector gerencia o servidor:

```powershell
$env:MCP_SPEC_URL = "https://petstore.swagger.io/v2/swagger.json"
$env:MCP_SERVER_NAME = "PetStore API"
python main.py --inspect --transport stdio
```

#### HTTP (Servidor HTTP + Inspector)

No modo HTTP com `--inspect`, o servidor roda continuamente e o Inspector conecta via HTTP:

```powershell
$env:MCP_SPEC_URL = "https://petstore.swagger.io/v2/swagger.json"
$env:MCP_SERVER_NAME = "PetStore API"
python main.py --inspect --transport http --port 8081
```

#### SSE (Servidor SSE + Inspector)

No modo SSE com `--inspect`, o servidor roda continuamente e o Inspector conecta via Server-Sent Events:

```powershell
$env:MCP_SPEC_URL = "https://petstore.swagger.io/v2/swagger.json"
$env:MCP_SERVER_NAME = "PetStore API"
python main.py --inspect --transport sse --port 8081
```

> **Nota**: O Inspector abrirá automaticamente no navegador em `http://localhost:6274`.

### Como usar sem `--inspect` (Produção)

Sem o flag `--inspect`, o servidor roda em modo produção:

#### STDIO (Padrão - Cliente spawna)

```powershell
$env:MCP_SPEC_URL = "https://petstore.swagger.io/v2/swagger.json"
$env:MCP_SERVER_NAME = "PetStore API"
python main.py --transport stdio
```

> O cliente MCP (VS Code, Claude) spawna o processo automaticamente.

#### HTTP (Servidor Independente)

```powershell
$env:MCP_SPEC_URL = "https://petstore.swagger.io/v2/swagger.json"
$env:MCP_SERVER_NAME = "PetStore API"
python main.py --transport http --port 8081
```

> O servidor roda continuamente. Configure o cliente para conectar em `http://localhost:8081`.

#### SSE (Servidor Independente)

```powershell
$env:MCP_SPEC_URL = "https://petstore.swagger.io/v2/swagger.json"
$env:MCP_SERVER_NAME = "PetStore API"
python main.py --transport sse --port 8081
```

> O servidor roda continuamente. Configure o cliente para conectar via SSE em `http://localhost:8081`.

### Exemplos Práticos

#### Com PetStore API (Swagger 2.0)

```powershell
# Terminal: configurar e rodar Inspector
$env:MCP_SPEC_URL = "https://petstore.swagger.io/v2/swagger.json"
$env:MCP_SERVER_NAME = "PetStore API"
python main.py --inspect
```

#### Com API Local (OpenAPI 3.0)

```bash
# Terminal 1: rodar sua API local
uvicorn main:app --reload --port 8000

# Terminal 2: rodar Inspector
$env:MCP_SPEC_URL = "http://localhost:8000/openapi.json"
$env:MCP_SERVER_NAME = "Minha API"
python main.py --inspect
```

---

## Variáveis de Ambiente

### Quem define as variáveis?

| Cenário                         | Quem define             | Quando                   |
| ------------------------------- | ----------------------- | ------------------------ |
| **Produção (Cliente MCP)**      | Você no `settings.json` | Uma vez, na configuração |
| **Desenvolvimento (Inspector)** | Você no terminal        | Toda vez que testar      |

### Variáveis Obrigatórias

| Variável       | Descrição                            | Exemplo                                       |
| -------------- | ------------------------------------ | --------------------------------------------- |
| `MCP_SPEC_URL` | URL da especificação OpenAPI/Swagger | `https://petstore.swagger.io/v2/swagger.json` |

### Variáveis Opcionais

| Variável          | Descrição                | Padrão          |
| ----------------- | ------------------------ | --------------- |
| `MCP_SERVER_NAME` | Nome exibido do servidor | `Universal API` |

### Por que variáveis de ambiente?

- **Desacoplamento**: O código não precisa ser editado para mudar de API
- **Segurança**: URLs e configs não ficam hardcoded
- **Flexibilidade**: Mesmo código roda com diferentes APIs
- **Padrão MCP**: Clientes MCP esperam configurar servidores via ambiente

---

## Conversão de OpenAPI

### Suporte a versões

| Versão da Spec | Suporte      | Ação                                           |
| -------------- | ------------ | ---------------------------------------------- |
| OpenAPI 3.0+   | ✅ Nativo    | Usa diretamente                                |
| OpenAPI 3.1    | ✅ Nativo    | Usa diretamente                                |
| Swagger 2.0    | ⚠️ Conversão | Converte automaticamente via `swagger2openapi` |

### Como funciona a conversão

1. O servidor detecta `"swagger": "2.0"` na spec
2. Salva a spec temporariamente em `_temp_swagger2.json`
3. Executa `npx swagger2openapi _temp_swagger2.json -o _temp_openapi3.json`
4. Carrega a spec convertida
5. Remove os arquivos temporários

### Pré-requisitos para conversão

```bash
npm install -g swagger2openapi
```

Ou deixe o `npx` instalar automaticamente (mais lento na primeira vez).

---

## Estrutura do Projeto

```
mcp-server-universal/
├── main.py              # Código principal do servidor
├── Makefile             # Comandos de instalação (cross-platform)
├── setup.sh             # Script de instalação (Linux/macOS)
├── setup.ps1            # Script de instalação (Windows PowerShell)
├── venv/                # Ambiente virtual Python
└── README.md            # Esta documentação
```

### Código Principal (main.py)

O arquivo `main.py` contém:

- **Logging colorido**: Saída formatada no stderr
- **Conversão automática**: Swagger 2.0 → OpenAPI 3.0
- **Detecção de versão**: Identifica OpenAPI vs Swagger
- **Modo dual**: Servidor direto ou Inspector

---

## API de Teste Local (loja_api.py)

Ficheiro: `loja_api.py`

Uma API FastAPI de demonstração que simula uma loja virtual, ideal para testar o MCP Server localmente sem depender de APIs externas.

### Recursos da API

| Endpoint                | Método | Descrição                               |
| ----------------------- | ------ | --------------------------------------- |
| `/`                     | GET    | Página inicial                          |
| `/api/v1/produtos`      | GET    | Listar produtos (com filtros opcionais) |
| `/api/v1/produtos/{id}` | GET    | Buscar produto por ID                   |
| `/api/v1/produtos`      | POST   | Criar novo produto                      |
| `/api/v1/produtos/{id}` | PUT    | Atualizar produto                       |
| `/api/v1/produtos/{id}` | DELETE | Deletar produto                         |
| `/api/v1/categorias`    | GET    | Listar categorias                       |

### Especificação OpenAPI

A API expõe automaticamente sua especificação OpenAPI 3.0 em:

- **JSON**: `http://localhost:8000/openapi.json`
- **Swagger UI**: `http://localhost:8000/docs`
- **ReDoc**: `http://localhost:8000/redoc`

### Como executar

```bash
# Terminal 1: Iniciar a API local
./venv/Scripts/python loja_api.py

# A API estará disponível em http://localhost:8000
```

### Como testar com o MCP Server

```bash
# Terminal 2: Configurar variáveis para o Inspector
$env:MCP_SPEC_URL = "http://localhost:8000/openapi.json"
$env:MCP_SERVER_NAME = "Loja API"

# Iniciar o MCP Inspector
./venv/Scripts/python main.py --inspect
```

O Inspector abrirá em `http://localhost:6274` onde poderá ver e testar as tools geradas automaticamente a partir da Loja API.

### Dados Mock

A API vem pré-carregada com 4 produtos:

1. Notebook Dell (Eletrônicos) - R$ 4500,00
2. Mouse Logitech (Periféricos) - R$ 150,00
3. Teclado Mecânico (Periféricos) - R$ 350,00 (sem estoque)
4. Monitor 27" (Eletrônicos) - R$ 1200,00

---

## Solução de Problemas

### Erro: `ImportError: cannot import name 'ImportString' from 'pydantic'`

**Causa**: Pydantic v1 instalado, mas FastMCP requer v2+

**Solução**:

```bash
pip install --upgrade "pydantic>=2.10"
```

### Erro: `MCP_SPEC_URL nao configurada no ambiente`

**Causa**: Variável de ambiente não definida

**Solução**:

```powershell
# No terminal (modo Inspector)
$env:MCP_SPEC_URL = "https://sua-api.com/openapi.json"

# Ou no settings.json (modo Produção)
"env": { "MCP_SPEC_URL": "https://sua-api.com/openapi.json" }
```

### Erro: `Conversao falhou` (swagger2openapi)

**Causa**: Node.js/npm não instalado ou `swagger2openapi` não disponível

**Solução**:

```bash
npm install -g swagger2openapi
```

### Servidor não aparece no VS Code

**Causa**: Configuração incorreta no `settings.json`

**Solução**:

1. Verifique o caminho do Python (deve ser do venv)
2. Verifique se `main.py` existe no caminho correto
3. Reinicie o VS Code após alterar o `settings.json`
4. Verifique o Output Panel → "MCP" para logs

### Inspector não abre no browser

**Causa**: Problema com `@hono/node-server` em algumas versões do Node.js

**Solução**:

```bash
# Atualize o Inspector
npx @modelcontextprotocol/inspector@latest
```

---

## Checklist de Instalação

Use esta lista para verificar se tudo está configurado:

### ✅ Instalação

- [ ] Python 3.10+ instalado
- [ ] Node.js 18+ instalado
- [ ] Ambiente virtual criado (`python -m venv venv`)
- [ ] Dependências instaladas (`pip install fastmcp httpx`)
- [ ] `swagger2openapi` instalado (`npm install -g swagger2openapi`)
- [ ] Arquivo `main.py` salvo no projeto

### ✅ Configuração de Produção

- [ ] `settings.json` do cliente MCP editado
- [ ] Caminho do Python aponta para o venv
- [ ] Caminho do `main.py` está correto
- [ ] `MCP_SPEC_URL` configurada no `env`
- [ ] `MCP_SERVER_NAME` configurada (opcional)
- [ ] Cliente MCP reiniciado

### ✅ Teste de Desenvolvimento

- [ ] Variáveis setadas no terminal
- [ ] `python main.py --inspect` roda sem erro
- [ ] Inspector abre no browser
- [ ] Tools aparecem no Inspector
- [ ] Chamada de teste funciona

---

## Arquitetura

### Fluxo de Produção - Transporte STDIO (Padrão)

No transporte STDIO, o servidor é um processo filho do cliente:

```
┌─────────────────┐
│   Usuário       │ "Quero listar pets disponíveis"
└────────┬────────┘
           │
┌────────▼────────┐
│   LLM/Agente    │ Precisa da tool "list_pets"
└────────┬────────┘
           │
┌────────▼────────┐     spawna     ┌──────────────────┐
│   Cliente MCP   │ ──────────────► │  python main.py  │
│  (VS Code/etc)  │  (com env vars) │                  │
│                 │                 │  • Lê MCP_SPEC_URL│
│                 │ ◄────────────── │  • Baixa spec     │
│                 │   lista tools   │  • Converte v2→v3 │
│                 │                 │  • Retorna tools  │
│                 │ ──────────────► │                  │
│                 │  chama tool     │  • Executa endpoint│
│                 │                 │  • Retorna resultado│
│                 │ ◄────────────── │                  │
│                 │   resultado     │  [processo morre] │
└─────────────────┘                 └──────────────────┘
```

**Comando**: `python main.py --transport stdio` (ou omitir `--transport`, padrão é STDIO)

### Fluxo de Produção - Transporte HTTP

No transporte HTTP, o servidor roda de forma independente:

```
┌─────────────────┐
│   Usuário       │ "Quero listar pets disponíveis"
└────────┬────────┘
           │
┌────────▼────────┐
│   LLM/Agente    │ Precisa da tool "list_pets"
└────────┬────────┘
           │
┌────────▼────────┐                ┌──────────────────┐
│   Cliente MCP   │ ── conecta ──► │  Servidor MCP    │
│  (VS Code/etc)  │    via HTTP    │  (rodando em     │
│                 │    :8081       │   host:port)     │
│                 │ ◄───────────── │                  │
│                 │   lista tools  │  • Responde via   │
│                 │                │    HTTP           │
│                 │ ─────────────► │                  │
│                 │  chama tool    │  • Executa endpoint│
│                 │                │  • Retorna via HTTP│
│                 │ ◄───────────── │                  │
│                 │   resultado    │  [contínuo]      │
└─────────────────┘                 └──────────────────┘
```

**Comando**: `python main.py --transport http --port 8081`

### Fluxo de Produção - Transporte SSE

No transporte SSE (Server-Sent Events), o servidor envia eventos em tempo real:

```
┌─────────────────┐
│   Usuário       │ "Quero listar pets disponíveis"
└────────┬────────┘
           │
┌────────▼────────┐
│   LLM/Agente    │ Precisa da tool "list_pets"
└────────┬────────┘
           │
┌────────▼────────┐                ┌──────────────────┐
│   Cliente MCP   │ ── conecta ──► │  Servidor MCP    │
│  (VS Code/etc)  │    via SSE     │  (rodando em     │
│                 │    :8081        │   host:port)     │
│                 │ ◄───────────── │                  │
│                 │   lista tools  │  • Responde via   │
│                 │                │    Server-Sent     │
│                 │ ─────────────► │    Events (SSE)   │
│                 │  chama tool    │                  │
│                 │                │  • Executa endpoint│
│                 │ ◄───────────── │  • Retorna via SSE│
│                 │   resultado    │  [contínuo]      │
└─────────────────┘                 └──────────────────┘
```

**Comando**: `python main.py --transport sse --port 8081`

### Fluxo de Desenvolvimento (Inspector)

```
┌─────────────────┐
│   Você          │ $env:MCP_SPEC_URL = "..."
└────────┬────────┘         python main.py --inspect
           │
┌────────▼────────┐
│   Inspector     │ Abre browser em localhost:6274
│                 │
│  ┌───────────┐  │
│  │  Browser  │  │ Você clica em "List Tools"
│  └─────┬─────┘  │
│        │        │
│  ┌─────▼─────┐  │ Inspector spawna python main.py
│  │   Tools   │  │ (sem --inspect, modo servidor)
│  └───────────┘  │
└─────────────────┘
```

**Com --inspect**: `python main.py --inspect --transport [stdio|http|sse] [--port 8081]`

---

## Recursos Adicionais

- [Documentação FastMCP](https://gofastmcp.com)
- [Protocolo MCP](https://modelcontextprotocol.io)
- [OpenAPI Specification](https://swagger.io/specification/)
- [swagger2openapi](https://github.com/Mermade/oas-kit)

---

**Autor**: Matias Fernando  
**Versão**: 1.0.0  
**Data**: 2026-05-05
