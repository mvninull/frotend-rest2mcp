# rest2mcp - Setup (Windows PowerShell)

Write-Host "=========================================" -ForegroundColor Cyan
Write-Host "rest2mcp - Setup (Windows)" -ForegroundColor Cyan
Write-Host "=========================================" -ForegroundColor Cyan

# Python setup
Write-Host ""
Write-Host "[1/3] Creating Python virtual environment..." -ForegroundColor Green
python -m venv venv

Write-Host ""
Write-Host "[2/3] Installing Python dependencies..." -ForegroundColor Green
./venv/Scripts/pip install --upgrade pip
./venv/Scripts/pip install fastmcp httpx "pydantic>=2.10"

# Node.js setup
Write-Host ""
Write-Host "[3/3] Installing Node.js dependencies..." -ForegroundColor Green
npm install -g swagger2openapi

Write-Host ""
Write-Host "=========================================" -ForegroundColor Cyan
Write-Host "Setup complete!" -ForegroundColor Green
Write-Host "=========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Next steps:" -ForegroundColor Yellow
Write-Host "  - Production: Configure your MCP client (VS Code, Claude, etc.)"
Write-Host "  - Development: `$env:MCP_SPEC_URL = 'https://petstore.swagger.io/v2/swagger.json'"
Write-Host "  - Development: `$env:MCP_SERVER_NAME = 'PetStore API'"
Write-Host "  - Development: ./venv/Scripts/python main.py --inspect"
