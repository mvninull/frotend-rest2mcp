#!/bin/bash
# Testes da Loja API

echo "🚀 Testando Loja API"
echo "===================="

BASE="http://localhost:8000"

echo ""
echo "1. Home:"
curl -s $BASE/ | python3 -m json.tool

echo ""
echo "2. Listar todos os produtos:"
curl -s $BASE/api/v1/produtos | python3 -m json.tool

echo ""
echo "3. Buscar produto ID 1:"
curl -s $BASE/api/v1/produtos/1 | python3 -m json.tool

echo ""
echo "4. Filtrar por categoria 'Eletrônicos':"
curl -s "$BASE/api/v1/produtos?categoria=Eletrônicos" | python3 -m json.tool

echo ""
echo "5. Criar novo produto:"
curl -s -X POST $BASE/api/v1/produtos   -H "Content-Type: application/json"   -d '{"nome":"Webcam 4K","preco":299.99,"categoria":"Periféricos","em_estoque":true}' | python3 -m json.tool

echo ""
echo "6. Listar categorias:"
curl -s $BASE/api/v1/categorias | python3 -m json.tool

echo ""
echo "7. OpenAPI Spec:"
curl -s $BASE/openapi.json | python3 -m json.tool | head -50

echo ""
echo "✅ Testes completos!"
