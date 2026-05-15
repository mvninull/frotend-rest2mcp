# Protocolo de Sincronização: Identidade, Pagamento e Status

Este documento descreve a lógica de negócio para autenticar utilizadores via Supabase,
vincular subscrições PayPal, e controlar privilégios (servidores MCP ativos/inativos)
com base no status de pagamento.

---

## 1. Arquitetura Geral

O sistema tem dois bancos de dados:

| Banco | Função | Tecnologia |
|---|---|---|
| **Supabase (PostgreSQL)** | `auth.users` + `profiles` (status, plano, assinatura PayPal) | Gerenciado |
| **Local (SQLite)** | `servers` + `logs` de cada servidor MCP | Ficheiro local |

A coluna `user_id` na tabela `servers` (SQLite) vincula cada servidor ao seu dono no Supabase.

---

## 2. Fluxo de Autenticação

### 2.1. Registo / Login (Frontend)

O utilizador faz login via **Supabase Auth** (email + password ou OAuth).
O Supabase devolve um **JWT** que o frontend armazena e envia em cada requisição.

### 2.2. Criação automática de `profiles`

No primeiro login, um trigger no Supabase (ou uma rota `POST /v1/auth/register` no backend)
cria o registo na tabela `profiles`:

```sql
-- Tabela profiles no Supabase
create table profiles (
  id          uuid references auth.users not null primary key,
  email       text,
  status      text check (status in ('active', 'suspended', 'banned')) default 'active',
  plan_tier   text check (plan_tier in ('free', 'pro')) default 'free',
  paypal_subscription_id text,
  created_at  timestamp default now(),
  updated_at  timestamp default now()
);
```

### 2.3. Middleware JWT (FastAPI)

Todas as rotas da **Management API** (`/v1/servers/*`) e do **Dashboard** exigem
`Authorization: Bearer <token>`.

O middleware:
1. Valida o JWT contra a chave pública do Supabase (`JWKS endpoint`)
2. Extrai o `user_id`
3. Injeta o `user_id` na requisição (via `request.state.user_id`)

```python
# Pseudocódigo do middleware
async def auth_middleware(request: Request, call_next):
    if request.url.path.startswith(("/v1/servers", "/v1/webhooks", "/health")):
        token = request.headers.get("Authorization", "").replace("Bearer ", "")
        try:
            payload = await supabase_client.auth.get_user(token)
            request.state.user_id = payload.user.id
        except:
            return JSONResponse(status_code=401, content={"detail": "Token inválido"})
    return await call_next(request)
```

### 2.4. Rotas que NÃO usam JWT

As rotas **MCP Proxy** (`/v1/{server_id}/{apikey}/sse`, `/messages`, `/mcp`)
são consumidas por clientes MCP (Claude, Cursor, etc.) e mantêm a autenticação
por **apikey na URL**. Nestas rotas, a verificação de acesso é:

```
apikey válida → servidor is_active = true → dono do servidor status = 'active'
```

---

## 3. O Elo de Ligação: `custom_id`

A sincronização entre Supabase e PayPal ocorre via `custom_id`.

### No Frontend

Ao criar a subscrição no botão do PayPal, o `user_id` do Supabase **DEVE** ser
enviado no campo `custom_id`:

```javascript
// Frontend — criação da subscrição PayPal
paypal.Buttons({
    createSubscription: function(data, actions) {
        return actions.subscription.create({
            'plan_id': 'P-XXXXXXXXXXXXXXXX',
            'custom_id': supabaseUserId  // ← user_id do Supabase
        });
    },
    onApprove: function(data, actions) {
        // data.subscriptionID contém o ID da subscrição PayPal
        // Notificar o backend para vincular
    }
});
```

### No PayPal Webhook

O `custom_id` é devolvido em cada evento como `resource.custom_id`,
permitindo identificar qual utilizador deve ser atualizado.

---

## 4. Gestão de Perfil (Supabase `profiles`)

Cada utilizador tem um perfil que funciona como "Painel de Controlo":

| Campo | Valores | Descrição |
|---|---|---|
| `status` | `active`, `suspended`, `banned` | Se o utilizador pode usar o serviço |
| `plan_tier` | `free`, `pro` | Plano de subscrição |
| `paypal_subscription_id` | string \| null | ID da subscrição PayPal ativa |

---

## 5. Sincronização de Pagamentos (Webhooks PayPal)

O backend expõe `POST /v1/webhooks/paypal` para receber eventos de subscrição.
**TODOS os webhooks devem ser verificados** (assinatura PayPal) antes de processar.

