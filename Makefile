.PHONY: help install run export test docker-build docker-run

help:
	@echo "ServiceNow MCP Server - Comandos Disponíveis:"
	@echo "  make install       Instala as dependências Python"
	@echo "  make run           Inicia o servidor MCP via Stdio Bridge"
	@echo "  make export        Exporta os esquemas JSON de todas as 97 ferramentas"
	@echo "  make test          Executa os testes automatizados com pytest"
	@echo "  make docker-build  Constrói a imagem Docker"
	@echo "  make docker-run    Executa o container Docker"

install:
	pip install -r requirements.txt

run:
	python servicenow-mcp-bridge.py

export:
	python export_schemas.py

test:
	pytest tests/

docker-build:
	docker build -t servicenow-mcp-server:latest .

docker-run:
	docker run -it --rm --env-file .env servicenow-mcp-server:latest
