from datetime import datetime, timedelta, timezone
from typing import List, Optional

import uvicorn
from fastapi import Depends, FastAPI, Form, HTTPException, Path, Query, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from pydantic import BaseModel, ConfigDict, Field

app = FastAPI(
    title="Loja API",
    description="API simples de demonstração para teste de auto-discovery",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    swagger_ui_parameters={"persistAuthorization": True},
)

# Make Swagger UI show the Authorize button for all protected routes


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

# ========== MODELS ==========


class Produto(BaseModel):
    id: int = Field(..., description="ID único do produto")
    nome: str = Field(..., min_length=2, max_length=100, description="Nome do produto")
    preco: float = Field(..., gt=0, description="Preço em reais")
    categoria: str = Field(..., description="Categoria do produto")
    em_estoque: bool = Field(default=True, description="Disponível em estoque")
    criado_em: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Data de criação",
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "id": 1,
                "nome": "Notebook Dell",
                "preco": 4500.00,
                "categoria": "Eletrônicos",
                "em_estoque": True,
                "criado_em": "2024-01-15T10:30:00",
            }
        }
    )


class ProdutoCreate(BaseModel):
    nome: str = Field(..., min_length=2, max_length=100, description="Nome do produto")
    preco: float = Field(..., gt=0, description="Preço em reais")
    categoria: str = Field(..., description="Categoria do produto")
    em_estoque: Optional[bool] = Field(default=True, description="Disponível em estoque")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "nome": "Mouse Logitech",
                "preco": 150.00,
                "categoria": "Periféricos",
                "em_estoque": True,
            }
        }
    )


class ProdutoUpdate(BaseModel):
    nome: Optional[str] = Field(None, min_length=2, max_length=100)
    preco: Optional[float] = Field(None, gt=0)
    categoria: Optional[str] = None
    em_estoque: Optional[bool] = None


class ErrorResponse(BaseModel):
    detail: str = Field(..., description="Mensagem de erro")


# ========== AUTH CONFIG ==========

SECRET_KEY = "super-secret-key-mude-em-producao"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
security = HTTPBearer()