### Verificação do Webhook

```python
# Pseudocódigo — verificar assinatura PayPal
async def verify_paypal_webhook(headers, body):
    # Validar headers:
    #   PAYPAL-AUTH-ALGO, PAYPAL-CERT-URL,
    #   PAYPAL-TRANSMIT-ID, PAYPAL-TRANSMIT-SIG
    # Chamar API PayPal: POST /v1/notifications/verify-webhook-signature
    return verified  # bool
```

### Mapeamento de Eventos

| Evento PayPal | Ação no Supabase (`profiles`) | Efeito no Gateway |
|---|---|---|
| `BILLING.SUBSCRIPTION.ACTIVATED` | `plan_tier = 'pro'`, `status = 'active'`, guardar `paypal_subscription_id` | Liberta criação de servidores ilimitados |
| `BILLING.SUBSCRIPTION.PAYMENT.FAILED` | `status = 'suspended'` | Bloqueia TODOS os servidores do utilizador (is_active = false) |
| `BILLING.SUBSCRIPTION.CANCELLED` | `plan_tier = 'free'`, limpar `paypal_subscription_id` | Desativa servidores que excedam o limite free |
| `BILLING.SUBSCRIPTION.RE-ACTIVATED` | `status = 'active'` | Reativa todos os servidores (is_active = true) |

### Comportamento pós-evento

```python
# Após atualizar o profile no Supabase, sincronizar com SQLite local
async def sync_user_servers(user_id: str):
    profile = await get_supabase_profile(user_id)
    db = SessionLocal()
    servers = db.query(ServerDB).filter(ServerDB.user_id == user_id).all()
    for s in servers:
        if profile.status == 'suspended':
            s.is_active = False
        elif profile.status == 'active' and profile.plan_tier == 'free':
            # Manter apenas o primeiro servidor ativo
            pass
    db.commit()
    db.close()
    # Notificar sessions SSE ativas (ver secção 7)
    await notify_session_termination(user_id)
```

---

## 6. Gestão de Servidores (Ativar / Desativar)

### 6.1. Verificação em Cascata (MCP Proxy)

Cada requisição a uma rota MCP Proxy passa por esta verificação:

```
1. Utilizador está active?           ← consulta Supabase profiles (cached)
   ├── Não → 403 Forbidden
   └── Sim →
2. Plano é free?                      ← consulta Supabase profiles
   ├── Sim → servidor é um dos permitidos?
   │   ├── Não → 403 Forbidden
   │   └── Sim → OK
   └── Não (pro) → OK
3. Servidor is_active = true?         ← consulta SQLite local
   ├── Não → 403 Forbidden
   └── Sim → OK, processa requisição
```

### 6.2. Cache do Profile

Para não consultar o Supabase em cada chamada MCP (latência), o profile pode
ser cacheado em memória com TTL curto (ex.: 60 segundos):

```python
from functools import lru_cache
from datetime import datetime, timedelta

profile_cache: dict[str, tuple[dict, datetime]] = {}

async def get_cached_profile(user_id: str) -> dict:
    if user_id in profile_cache:
        data, expires = profile_cache[user_id]
        if datetime.now() < expires:
            return data
    profile = await fetch_supabase_profile(user_id)
    profile_cache[user_id] = (profile, datetime.now() + timedelta(seconds=60))
    return profile

def invalidate_profile_cache(user_id: str):
    profile_cache.pop(user_id, None)
```

### 6.3. Limites por Plano

| Plano | Máx. Servidores | Campos permitidos |
|---|---|---|
| `free` | 1 | Transporte SSE ou HTTP |
| `pro` | Ilimitado | Transporte SSE ou HTTP |

A validação acontece:
- **No create** (`POST /v1/servers`): se `plan_tier = free` e o utilizador já tem 1 servidor, retorna **402 Payment Required**
- **No sync** (pós-webhook): se o utilizador passou de `pro` para `free` e tem >1 servidor, os excedentes são marcados `is_active = false`

### 6.4. Lógica de Interrupção Imediata

Quando o utilizador desativa um servidor no Dashboard:

```python
# Frontend → PATCH /v1/servers/{server_id} { "is_active": false }
# Backend:
server.is_active = False
db.commit()
# Remover dos active_servers (força desconexão)
key = f"{server.server_id}:{server.apikey}"
if key in active_servers:
    await active_servers[key].stop()
    del active_servers[key]
```

