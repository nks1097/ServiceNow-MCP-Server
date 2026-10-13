#!/usr/bin/env python3
"""
ServiceNow MCP Server - Bridge Stdio nativo para Antigravity IDE.
Suporta ferramentas nativas em Português com Aliases em Inglês para máxima interoperabilidade.
Redireciona stderr para logs/servicenow_bridge.log para estabilidade total no pipe stdio.
"""

import asyncio
import inspect
import json
import os
import sys
from pathlib import Path

# Configurações de ambiente silenciosas
os.environ["PYTHONIOENCODING"] = "utf-8"
os.environ["FASTMCP_SHOW_SERVER_BANNER"] = "false"
os.environ["FASTMCP_LOG_LEVEL"] = "CRITICAL"

# Redireciona stderr para log local
LOG_DIR = Path(__file__).resolve().parent / "logs"
LOG_DIR.mkdir(exist_ok=True)
sys.stderr = open(LOG_DIR / "servicenow_bridge.log", "a", encoding="utf-8")

# Adiciona o diretório atual ao sys.path
BASE_DIR = Path(__file__).resolve().parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

# Importa o módulo do servidor ServiceNow
import servicenow_mcp_server as srv

# Mapeamento oficial de ferramentas em Português
TOOLS_HANDLERS = {
    # Core CRUD & Metadados
    "servicenow_consultar_tabela": srv.servicenow_consultar_tabela,
    "servicenow_obter_registro_por_id": srv.servicenow_obter_registro_por_id,
    "servicenow_criar_registro": srv.servicenow_criar_registro,
    "servicenow_atualizar_registro": srv.servicenow_atualizar_registro,
    "servicenow_excluir_registro": srv.servicenow_excluir_registro,
    "servicenow_descrever_campos_tabela": srv.servicenow_descrever_campos_tabela,
    "servicenow_listar_tabelas": srv.servicenow_listar_tabelas,
    "servicenow_obter_estatisticas_tabela": srv.servicenow_obter_estatisticas_tabela,
    # Incidentes
    "servicenow_criar_incidente": srv.servicenow_criar_incidente,
    "servicenow_atualizar_incidente": srv.servicenow_atualizar_incidente,
    "servicenow_adicionar_comentario": srv.servicenow_adicionar_comentario,
    "servicenow_adicionar_nota_tecnica": srv.servicenow_adicionar_nota_tecnica,
    "servicenow_resolver_incidente": srv.servicenow_resolver_incidente,
    "servicenow_listar_incidentes": srv.servicenow_listar_incidentes,
    "servicenow_abrir_incidente_seguranca": srv.servicenow_abrir_incidente_seguranca,
    "servicenow_fechar_incidente": srv.servicenow_fechar_incidente,
    # Catálogo de Serviços
    "servicenow_listar_itens_catalogo": srv.servicenow_listar_itens_catalogo,
    "servicenow_obter_item_catalogo": srv.servicenow_obter_item_catalogo,
    "servicenow_atualizar_item_catalogo": srv.servicenow_atualizar_item_catalogo,
    "servicenow_listar_categorias_catalogo": srv.servicenow_listar_categorias_catalogo,
    "servicenow_criar_categoria_catalogo": srv.servicenow_criar_categoria_catalogo,
    "servicenow_atualizar_categoria_catalogo": srv.servicenow_atualizar_categoria_catalogo,
    "servicenow_mover_item_catalogo": srv.servicenow_mover_item_catalogo,
    "servicenow_criar_variavel_item_catalogo": srv.servicenow_criar_variavel_item_catalogo,
    "servicenow_listar_variaveis_item_catalogo": srv.servicenow_listar_variaveis_item_catalogo,
    "servicenow_atualizar_variavel_item_catalogo": srv.servicenow_atualizar_variavel_item_catalogo,
    "servicenow_listar_catalogos": srv.servicenow_listar_catalogos,
    "servicenow_obter_recomendacoes_otimizacao_catalogo": srv.servicenow_obter_recomendacoes_otimizacao_catalogo,
    # Mudanças (GMUD)
    "servicenow_criar_solicitacao_mudanca": srv.servicenow_criar_solicitacao_mudanca,
    "servicenow_atualizar_solicitacao_mudanca": srv.servicenow_atualizar_solicitacao_mudanca,
    "servicenow_listar_solicitacoes_mudanca": srv.servicenow_listar_solicitacoes_mudanca,
    "servicenow_obter_detalhes_mudanca": srv.servicenow_obter_detalhes_mudanca,
    "servicenow_adicionar_tarefa_mudanca": srv.servicenow_adicionar_tarefa_mudanca,
    "servicenow_enviar_mudanca_aprovacao": srv.servicenow_enviar_mudanca_aprovacao,
    "servicenow_aprovar_mudanca": srv.servicenow_aprovar_mudanca,
    "servicenow_rejeitar_mudanca": srv.servicenow_rejeitar_mudanca,
    "servicenow_criar_gmud": srv.servicenow_criar_gmud,
    # Gestão Ágil & Projetos
    "servicenow_criar_historia": srv.servicenow_criar_historia,
    "servicenow_atualizar_historia": srv.servicenow_atualizar_historia,
    "servicenow_listar_historias": srv.servicenow_listar_historias,
    "servicenow_criar_dependencia_historia": srv.servicenow_criar_dependencia_historia,
    "servicenow_excluir_dependencia_historia": srv.servicenow_excluir_dependencia_historia,
    "servicenow_criar_epico": srv.servicenow_criar_epico,
    "servicenow_atualizar_epico": srv.servicenow_atualizar_epico,
    "servicenow_listar_epicos": srv.servicenow_listar_epicos,
    "servicenow_criar_tarefa_scrum": srv.servicenow_criar_tarefa_scrum,
    "servicenow_atualizar_tarefa_scrum": srv.servicenow_atualizar_tarefa_scrum,
    "servicenow_listar_tarefas_scrum": srv.servicenow_listar_tarefas_scrum,
    "servicenow_criar_projeto": srv.servicenow_criar_projeto,
    "servicenow_atualizar_projeto": srv.servicenow_atualizar_projeto,
    "servicenow_listar_projetos": srv.servicenow_listar_projetos,
    # Fluxos de Trabalho
    "servicenow_listar_fluxos_trabalho": srv.servicenow_listar_fluxos_trabalho,
    "servicenow_obter_fluxo_trabalho": srv.servicenow_obter_fluxo_trabalho,
    "servicenow_criar_fluxo_trabalho": srv.servicenow_criar_fluxo_trabalho,
    "servicenow_atualizar_fluxo_trabalho": srv.servicenow_atualizar_fluxo_trabalho,
    "servicenow_excluir_fluxo_trabalho": srv.servicenow_excluir_fluxo_trabalho,
    # Script Includes
    "servicenow_listar_script_includes": srv.servicenow_listar_script_includes,
    "servicenow_obter_script_include": srv.servicenow_obter_script_include,
    "servicenow_criar_script_include": srv.servicenow_criar_script_include,
    "servicenow_atualizar_script_include": srv.servicenow_atualizar_script_include,
    "servicenow_excluir_script_include": srv.servicenow_excluir_script_include,
    # Update Sets
    "servicenow_listar_conjuntos_alteracoes": srv.servicenow_listar_conjuntos_alteracoes,
    "servicenow_obter_detalhes_conjunto_alteracoes": srv.servicenow_obter_detalhes_conjunto_alteracoes,
    "servicenow_criar_conjunto_alteracoes": srv.servicenow_criar_conjunto_alteracoes,
    "servicenow_atualizar_conjunto_alteracoes": srv.servicenow_atualizar_conjunto_alteracoes,
    "servicenow_confirmar_conjunto_alteracoes": srv.servicenow_confirmar_conjunto_alteracoes,
    "servicenow_publicar_conjunto_alteracoes": srv.servicenow_publicar_conjunto_alteracoes,
    "servicenow_adicionar_arquivo_conjunto_alteracoes": srv.servicenow_adicionar_arquivo_conjunto_alteracoes,
    # Base de Conhecimento
    "servicenow_criar_base_conhecimento": srv.servicenow_criar_base_conhecimento,
    "servicenow_listar_bases_conhecimento": srv.servicenow_listar_bases_conhecimento,
    "servicenow_criar_categoria_conhecimento": srv.servicenow_criar_categoria_conhecimento,
    "servicenow_criar_artigo_conhecimento": srv.servicenow_criar_artigo_conhecimento,
    "servicenow_atualizar_artigo_conhecimento": srv.servicenow_atualizar_artigo_conhecimento,
    "servicenow_publicar_artigo_conhecimento": srv.servicenow_publicar_artigo_conhecimento,
    "servicenow_listar_artigos_conhecimento": srv.servicenow_listar_artigos_conhecimento,
    "servicenow_obter_artigo_conhecimento": srv.servicenow_obter_artigo_conhecimento,
    "servicenow_consultar_base_conhecimento": srv.servicenow_consultar_base_conhecimento,
    # Usuários, Grupos e Membros
    "servicenow_criar_usuario": srv.servicenow_criar_usuario,
    "servicenow_atualizar_usuario": srv.servicenow_atualizar_usuario,
    "servicenow_obter_usuario": srv.servicenow_obter_usuario,
    "servicenow_listar_usuarios": srv.servicenow_listar_usuarios,
    "servicenow_buscar_usuario": srv.servicenow_buscar_usuario,
    "servicenow_criar_grupo": srv.servicenow_criar_grupo,
    "servicenow_atualizar_grupo": srv.servicenow_atualizar_grupo,
    "servicenow_listar_grupos": srv.servicenow_listar_grupos,
    "servicenow_buscar_grupo": srv.servicenow_buscar_grupo,
    "servicenow_adicionar_membros_grupo": srv.servicenow_adicionar_membros_grupo,
    "servicenow_remover_membros_grupo": srv.servicenow_remover_membros_grupo,
    "servicenow_atribuir_chamado": srv.servicenow_atribuir_chamado,
    # Gestão de Problemas
    "servicenow_criar_problema": srv.servicenow_criar_problema,
    "servicenow_vincular_incidente_problema": srv.servicenow_vincular_incidente_problema,
    # CMDB, Relacionamentos, Anexos, Auditoria & Health
    "servicenow_consultar_cmdb": srv.servicenow_consultar_cmdb,
    "servicenow_obter_relacionamentos_ci": srv.servicenow_obter_relacionamentos_ci,
    "servicenow_anexar_arquivo": srv.servicenow_anexar_arquivo,
    "servicenow_listar_anexos": srv.servicenow_listar_anexos,
    "servicenow_consultar_auditoria": srv.servicenow_consultar_auditoria,
    "servicenow_testar_conexao": srv.servicenow_testar_conexao,
}

