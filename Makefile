.PHONY: help install-python install-node install clean inspect

OS := $(shell uname -s 2>/dev/null || echo Windows)

ifeq ($(OS),Windows_NT)
    VENV_ACTIVATE = venv/Scripts/activate
    PYTHON = venv/Scripts/python
    PIP = venv/Scripts/pip
    RM = powershell -Command "Remove-Item -Recurse -Force"
else
    VENV_ACTIVATE = venv/bin/activate
    PYTHON = venv/bin/python
    PIP = venv/bin/pip
    RM = rm -rf
endif

help:
	@echo "MCP Server Universal - Makefile Targets"
	@echo "======================================="
	@echo "install-python  : Create Python venv and install required pip packages"
	@echo "install-node    : Install global Node.js dependency (swagger2openapi)"
	@echo "install         : Run all installation steps (python + node)"
	@echo "clean           : Remove venv and temporary files"
	@echo "inspect         : Launch MCP Inspector (requires MCP_SPEC_URL to be set)"

install-python:
	python -m venv venv
	$(PIP) install --upgrade pip
	$(PIP) install fastmcp httpx "pydantic>=2.10"

install-node:
	npm install -g swagger2openapi

install: install-python install-node

clean:
	$(RM) venv
	$(RM) _temp_swagger2.json _temp_openapi3.json

inspect:
	@test -n "$(MCP_SPEC_URL)" || (echo "Error: MCP_SPEC_URL environment variable is not set" && exit 1)
	$(PYTHON) main.py --inspect