No milissegundo seguinte, qualquer chamada MCP a esse servidor retorna **403 Forbidden**.

---

## 7. Gestão de Sessions SSE Ao Vivo

Conexões SSE são long-lived. Se o utilizador for suspenso, as sessions existentes
precisam ser terminadas.

### 7.1. Registo de Sessions

```python
# Mapa: user_id → lista de eventos de término
sse_sessions: dict[str, list[asyncio.Event]] = {}

def register_sse_session(user_id: str) -> asyncio.Event:
    exit_event = asyncio.Event()
    sse_sessions.setdefault(user_id, []).append(exit_event)
    return exit_event

def unregister_sse_session(user_id: str, event: asyncio.Event):
    if user_id in sse_sessions:
        sse_sessions[user_id] = [e for e in sse_sessions[user_id] if e is not event]
```

### 7.2. Terminação Remota

```python
async def notify_session_termination(user_id: str):
    events = sse_sessions.get(user_id, [])
    for event in events:
        event.set()  # Faz o event_stream() sair do loop
```

### 7.3. No `event_stream`

```python
async def event_stream(user_id: str):
    exit_event = register_sse_session(user_id)
    try:
        # ... loop normal de SSE ...
        # Adicionar verificação periódica:
        while True:
            line = await asyncio.wait_for(read_line(), timeout=30)
            if exit_event.is_set():
                yield "event: error\ndata: Sessão terminada\n\n"
                return
            yield line
    finally:
        unregister_sse_session(user_id, exit_event)
```

---

## 8. Resumo de Endpoints e Autenticação

| Rota | Método | Autenticação | Descrição |
|---|---|---|---|
| `/v1/servers` | GET | JWT | Listar servidores do utilizador |
| `/v1/servers` | POST | JWT | Criar servidor (valida limite free/pro) |
| `/v1/servers/{id}` | PATCH | JWT | Editar / ativar / desativar servidor |
| `/v1/servers/{id}` | DELETE | JWT | Remover servidor |
| `/v1/servers/{id}/logs` | GET | JWT | Logs do servidor |
| `/v1/servers/{id}/logs/export` | GET | JWT | Exportar logs |
| `/v1/servers/{id}/logs/{log_id}` | GET | JWT | Detalhe do log |
| `/v1/servers/{id}/logs` | DELETE | JWT | Limpar logs |
| `/v1/webhooks/paypal` | POST | Verificação PayPal | Webhook de subscrições |
| `/health` | GET | Nenhuma | Health check |

**Rotas MCP Proxy (apikey, sem JWT):**

| Rota | Método | Autenticação | Descrição |
|---|---|---|---|
| `/v1/{id}/{key}/sse` | GET (+ POST erro) | apikey | Conexão SSE |
| `/v1/{id}/{key}/messages` | POST | apikey | Enviar mensagens MCP |
| `/v1/{id}/{key}/mcp` | GET/POST | apikey | Streamable HTTP + init |

---

## 9. Variáveis de Ambiente

```
# Supabase (obrigatório)
SUPABASE_URL=https://xxxxx.supabase.co
SUPABASE_ANON_KEY=eyJ...
SUPABASE_SERVICE_KEY=eyJ...  # chave service_role (para webhooks)

# PayPal (obrigatório)
PAYPAL_CLIENT_ID=Af...
PAYPAL_CLIENT_SECRET=EH...
PAYPAL_WEBHOOK_ID=WH-...    # para verificar assinatura dos webhooks

# Plano free
FREE_TIER_MAX_SERVERS=1
```

---

## 10. Checklist de Implementação

- [ ] Adicionar `user_id` à tabela `servers` no SQLite (migration automática)
- [ ] Criar tabela `profiles` no Supabase
- [ ] Implementar middleware JWT nas rotas Management API
- [ ] Filtrar servidores por `user_id` nas queries (cada user vê só os seus)
- [ ] Implementar `POST /v1/webhooks/paypal` com verificação de assinatura
- [ ] Mapear eventos PayPal → atualização de `profiles` no Supabase
- [ ] Sincronizar `profiles` do Supabase com `servers` no SQLite local
- [ ] Implementar cache de profiles (60s TTL)
- [ ] Verificação em cascata nas rotas MCP Proxy (user → plan → server)
- [ ] Limitar criação de servidores por plano (free = 1, pro = ∞)
- [ ] Registrar sessions SSE e terminar ao suspender utilizador
- [ ] Atualizar frontend: login Supabase, botão PayPal, mostrar plano