# Mapeamento de Aliases em Inglês
ALIASES = {
    # Incidentes
    "create_incident": "servicenow_criar_incidente",
    "update_incident": "servicenow_atualizar_incidente",
    "add_comment": "servicenow_adicionar_comentario",
    "resolve_incident": "servicenow_resolver_incidente",
    "list_incidents": "servicenow_listar_incidentes",
    # Catálogo
    "list_catalog_items": "servicenow_listar_itens_catalogo",
    "get_catalog_item": "servicenow_obter_item_catalogo",
    "update_catalog_item": "servicenow_atualizar_item_catalogo",
    "list_catalog_categories": "servicenow_listar_categorias_catalogo",
    "create_catalog_category": "servicenow_criar_categoria_catalogo",
    "update_catalog_category": "servicenow_atualizar_categoria_catalogo",
    "move_catalog_item": "servicenow_mover_item_catalogo",
    "mover_itens_do_catálogo": "servicenow_mover_item_catalogo",
    "create_catalog_item_variable": "servicenow_criar_variavel_item_catalogo",
    "list_catalog_item_variables": "servicenow_listar_variaveis_item_catalogo",
    "update_catalog_item_variable": "servicenow_atualizar_variavel_item_catalogo",
    "list_catalogs": "servicenow_listar_catalogos",
    "get_optimization_recommendations": "servicenow_obter_recomendacoes_otimizacao_catalogo",
    # Mudanças
    "create_change_request": "servicenow_criar_solicitacao_mudanca",
    "update_change_request": "servicenow_atualizar_solicitacao_mudanca",
    "list_change_requests": "servicenow_listar_solicitacoes_mudanca",
    "get_change_request_details": "servicenow_obter_detalhes_mudanca",
    "add_change_task": "servicenow_adicionar_tarefa_mudanca",
    "submit_change_for_approval": "servicenow_enviar_mudanca_aprovacao",
    "approve_change": "servicenow_aprovar_mudanca",
    "reject_change": "servicenow_rejeitar_mudanca",
    # Ágil
    "create_story": "servicenow_criar_historia",
    "update_story": "servicenow_atualizar_historia",
    "list_stories": "servicenow_listar_historias",
    "create_story_dependency": "servicenow_criar_dependencia_historia",
    "create_tory_dependency": "servicenow_criar_dependencia_historia",
    "delete_story_dependency": "servicenow_excluir_dependencia_historia",
    "create_epic": "servicenow_criar_epico",
    "update_epic": "servicenow_atualizar_epico",
    "list_epics": "servicenow_listar_epicos",
    "create_scrum_task": "servicenow_criar_tarefa_scrum",
    "update_scrum_task": "servicenow_atualizar_tarefa_scrum",
    "list_scrum_tasks": "servicenow_listar_tarefas_scrum",
    "create_project": "servicenow_criar_projeto",
    "criar_projeto": "servicenow_criar_projeto",
    "update_project": "servicenow_atualizar_projeto",
    "list_projects": "servicenow_listar_projetos",
    # Fluxos
    "list_workflows": "servicenow_listar_fluxos_trabalho",
    "get_workflow": "servicenow_obter_fluxo_trabalho",
    "create_workflow": "servicenow_criar_fluxo_trabalho",
    "criar_fluxo_de_trabalho": "servicenow_criar_fluxo_trabalho",
    "update_workflow": "servicenow_atualizar_fluxo_trabalho",
    "delete_workflow": "servicenow_excluir_fluxo_trabalho",
    # Script Includes
    "list_script_includes": "servicenow_listar_script_includes",
    "get_script_include": "servicenow_obter_script_include",
    "create_script_include": "servicenow_criar_script_include",
    "update_script_include": "servicenow_atualizar_script_include",
    "delete_script_include": "servicenow_excluir_script_include",
    # Update Sets
    "list_changesets": "servicenow_listar_conjuntos_alteracoes",
    "get_changeset_details": "servicenow_obter_detalhes_conjunto_alteracoes",
    "create_changeset": "servicenow_criar_conjunto_alteracoes",
    "update_changeset": "servicenow_atualizar_conjunto_alteracoes",
    "commit_changeset": "servicenow_confirmar_conjunto_alteracoes",
    "publicar_conjunto_de_alterações": "servicenow_publicar_conjunto_alteracoes",
    "publish_changeset": "servicenow_publicar_conjunto_alteracoes",
    "add_file_to_changeset": "servicenow_adicionar_arquivo_conjunto_alteracoes",
    # Base de Conhecimento
    "create_knowledge_base": "servicenow_criar_base_conhecimento",
    "criar_base_de_conhecimento": "servicenow_criar_base_conhecimento",
    "list_knowledge_bases": "servicenow_listar_bases_conhecimento",
    "listar bases de conhecimento": "servicenow_listar_bases_conhecimento",
    "create_knowledge_category": "servicenow_criar_categoria_conhecimento",
    "criar_categoria": "servicenow_criar_categoria_conhecimento",
    "create_article": "servicenow_criar_artigo_conhecimento",
    "update_article": "servicenow_atualizar_artigo_conhecimento",
    "publish_article": "servicenow_publicar_artigo_conhecimento",
    "publicar_artigo": "servicenow_publicar_artigo_conhecimento",
    "list_articles": "servicenow_listar_artigos_conhecimento",
    "get_article": "servicenow_obter_artigo_conhecimento",
    # Usuários e Grupos
    "create_user": "servicenow_criar_usuario",
    "criar_usuário": "servicenow_criar_usuario",
    "update_user": "servicenow_atualizar_usuario",
    "get_user": "servicenow_obter_usuario",
    "list_users": "servicenow_listar_usuarios",
    "create_group": "servicenow_criar_grupo",
    "criar_grupo": "servicenow_criar_grupo",
    "update_group": "servicenow_atualizar_grupo",
    "list_groups": "servicenow_listar_grupos",
    "add_group_members": "servicenow_adicionar_membros_grupo",
    "remove_group_members": "servicenow_remover_membros_grupo",
}


