#!/bin/bash

set -e

echo "========================================="
echo "MCP Server Universal - Setup (Linux/Mac)"
echo "========================================="

# Python setup
echo ""
echo "[1/3] Creating Python virtual environment..."
python3 -m venv venv

echo ""
echo "[2/3] Installing Python dependencies..."
./venv/bin/pip install --upgrade pip
./venv/bin/pip install fastmcp httpx "pydantic>=2.10"

# Node.js setup
echo ""
echo "[3/3] Installing Node.js dependencies..."
npm install -g swagger2openapi

echo ""
echo "========================================="
echo "Setup complete!"
echo "========================================="
echo ""
echo "Next steps:"
echo "  - Production: Configure your MCP client (VS Code, Claude, etc.)"
echo "  - Development: export MCP_SPEC_URL=https://petstore.swagger.io/v2/swagger.json"
echo "  - Development: export MCP_SERVER_NAME=PetStore API"
echo "  - Development: ./venv/bin/python main.py --inspect"