class LoginRequest(BaseModel):
    username: str
    password: str


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
    User(
        username="user",
        hashed_password=pwd_context.hash("senha123"),
        nome="Usuário Teste",
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
            raise HTTPException(status_code=401, detail="Token inválido")
    except JWTError:
        raise HTTPException(status_code=401, detail="Token inválido ou expirado")
    for user in fake_users_db:
        if user.username == username:
            return user
    raise HTTPException(status_code=401, detail="Usuário não encontrado")


# ========== DATABASE MOCK ==========

produtos_db = [
    Produto(
        id=1,
        nome="Notebook Dell",
        preco=4500.00,
        categoria="Eletrônicos",
        em_estoque=True,
    ),
    Produto(
        id=2,
        nome="Mouse Logitech",
        preco=150.00,
        categoria="Periféricos",
        em_estoque=True,
    ),
    Produto(
        id=3,
        nome="Teclado Mecânico",
        preco=350.00,
        categoria="Periféricos",
        em_estoque=False,
    ),
    Produto(id=4, nome="Monitor 27", preco=1200.00, categoria="Eletrônicos", em_estoque=True),
]

# ========== ENDPOINTS ==========


@app.get("/", tags=["Root"], summary="Home")
def home():
    """Endpoint raiz da API."""
    return {"message": "Bem-vindo à Loja API", "docs": "/docs"}


# ========== AUTH ENDPOINTS ==========


@app.post(
    "/api/v1/auth/login",
    response_model=TokenResponse,
    tags=["Autenticação"],
    summary="Login",
    description="Autentica um usuário e retorna um token JWT.",
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
        detail="Usuário ou senha inválidos",
    )


@app.get(
    "/api/v1/auth/me",
    tags=["Autenticação"],
    summary="Dados do usuário atual",
    description="Retorna informações do usuário autenticado.",
)
def me(usuario: User = Depends(get_current_user)):
    return {"username": usuario.username, "nome": usuario.nome}


# ========== PRODUCT ENDPOINTS ==========


@app.get(
    "/api/v1/produtos",
    response_model=List[Produto],
    tags=["Produtos"],
    summary="Listar todos os produtos",
    description="Retorna a lista completa de produtos cadastrados.",
)
def listar_produtos(
    categoria: Optional[str] = Query(None, description="Filtrar por categoria"),
    em_estoque: Optional[bool] = Query(None, description="Filtrar por disponibilidade"),
    usuario: User = Depends(get_current_user),
):
    """
    Lista todos os produtos com filtros opcionais por categoria e estoque.
    """
    resultado = produtos_db

    if categoria:
        resultado = [p for p in resultado if p.categoria.lower() == categoria.lower()]

    if em_estoque is not None:
        resultado = [p for p in resultado if p.em_estoque == em_estoque]

    return resultado


@app.get(
    "/api/v1/produtos/{produto_id}",
    response_model=Produto,
    tags=["Produtos"],
    summary="Buscar produto por ID",
    description="Retorna os detalhes de um produto específico.",
    responses={404: {"model": ErrorResponse, "description": "Produto não encontrado"}},
)
def buscar_produto(
    produto_id: int = Path(..., gt=0, description="ID do produto"),
    usuario: User = Depends(get_current_user),
):
    """
    Busca um produto pelo ID único.
    """
    for produto in produtos_db:
        if produto.id == produto_id:
            return produto
    raise HTTPException(status_code=404, detail=f"Produto {produto_id} não encontrado")


@app.post(
    "/api/v1/produtos",
    response_model=Produto,
    status_code=201,
    tags=["Produtos"],
    summary="Criar novo produto",
    description="Cadastra um novo produto no sistema.",
    responses={
        201: {"description": "Produto criado com sucesso"},
        422: {"description": "Dados inválidos"},
    },
)
def criar_produto(
    produto: ProdutoCreate,
    usuario: User = Depends(get_current_user),
):
    """
    Cria um novo produto com os dados fornecidos.
    """
    novo_id = max(p.id for p in produtos_db) + 1
    novo_produto = Produto(
        id=novo_id,
        nome=produto.nome,
        preco=produto.preco,
        categoria=produto.categoria,
        em_estoque=produto.em_estoque,
    )
    produtos_db.append(novo_produto)
    return novo_produto


@app.put(
    "/api/v1/produtos/{produto_id}",
    response_model=Produto,
    tags=["Produtos"],
    summary="Atualizar produto",
    description="Atualiza os dados de um produto existente.",
    responses={
        404: {"model": ErrorResponse, "description": "Produto não encontrado"},
        422: {"description": "Dados inválidos"},
    },
)
def atualizar_produto(
    produto_id: int = Path(..., gt=0, description="ID do produto"),
    dados: ProdutoUpdate = ...,
    usuario: User = Depends(get_current_user),
):
    """
    Atualiza parcialmente um produto existente.
    """
    for produto in produtos_db:
        if produto.id == produto_id:
            if dados.nome is not None:
                produto.nome = dados.nome
            if dados.preco is not None:
                produto.preco = dados.preco
            if dados.categoria is not None:
                produto.categoria = dados.categoria
            if dados.em_estoque is not None:
                produto.em_estoque = dados.em_estoque
            return produto
    raise HTTPException(status_code=404, detail=f"Produto {produto_id} não encontrado")


@app.delete(
    "/api/v1/produtos/{produto_id}",
    status_code=204,
    tags=["Produtos"],
    summary="Deletar produto",
    description="Remove um produto do sistema.",
    responses={
        204: {"description": "Produto deletado com sucesso"},
        404: {"model": ErrorResponse, "description": "Produto não encontrado"},
    },
)
def deletar_produto(
    produto_id: int = Path(..., gt=0, description="ID do produto"),
    usuario: User = Depends(get_current_user),
):
    """
    Remove permanentemente um produto.
    """
    for i, produto in enumerate(produtos_db):
        if produto.id == produto_id:
            produtos_db.pop(i)
            return
    raise HTTPException(status_code=404, detail=f"Produto {produto_id} não encontrado")


@app.get(
    "/api/v1/categorias",
    tags=["Categorias"],
    summary="Listar categorias",
    description="Retorna todas as categorias únicas de produtos.",
)
def listar_categorias(
    usuario: User = Depends(get_current_user),
):
    """
    Lista todas as categorias disponíveis.
    """
    categorias = list(set(p.categoria for p in produtos_db))
    return {"categorias": categorias, "total": len(categorias)}


# ========== RUN ==========

if __name__ == "__main__":
    print("Iniciando Loja API...")
    print("Swagger UI: http://localhost:8000/docs")
    print("ReDoc: http://localhost:8000/redoc")
    print("OpenAPI JSON: http://localhost:8000/openapi.json")
    uvicorn.run(app, host="0.0.0.0", port=8000)