def load_tools_list() -> list:
    """Carrega os esquemas salvos em *.json para retornar em tools/list."""
    tools = []
    for tool_name in TOOLS_HANDLERS.keys():
        json_file = BASE_DIR / f"{tool_name}.json"
        if json_file.exists():
            try:
                with open(json_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    tools.append({
                        "name": data.get("name", tool_name),
                        "description": data.get("description", ""),
                        "inputSchema": data.get("parameters", {"type": "object", "properties": {}}),
                    })
            except Exception as e:
                sys.stderr.write(f"Erro ao carregar schema {tool_name}: {e}\n")
    return tools


def write_response(payload: dict):
    line = json.dumps(payload, ensure_ascii=False)
    sys.stdout.write(line + "\n")
    sys.stdout.flush()


async def execute_tool_async(tool_name: str, arguments: dict) -> dict:
    # Resolve alias se necessário
    real_tool_name = ALIASES.get(tool_name, tool_name)
    handler = TOOLS_HANDLERS.get(real_tool_name)

    if not handler:
        return {
            "content": [{"type": "text", "text": f"Ferramenta '{tool_name}' não encontrada no ServiceNow MCP Server."}],
            "isError": True,
        }

    try:
        if inspect.iscoroutinefunction(handler):
            result = await handler(**arguments)
        else:
            result = handler(**arguments)

        text_out = json.dumps(result, ensure_ascii=False, indent=2)
        is_err = isinstance(result, dict) and result.get("status") == "erro"

        return {
            "content": [{"type": "text", "text": text_out}],
            "isError": is_err,
        }
    except Exception as exc:
        return {
            "content": [{"type": "text", "text": f"Erro na execução da ferramenta {tool_name}: {str(exc)}"}],
            "isError": True,
        }


def main():
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    try:
        for raw_line in sys.stdin:
            raw_line = raw_line.strip()
            if not raw_line:
                continue

            try:
                msg = json.loads(raw_line)
            except json.JSONDecodeError:
                continue

            method = msg.get("method", "")
            msg_id = msg.get("id")

            # 1. Antigravity Discovery proprietário
            if method == "server/discover":
                write_response({
                    "jsonrpc": "2.0",
                    "id": msg_id,
                    "result": {
                        "serverInfo": {
                            "name": "servicenow",
                            "version": "2.0.0",
                        },
                        "capabilities": {
                            "tools": {"listChanged": False},
                        },
                    },
                })
                continue

            # 2. Inicialização MCP padrão
            if method == "initialize":
                write_response({
                    "jsonrpc": "2.0",
                    "id": msg_id,
                    "result": {
                        "protocolVersion": "2024-11-05",
                        "capabilities": {
                            "tools": {"listChanged": False},
                        },
                        "serverInfo": {
                            "name": "servicenow",
                            "version": "2.0.0",
                        },
                    },
                })
                continue

            # 3. Notificações MCP (sem id)
            if method == "notifications/initialized":
                continue

            # 4. Ping
            if method == "ping":
                write_response({
                    "jsonrpc": "2.0",
                    "id": msg_id,
                    "result": {},
                })
                continue

            # 5. Listagem de ferramentas
            if method == "tools/list":
                write_response({
                    "jsonrpc": "2.0",
                    "id": msg_id,
                    "result": {
                        "tools": load_tools_list(),
                    },
                })
                continue

            # 6. Execução de ferramentas
            if method == "tools/call":
                params = msg.get("params", {})
                tool_name = params.get("name", "")
                arguments = params.get("arguments", {})
                call_result = loop.run_until_complete(execute_tool_async(tool_name, arguments))
                write_response({
                    "jsonrpc": "2.0",
                    "id": msg_id,
                    "result": call_result,
                })
                continue

            # Métodos desconhecidos
            if msg_id is not None:
                write_response({
                    "jsonrpc": "2.0",
                    "id": msg_id,
                    "error": {
                        "code": -32601,
                        "message": f"Método não suportado: {method}",
                    },
                })

    except (KeyboardInterrupt, BrokenPipeError, EOFError):
        pass
    finally:
        loop.close()


if __name__ == "__main__":
    main()
