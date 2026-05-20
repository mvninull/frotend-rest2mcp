from datetime import datetime, timedelta, timezone
from typing import List, Optional

import uvicorn
from fastapi import Depends, FastAPI, Form, HTTPException, Path, Query, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from pydantic import BaseModel, Field

app = FastAPI(
    title="Tarefas API",
    description="API simples de tarefas (todo list)",
    version="1.0.0",
    swagger_ui_parameters={"persistAuthorization": True},
)


def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema
    from fastapi.openapi.utils import get_openapi

    schema = get_openapi(
        title=app.title,
        version=app.version,
        openapi_version=app.openapi_version,
        description=app.description,
        routes=app.routes,
    )
    schema["components"]["securitySchemes"] = {
        "BearerAuth": {
            "type": "http",
            "scheme": "bearer",
            "bearerFormat": "JWT",
        }
    }
    for path in schema["paths"]:
        if path.startswith("/api/v1/auth"):
            continue
        for method in schema["paths"][path]:
            schema["paths"][path][method]["security"] = [{"BearerAuth": []}]
    app.openapi_schema = schema
    return schema


app.openapi = custom_openapi

# ========== AUTH ==========

SECRET_KEY = "super-secret-key-mude-em-producao"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
security = HTTPBearer()


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class User(BaseModel):
    username: str
    hashed_password: str
    nome: str


fake_users_db = [
    User(
        username="admin",
        hashed_password=pwd_context.hash("123456"),
        nome="Administrador",
    ),
]


def create_access_token(data: dict) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> User:
    token = credentials.credentials
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise HTTPException(status_code=401, detail="Token invalido")
    except JWTError:
        raise HTTPException(status_code=401, detail="Token invalido ou expirado")
    for user in fake_users_db:
        if user.username == username:
            return user
    raise HTTPException(status_code=401, detail="Usuario nao encontrado")


@app.post(
    "/api/v1/auth/login",
    response_model=TokenResponse,
    tags=["Autenticacao"],
    summary="Login",
)
def login(
    username: str = Form(...),
    password: str = Form(...),
):
    for user in fake_users_db:
        if user.username == username and pwd_context.verify(password, user.hashed_password):
            token = create_access_token({"sub": user.username})
            return TokenResponse(access_token=token)
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Usuario ou senha invalidos",
    )


@app.get(
    "/api/v1/auth/me",
    tags=["Autenticacao"],
    summary="Dados do usuario atual",
)
def me(usuario: User = Depends(get_current_user)):
    return {"username": usuario.username, "nome": usuario.nome}


# ========== TAREFAS ==========


class Tarefa(BaseModel):
    id: int
    titulo: str
    concluida: bool = False
    criada_em: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class TarefaCreate(BaseModel):
    titulo: str = Field(..., min_length=1, max_length=200)


tarefas_db = [
    Tarefa(id=1, titulo="Comprar leite", concluida=False),
    Tarefa(id=2, titulo="Estudar Python", concluida=True),
    Tarefa(id=3, titulo="Fazer exercicios", concluida=False),
]


@app.get(
    "/api/v1/tarefas",
    response_model=List[Tarefa],
    tags=["Tarefas"],
    summary="Listar tarefas",
)
def listar_tarefas(
    concluida: Optional[bool] = Query(None, description="Filtrar por status"),
    usuario: User = Depends(get_current_user),
):
    if concluida is None:
        return tarefas_db
    return [t for t in tarefas_db if t.concluida == concluida]


@app.post(
    "/api/v1/tarefas",
    response_model=Tarefa,
    status_code=201,
    tags=["Tarefas"],
    summary="Adicionar tarefa",
)
def adicionar_tarefa(
    tarefa: TarefaCreate,
    usuario: User = Depends(get_current_user),
):
    novo_id = max(t.id for t in tarefas_db) + 1 if tarefas_db else 1
    nova = Tarefa(id=novo_id, titulo=tarefa.titulo)
    tarefas_db.append(nova)
    return nova


@app.delete(
    "/api/v1/tarefas/{tarefa_id}",
    status_code=204,
    tags=["Tarefas"],
    summary="Remover tarefa",
)
def remover_tarefa(
    tarefa_id: int = Path(..., gt=0),
    usuario: User = Depends(get_current_user),
):
    for i, t in enumerate(tarefas_db):
        if t.id == tarefa_id:
            tarefas_db.pop(i)
            return
    raise HTTPException(status_code=404, detail="Tarefa nao encontrada")


if __name__ == "__main__":
    print("Iniciando Tarefas API...")
    print("Swagger UI: http://localhost:8001/docs")
    uvicorn.run(app, host="0.0.0.0", port=8001)
