from fastapi import FastAPI, HTTPException, Query, Path
from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime, timezone
import uvicorn

app = FastAPI(
    title="Loja API",
    description="API simples de demonstração para teste de auto-discovery",
    version="1.0.0",
    docs_url="/docs",  # Swagger UI
    redoc_url="/redoc",  # ReDoc
    openapi_url="/openapi.json",  # OpenAPI spec
)

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

    class Config:
        json_schema_extra = {
            "example": {
                "id": 1,
                "nome": "Notebook Dell",
                "preco": 4500.00,
                "categoria": "Eletrônicos",
                "em_estoque": True,
                "criado_em": "2024-01-15T10:30:00",
            }
        }


class ProdutoCreate(BaseModel):
    nome: str = Field(..., min_length=2, max_length=100, description="Nome do produto")
    preco: float = Field(..., gt=0, description="Preço em reais")
    categoria: str = Field(..., description="Categoria do produto")
    em_estoque: Optional[bool] = Field(
        default=True, description="Disponível em estoque"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "nome": "Mouse Logitech",
                "preco": 150.00,
                "categoria": "Periféricos",
                "em_estoque": True,
            }
        }


class ProdutoUpdate(BaseModel):
    nome: Optional[str] = Field(None, min_length=2, max_length=100)
    preco: Optional[float] = Field(None, gt=0)
    categoria: Optional[str] = None
    em_estoque: Optional[bool] = None


class ErrorResponse(BaseModel):
    detail: str = Field(..., description="Mensagem de erro")


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
    Produto(
        id=4, nome="Monitor 27", preco=1200.00, categoria="Eletrônicos", em_estoque=True
    ),
]

# ========== ENDPOINTS ==========


@app.get("/", tags=["Root"], summary="Home")
def home():
    """Endpoint raiz da API."""
    return {"message": "Bem-vindo à Loja API", "docs": "/docs"}


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
def buscar_produto(produto_id: int = Path(..., gt=0, description="ID do produto")):
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
def criar_produto(produto: ProdutoCreate):
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
def deletar_produto(produto_id: int = Path(..., gt=0, description="ID do produto")):
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
def listar_categorias():
    """
    Lista todas as categorias disponíveis.
    """
    categorias = list(set(p.categoria for p in produtos_db))
    return {"categorias": categorias, "total": len(categorias)}


# ========== RUN ==========

if __name__ == "__main__":
    print("🚀 Iniciando Loja API...")
    print("📚 Swagger UI: http://localhost:8000/docs")
    print("📖 ReDoc: http://localhost:8000/redoc")
    print("🔧 OpenAPI JSON: http://localhost:8000/openapi.json")
    uvicorn.run(app, host="0.0.0.0", port=8000)
