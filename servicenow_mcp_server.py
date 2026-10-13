#!/usr/bin/env python3
"""
ServiceNow MCP Server - Suíte Empresarial Completa em Português para ITSM, CMDB,
Catálogo de Serviços, Gestão Ágil, Update Sets, Script Includes e SOAR (Cibersegurança).
"""

import os
import sys
import re
import base64
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional
import httpx
from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP

# Carrega variáveis do arquivo .env
env_path = Path(__file__).parent / ".env"
if env_path.exists():
    load_dotenv(dotenv_path=env_path)
else:
    load_dotenv()

# Configuração de logs
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    stream=sys.stderr
)
logger = logging.getLogger("servicenow-mcp")

# Configurações da Instância
SN_INSTANCE = os.getenv("SN_INSTANCE", "").strip()
if SN_INSTANCE.startswith("https://") or SN_INSTANCE.startswith("http://"):
    SN_URL = SN_INSTANCE.rstrip("/")
else:
    SN_URL = f"https://{SN_INSTANCE}.service-now.com"

SN_USER = os.getenv("SN_USER", "admin").strip()
SN_PASS = os.getenv("SN_PASS", "").strip()
SN_TIMEOUT = float(os.getenv("SN_TIMEOUT", "30.0"))
SN_VERIFY_SSL = os.getenv("SN_VERIFY_SSL", "true").lower() not in ("false", "0", "no")

# Inicializa FastMCP
mcp = FastMCP("ServiceNow-MCP-Server")


class ServiceNowClient:
    """Cliente HTTP com suporte a autenticação por Sessão (X-UserToken), retry e anexos."""

    def __init__(self, base_url: str, user: str, password: str, timeout: float = 30.0, verify_ssl: bool = True):
        self.base_url = base_url.rstrip("/")
        self.user = user
        self.password = password
        self.timeout = timeout
        self.verify_ssl = verify_ssl
        self.client = httpx.AsyncClient(timeout=timeout, verify=verify_ssl, follow_redirects=True)
        self.user_token: Optional[str] = None
        self._authenticated = False

    async def authenticate(self) -> bool:
        login_url = f"{self.base_url}/login.do"
        try:
            r_login = await self.client.post(
                login_url,
                data={
                    "user_name": self.user,
                    "user_password": self.password,
                    "sys_action": "sysverb_login",
                },
            )
            r_nav = await self.client.get(f"{self.base_url}/navpage.do")
            m = re.search(r"g_ck\s*=\s*['\"]([^'\"]+)['\"]", r_nav.text)
            if m:
                self.user_token = m.group(1)
                self._authenticated = True
                logger.info(f"Sessão autenticada no ServiceNow ({self.base_url})")
                return True
            logger.warning("Não foi possível extrair token g_ck do ServiceNow")
            return False
        except Exception as e:
            logger.error(f"Erro ao autenticar sessão no ServiceNow: {e}")
            return False

    async def request(
        self,
        method: str,
        path: str,
        params: Optional[Dict[str, Any]] = None,
        json_data: Optional[Dict[str, Any]] = None,
        content: Optional[bytes] = None,
        headers_override: Optional[Dict[str, str]] = None,
    ) -> httpx.Response:
        url = f"{self.base_url}{path}"
        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
        }
        if headers_override:
            headers.update(headers_override)

        if not self._authenticated:
            await self.authenticate()

        if self.user_token:
            headers["X-UserToken"] = self.user_token

        r = await self.client.request(
            method=method,
            url=url,
            headers=headers,
            params=params,
            json=json_data,
            content=content,
            auth=(self.user, self.password) if not self.user_token else None
        )

        if r.status_code == 401:
            logger.info("Sessão expirada (401). Renovando credenciais...")
            success = await self.authenticate()
            if success and self.user_token:
                headers["X-UserToken"] = self.user_token
                r = await self.client.request(
                    method=method,
                    url=url,
                    headers=headers,
                    params=params,
                    json=json_data,
                    content=content
                )
            else:
                r = await self.client.request(
                    method=method,
                    url=url,
                    headers=headers,
                    params=params,
                    json=json_data,
                    content=content,
                    auth=(self.user, self.password)
                )

        return r


sn_client = ServiceNowClient(
    base_url=SN_URL,
    user=SN_USER,
    password=SN_PASS,
    timeout=SN_TIMEOUT,
    verify_ssl=SN_VERIFY_SSL
)


def _format_error(status_code: int, response_text: str) -> Dict[str, Any]:
    msg = f"HTTP {status_code}"
    dica = None
    if status_code == 401:
        msg = "Falha de Autenticação (401 Unauthorized)"
        dica = "Verifique se usuário e senha em SN_USER e SN_PASS estão corretos."
    elif status_code == 403:
        msg = "Acesso Negado (403 Forbidden)"
        dica = "Usuário sem permissões suficientes para esta tabela/recurso."
    elif status_code == 404:
        msg = "Recurso Não Encontrado (404 Not Found)"
        dica = "Verifique se a tabela ou o sys_id fornecido existem."

    return {
        "status": "erro",
        "codigo": status_code,
        "mensagem": msg,
        "detalhes": response_text,
        "dica": dica
    }


# =====================================================================
# 1. CORE CRUD & METADADOS (TABLE & DICTIONARY API)
# =====================================================================

@mcp.tool()
async def servicenow_consultar_tabela(
    tabela: str,
    query: Optional[str] = "",
    limite: int = 10,
    campos: Optional[str] = "",
    ordenar_por: Optional[str] = "",
    incluir_display_value: bool = False
) -> Dict[str, Any]:
    """Consulta registros em qualquer tabela do ServiceNow com filtros codificados."""
    encoded_query = query or ""
    if ordenar_por:
        if "ORDERBY" in ordenar_por:
            encoded_query = f"{encoded_query}^{ordenar_por}" if encoded_query else ordenar_por
        else:
            encoded_query = f"{encoded_query}^ORDERBYDESC{ordenar_por}" if encoded_query else f"ORDERBYDESC{ordenar_por}"

    params: Dict[str, Any] = {
        "sysparm_limit": min(limite, 100),
        "sysparm_query": encoded_query,
    }
    if campos:
        params["sysparm_fields"] = campos
    if incluir_display_value:
        params["sysparm_display_value"] = "true"

    try:
        response = await sn_client.request("GET", f"/api/now/table/{tabela}", params=params)
        if response.status_code == 200:
            res = response.json().get("result", [])
            return {"status": "sucesso", "tabela": tabela, "total_retornado": len(res), "dados": res}
        return _format_error(response.status_code, response.text)
    except Exception as e:
        return {"status": "erro", "mensagem": f"Erro de conexão: {str(e)}"}


@mcp.tool()
async def servicenow_obter_registro_por_id(
    tabela: str,
    sys_id: str,
    campos: Optional[str] = "",
    incluir_display_value: bool = False
) -> Dict[str, Any]:
    """Busca os detalhes de um registro específico pelo seu sys_id único."""
    params: Dict[str, Any] = {}
    if campos:
        params["sysparm_fields"] = campos
    if incluir_display_value:
        params["sysparm_display_value"] = "true"

    try:
        response = await sn_client.request("GET", f"/api/now/table/{tabela}/{sys_id}", params=params)
        if response.status_code == 200:
            return {"status": "sucesso", "tabela": tabela, "sys_id": sys_id, "registro": response.json().get("result", {})}
        return _format_error(response.status_code, response.text)
    except Exception as e:
        return {"status": "erro", "mensagem": f"Erro de conexão: {str(e)}"}


@mcp.tool()
async def servicenow_criar_registro(
    tabela: str,
    dados_json: Dict[str, Any]
) -> Dict[str, Any]:
    """Cria um novo registro em qualquer tabela do ServiceNow."""
    try:
        response = await sn_client.request("POST", f"/api/now/table/{tabela}", json_data=dados_json)
        if response.status_code in (200, 201):
            res = response.json().get("result", {})
            return {"status": "criado", "tabela": tabela, "sys_id": res.get("sys_id"), "numero": res.get("number"), "registro": res}
        return _format_error(response.status_code, response.text)
    except Exception as e:
        return {"status": "erro", "mensagem": f"Erro de conexão: {str(e)}"}


@mcp.tool()
async def servicenow_atualizar_registro(
    tabela: str,
    sys_id: str,
    dados_json: Dict[str, Any]
) -> Dict[str, Any]:
    """Atualiza campos de um registro existente via PATCH."""
    try:
        response = await sn_client.request("PATCH", f"/api/now/table/{tabela}/{sys_id}", json_data=dados_json)
        if response.status_code == 200:
            res = response.json().get("result", {})
            return {"status": "atualizado", "tabela": tabela, "sys_id": sys_id, "registro": res}
        return _format_error(response.status_code, response.text)
    except Exception as e:
        return {"status": "erro", "mensagem": f"Erro de conexão: {str(e)}"}


@mcp.tool()
async def servicenow_excluir_registro(
    tabela: str,
    sys_id: str,
    confirmar: bool = False
) -> Dict[str, Any]:
    """Exclui permanentemente um registro de qualquer tabela (exige confirmar=True)."""
    if not confirmar:
        return {"status": "bloqueado", "mensagem": "Operação destrutiva requer confirmação explícita. Defina confirmar=True."}

    try:
        response = await sn_client.request("DELETE", f"/api/now/table/{tabela}/{sys_id}")
        if response.status_code in (200, 204):
            return {"status": "excluido", "tabela": tabela, "sys_id": sys_id, "mensagem": "Registro excluído com sucesso."}
        return _format_error(response.status_code, response.text)
    except Exception as e:
        return {"status": "erro", "mensagem": f"Erro de conexão: {str(e)}"}


@mcp.tool()
async def servicenow_descrever_campos_tabela(
    tabela: str,
    limite: int = 100
) -> Dict[str, Any]:
    """Inspeciona o dicionário de dados (sys_dictionary) para descobrir campos técnicos e tipos."""
    params = {
        "sysparm_query": f"name={tabela}^active=true",
        "sysparm_fields": "element,column_label,internal_type,max_length,mandatory,reference",
        "sysparm_limit": limite,
    }
    try:
        response = await sn_client.request("GET", "/api/now/table/sys_dictionary", params=params)
        if response.status_code == 200:
            campos = []
            for r in response.json().get("result", []):
                elem = r.get("element")
                if not elem:
                    continue
                tipo = r.get("internal_type")
                if isinstance(tipo, dict):
                    tipo = tipo.get("value")
                campos.append({
                    "campo_tecnico": elem,
                    "rotulo": r.get("column_label"),
                    "tipo": tipo,
                    "obrigatorio": r.get("mandatory") in ("true", True, "1"),
                    "referencia_tabela": r.get("reference")
                })
            return {"status": "sucesso", "tabela": tabela, "total_campos": len(campos), "campos": campos}
        return _format_error(response.status_code, response.text)
    except Exception as e:
        return {"status": "erro", "mensagem": f"Erro ao obter dicionário: {str(e)}"}


@mcp.tool()
async def servicenow_listar_tabelas(
    filtro_nome: Optional[str] = "",
    limite: int = 30
) -> Dict[str, Any]:
    """Lista tabelas cadastradas no ServiceNow consultando 'sys_db_object'."""
    query = "sys_update_nameISEMPTY^ORsys_update_nameISNOTEMPTY"
    if filtro_nome:
        query = f"nameLIKE{filtro_nome}^ORlabelLIKE{filtro_nome}"

    params = {
        "sysparm_query": query,
        "sysparm_fields": "name,label,super_class,is_extendable",
        "sysparm_limit": limite
    }
    try:
        response = await sn_client.request("GET", "/api/now/table/sys_db_object", params=params)
        if response.status_code == 200:
            tabelas = [{"nome": r.get("name"), "rotulo": r.get("label"), "estende": r.get("super_class")} for r in response.json().get("result", [])]
            return {"status": "sucesso", "total_retornado": len(tabelas), "tabelas": tabelas}
        return _format_error(response.status_code, response.text)
    except Exception as e:
        return {"status": "erro", "mensagem": f"Erro ao listar tabelas: {str(e)}"}


@mcp.tool()
async def servicenow_obter_estatisticas_tabela(
    tabela: str,
    query: Optional[str] = "",
    agrupar_por: Optional[str] = "",
    campo_agregado: str = "COUNT"
) -> Dict[str, Any]:
    """Executa cálculos agregados e contagens na Aggregate API (/api/now/stats/{table})."""
    params: Dict[str, Any] = {
        "sysparm_query": query or "",
        "sysparm_count": "true"
    }
    if agrupar_por:
        params["sysparm_group_by"] = agrupar_por

    try:
        response = await sn_client.request("GET", f"/api/now/stats/{tabela}", params=params)
        if response.status_code == 200:
            return {"status": "sucesso", "tabela": tabela, "agrupado_por": agrupar_por, "resultado": response.json().get("result", {})}
        return _format_error(response.status_code, response.text)
    except Exception as e:
        return {"status": "erro", "mensagem": f"Erro na Aggregate API: {str(e)}"}


# =====================================================================
# 2. GERENCIAMENTO DE INCIDENTES (INCIDENT MANAGEMENT)
# =====================================================================

@mcp.tool()
async def servicenow_criar_incidente(
    titulo: str,
    descricao: str,
    urgencia_1_a_3: str = "2",
    impacto_1_a_3: str = "2",
    categoria: Optional[str] = "Inquiry / Help",
    solicitante: Optional[str] = "",
    ativo_cmdb: Optional[str] = "",
    grupo_atribuicao: Optional[str] = ""
) -> Dict[str, Any]:
    """Cria um novo incidente no ServiceNow com prioridade, categoria e ativo impactado."""
    payload: Dict[str, Any] = {
        "short_description": titulo,
        "description": descricao,
        "urgency": str(urgencia_1_a_3),
        "impact": str(impacto_1_a_3),
        "category": categoria,
    }
    if solicitante:
        payload["caller_id"] = solicitante
    if ativo_cmdb:
        payload["cmdb_ci"] = ativo_cmdb
    if grupo_atribuicao:
        payload["assignment_group"] = grupo_atribuicao

    return await servicenow_criar_registro("incident", payload)


@mcp.tool()
async def servicenow_atualizar_incidente(
    sys_id: str,
    campos_json: Dict[str, Any]
) -> Dict[str, Any]:
    """Atualiza campos de um incidente existente no ServiceNow."""
    return await servicenow_atualizar_registro("incident", sys_id, campos_json)


@mcp.tool()
async def servicenow_adicionar_comentario(
    sys_id: str,
    comentario: str
) -> Dict[str, Any]:
    """Adiciona um comentário público ao incidente visível para o cliente/solicitante."""
    payload = {"comments": comentario}
    return await servicenow_atualizar_registro("incident", sys_id, payload)


@mcp.tool()
async def servicenow_adicionar_nota_tecnica(
    tabela: str,
    sys_id: str,
    nota_tecnica: str
) -> Dict[str, Any]:
    """Adiciona uma anotação de trabalho técnica interna ('work_notes') para a equipe."""
    payload = {"work_notes": nota_tecnica}
    return await servicenow_atualizar_registro(tabela, sys_id, payload)


@mcp.tool()
async def servicenow_resolver_incidente(
    sys_id: str,
    codigo_resolucao: str = "Solution provided",
    notas_resolucao: str = "Incidente resolvido com sucesso."
) -> Dict[str, Any]:
    """Resolve formalmente um incidente no ServiceNow alterando o estado para 'Resolved' (state=6)."""
    payload = {
        "state": "6",
        "close_code": codigo_resolucao,
        "close_notes": notas_resolucao
    }
    return await servicenow_atualizar_registro("incident", sys_id, payload)


@mcp.tool()
async def servicenow_listar_incidentes(
    filtro_query: Optional[str] = "",
    limite: int = 20,
    apenas_ativos: bool = True
) -> Dict[str, Any]:
    """Lista incidentes no ServiceNow com opções de filtros codificados e ordenação."""
    query = filtro_query or ""
    if apenas_ativos:
        query = f"active=true^{query}" if query else "active=true"

    campos = "number,short_description,priority,state,urgency,category,assignment_group,assigned_to,sys_created_on"
    return await servicenow_consultar_tabela("incident", query=query, limite=limite, campos=campos, incluir_display_value=True)


@mcp.tool()
async def servicenow_abrir_incidente_seguranca(
    titulo: str,
    descricao: str,
    severidade_1_a_3: str = "1",
    ip_ou_host_afetado: str = "",
    categoria: str = "inquiry",
    subcategoria: str = "",
    caller_id: Optional[str] = ""
) -> Dict[str, Any]:
    """Abre um incidente de segurança formal de alta prioridade (P1) com detalhes de ameaça e IoCs."""
    corpo_desc = descricao
    if ip_ou_host_afetado:
        corpo_desc = f"{descricao}\n\n[SOAR / SOC INTEL]\nAtivo/IP Afetado: {ip_ou_host_afetado}"

    payload = {
        "short_description": titulo,
        "description": corpo_desc,
        "urgency": str(severidade_1_a_3),
        "impact": str(severidade_1_a_3),
        "category": categoria,
        "contact_type": "email"
    }
    if subcategoria:
        payload["subcategory"] = subcategoria
    if caller_id:
        payload["caller_id"] = caller_id

    return await servicenow_criar_registro("incident", payload)


@mcp.tool()
async def servicenow_fechar_incidente(
    sys_id: str,
    codigo_resolucao: str = "Solution provided",
    notas_resolucao: str = "Incidente mitigado e encerrado pelo SOAR Agent."
) -> Dict[str, Any]:
    """Alias compatível para fechamento/resolução de incidentes."""
    return await servicenow_resolver_incidente(sys_id, codigo_resolucao, notas_resolucao)


# =====================================================================
# 3. CATÁLOGO DE SERVIÇOS (SERVICE CATALOG)
# =====================================================================

@mcp.tool()
async def servicenow_listar_itens_catalogo(
    filtro_termo: Optional[str] = "",
    categoria_sys_id: Optional[str] = "",
    limite: int = 20
) -> Dict[str, Any]:
    """Lista itens do catálogo de serviços do ServiceNow (tabela sc_cat_item)."""
    query = "active=true"
    if filtro_termo:
        query += f"^nameLIKE{filtro_termo}^ORshort_descriptionLIKE{filtro_termo}"
    if categoria_sys_id:
        query += f"^category={categoria_sys_id}"

    campos = "sys_id,name,short_description,price,category,sc_catalogs"
    return await servicenow_consultar_tabela("sc_cat_item", query=query, limite=limite, campos=campos, incluir_display_value=True)


@mcp.tool()
async def servicenow_obter_item_catalogo(
    sys_id: str
) -> Dict[str, Any]:
    """Obtém detalhes completos de um item de catálogo de serviços específico por sys_id."""
    return await servicenow_obter_registro_por_id("sc_cat_item", sys_id, incluir_display_value=True)


@mcp.tool()
async def servicenow_atualizar_item_catalogo(
    sys_id: str,
    dados_json: Dict[str, Any]
) -> Dict[str, Any]:
    """Atualiza propriedades de um item do catálogo de serviços (preço, descrição, disponibilidade)."""
    return await servicenow_atualizar_registro("sc_cat_item", sys_id, dados_json)


@mcp.tool()
async def servicenow_listar_categorias_catalogo(
    catalogo_sys_id: Optional[str] = "",
    limite: int = 30
) -> Dict[str, Any]:
    """Lista categorias de itens do catálogo de serviços (tabela sc_category)."""
    query = "active=true"
    if catalogo_sys_id:
        query += f"^sc_catalog={catalogo_sys_id}"

    campos = "sys_id,title,description,parent,sc_catalog"
    return await servicenow_consultar_tabela("sc_category", query=query, limite=limite, campos=campos, incluir_display_value=True)


@mcp.tool()
async def servicenow_criar_categoria_catalogo(
    titulo: str,
    descricao: str = "",
    catalogo_sys_id: str = "",
    categoria_pai_sys_id: str = ""
) -> Dict[str, Any]:
    """Cria uma nova categoria no catálogo de serviços (sc_category)."""
    payload = {"title": titulo, "description": descricao}
    if catalogo_sys_id:
        payload["sc_catalog"] = catalogo_sys_id
    if categoria_pai_sys_id:
        payload["parent"] = categoria_pai_sys_id

    return await servicenow_criar_registro("sc_category", payload)


@mcp.tool()
async def servicenow_atualizar_categoria_catalogo(
    sys_id: str,
    dados_json: Dict[str, Any]
) -> Dict[str, Any]:
    """Atualiza uma categoria existente do catálogo de serviços."""
    return await servicenow_atualizar_registro("sc_category", sys_id, dados_json)


@mcp.tool()
async def servicenow_mover_item_catalogo(
    item_sys_id: str,
    nova_categoria_sys_id: str
) -> Dict[str, Any]:
    """Move um item do catálogo de serviços para uma nova categoria."""
    return await servicenow_atualizar_registro("sc_cat_item", item_sys_id, {"category": nova_categoria_sys_id})


@mcp.tool()
async def servicenow_criar_variavel_item_catalogo(
    item_catalogo_sys_id: str,
    nome_tecnico: str,
    rotulo_pergunta: str,
    tipo_campo: int = 6,
    obrigatorio: bool = False
) -> Dict[str, Any]:
    """Cria uma nova variável/pergunta de formulário para um item de catálogo (tabela item_option_new)."""
    payload = {
        "cat_item": item_catalogo_sys_id,
        "name": nome_tecnico,
        "question_text": rotulo_pergunta,
        "type": str(tipo_campo),  # 6=Single Line Text, 2=Multi-line, 1=Yes/No, 8=Reference
        "mandatory": "true" if obrigatorio else "false"
    }
    return await servicenow_criar_registro("item_option_new", payload)


@mcp.tool()
async def servicenow_listar_variaveis_item_catalogo(
    item_catalogo_sys_id: str
) -> Dict[str, Any]:
    """Lista todas as variáveis (perguntas/campos) associadas a um item de catálogo."""
    query = f"cat_item={item_catalogo_sys_id}"
    campos = "sys_id,name,question_text,type,mandatory,order"
    return await servicenow_consultar_tabela("item_option_new", query=query, campos=campos, incluir_display_value=True)


@mcp.tool()
async def servicenow_atualizar_variavel_item_catalogo(
    variavel_sys_id: str,
    dados_json: Dict[str, Any]
) -> Dict[str, Any]:
    """Atualiza uma variável existente de um item de catálogo (item_option_new)."""
    return await servicenow_atualizar_registro("item_option_new", variavel_sys_id, dados_json)


@mcp.tool()
async def servicenow_listar_catalogos(
    limite: int = 10
) -> Dict[str, Any]:
    """Lista catálogos de serviços cadastrados (tabela sc_catalog)."""
    campos = "sys_id,title,description,active"
    return await servicenow_consultar_tabela("sc_catalog", query="active=true", limite=limite, campos=campos)


@mcp.tool()
async def servicenow_obter_recomendacoes_otimizacao_catalogo() -> Dict[str, Any]:
    """Analisa o catálogo de serviços identificando itens sem categoria, inativos ou sem descrição."""
    itens_sem_desc = await servicenow_consultar_tabela("sc_cat_item", query="active=true^short_descriptionISEMPTY", limite=15, campos="sys_id,name")
    itens_sem_cat = await servicenow_consultar_tabela("sc_cat_item", query="active=true^categoryISEMPTY", limite=15, campos="sys_id,name")

    return {
        "status": "analise_concluida",
        "total_itens_sem_descricao": itens_sem_desc.get("total_retornado", 0),
        "itens_sem_descricao": itens_sem_desc.get("dados", []),
        "total_itens_sem_categoria": itens_sem_cat.get("total_retornado", 0),
        "itens_sem_categoria": itens_sem_cat.get("dados", []),
        "recomendacoes": [
            "Preencher short_description para melhorar descoberta na busca por linguagem natural",
            "Associar categorias ativas aos itens órfãos para exibição no portal corporativo",
            "Garantir variáveis de formulário claras para evitar retrabalho operacional"
        ]
    }


# =====================================================================
# 4. GESTÃO DE MUDANÇAS E APROVAÇÕES (CHANGE MANAGEMENT & TASKS)
# =====================================================================

@mcp.tool()
async def servicenow_criar_solicitacao_mudanca(
    titulo: str,
    descricao: str,
    tipo: str = "normal",
    risco: str = "moderate",
    justificativa: str = "",
    plano_implementacao: str = "",
    plano_rollback: str = "",
    ativo_afetado: str = ""
) -> Dict[str, Any]:
    """Cria uma nova solicitação de mudança (GMUD / change_request)."""
    risk_map = {"very_high": "1", "high": "2", "moderate": "3", "low": "4"}
    payload = {
        "short_description": titulo,
        "description": f"{descricao}\n\nAtivo Impactado: {ativo_afetado}" if ativo_afetado else descricao,
        "type": tipo.lower(),
        "risk": risk_map.get(risco.lower(), "3"),
        "justification": justificativa,
        "implementation_plan": plano_implementacao,
        "backout_plan": plano_rollback,
        "category": "Network"
    }
    return await servicenow_criar_registro("change_request", payload)


@mcp.tool()
async def servicenow_atualizar_solicitacao_mudanca(
    sys_id: str,
    dados_json: Dict[str, Any]
) -> Dict[str, Any]:
    """Atualiza uma solicitação de mudança existente no ServiceNow."""
    return await servicenow_atualizar_registro("change_request", sys_id, dados_json)


@mcp.tool()
async def servicenow_listar_solicitacoes_mudanca(
    filtro_query: Optional[str] = "",
    limite: int = 20
) -> Dict[str, Any]:
    """Lista solicitações de mudança (change_request) com opções de filtros."""
    campos = "number,short_description,type,state,risk,priority,category,assigned_to,assignment_group,sys_created_on"
    return await servicenow_consultar_tabela("change_request", query=filtro_query or "", limite=limite, campos=campos, incluir_display_value=True)


@mcp.tool()
async def servicenow_obter_detalhes_mudanca(
    sys_id_ou_numero: str
) -> Dict[str, Any]:
    """Obtém detalhes completos de uma solicitação de mudança específica por sys_id ou número (ex: CHG0040007)."""
    if sys_id_ou_numero.startswith("CHG"):
        res = await servicenow_consultar_tabela("change_request", query=f"number={sys_id_ou_numero}", limite=1, incluir_display_value=True)
        dados = res.get("dados", [])
        if dados:
            return {"status": "sucesso", "mudanca": dados[0]}
        return {"status": "erro", "mensagem": f"Mudança {sys_id_ou_numero} não encontrada."}
    return await servicenow_obter_registro_por_id("change_request", sys_id_ou_numero, incluir_display_value=True)


@mcp.tool()
async def servicenow_adicionar_tarefa_mudanca(
    mudanca_sys_id: str,
    titulo_tarefa: str,
    descricao_tarefa: str = "",
    grupo_atribuicao: str = ""
) -> Dict[str, Any]:
    """Adiciona uma tarefa de execução técnica a uma solicitação de mudança (tabela change_task)."""
    payload = {
        "change_request": mudanca_sys_id,
        "short_description": titulo_tarefa,
        "description": descricao_tarefa,
    }
    if grupo_atribuicao:
        payload["assignment_group"] = grupo_atribuicao

    return await servicenow_criar_registro("change_task", payload)


@mcp.tool()
async def servicenow_enviar_mudanca_aprovacao(
    mudanca_sys_id: str
) -> Dict[str, Any]:
    """Envia uma solicitação de mudança para o estado de aprovação ('Authorize' / state=-4)."""
    payload = {"state": "-4", "work_notes": "Solicitação de mudança submetida para aprovação formal."}
    return await servicenow_atualizar_registro("change_request", mudanca_sys_id, payload)


@mcp.tool()
async def servicenow_aprovar_mudanca(
    mudanca_sys_id: str,
    comentario_aprovacao: str = "Aprovado pelo Agente SOAR / Auditoria."
) -> Dict[str, Any]:
    """Aprova formalmente uma requisição de mudança na tabela 'sysapproval_approver'."""
    # Localiza o registro de aprovação pendente para esta mudança
    query = f"sysapproval={mudanca_sys_id}^state=requested"
    aprovacoes = await servicenow_consultar_tabela("sysapproval_approver", query=query, limite=5)
    dados = aprovacoes.get("dados", [])
    if not dados:
        # Fallback: atualiza approval diretamente na change_request
        return await servicenow_atualizar_registro("change_request", mudanca_sys_id, {
            "approval": "approved",
            "work_notes": f"[APROVAÇÃO] {comentario_aprovacao}"
        })

    resultados = []
    for ap in dados:
        r = await servicenow_atualizar_registro("sysapproval_approver", ap.get("sys_id"), {
            "state": "approved",
            "comments": comentario_aprovacao
        })
        resultados.append(r)

    return {"status": "aprovado", "total_aprovacoes": len(resultados), "detalhes": resultados}


@mcp.tool()
async def servicenow_rejeitar_mudanca(
    mudanca_sys_id: str,
    motivo_rejeicao: str
) -> Dict[str, Any]:
    """Rejeita formalmente uma requisição de mudança na tabela 'sysapproval_approver'."""
    query = f"sysapproval={mudanca_sys_id}^state=requested"
    aprovacoes = await servicenow_consultar_tabela("sysapproval_approver", query=query, limite=5)
    dados = aprovacoes.get("dados", [])
    if not dados:
        return await servicenow_atualizar_registro("change_request", mudanca_sys_id, {
            "approval": "rejected",
            "work_notes": f"[REJEIÇÃO] {motivo_rejeicao}"
        })

    resultados = []
    for ap in dados:
        r = await servicenow_atualizar_registro("sysapproval_approver", ap.get("sys_id"), {
            "state": "rejected",
            "comments": motivo_rejeicao
        })
        resultados.append(r)

    return {"status": "rejeitado", "total_rejeicoes": len(resultados), "detalhes": resultados}


@mcp.tool()
async def servicenow_criar_gmud(
    titulo: str,
    descricao: str,
    tipo_mudanca: str = "normal",
    justificativa: str = "",
    plano_implementacao: str = "",
    plano_rollback: str = "",
    ativo_afetado: str = "",
    risco: str = "moderate"
) -> Dict[str, Any]:
    """Alias direto para criar_solicitacao_mudanca."""
    return await servicenow_criar_solicitacao_mudanca(
        titulo=titulo,
        descricao=descricao,
        tipo=tipo_mudanca,
        risco=risco,
        justificativa=justificativa,
        plano_implementacao=plano_implementacao,
        plano_rollback=plano_rollback,
        ativo_afetado=ativo_afetado
    )


# =====================================================================
# 5. GESTÃO ÁGIL E PROJETOS (AGILE 2.0 / SCRUM & PROJECTS)
# =====================================================================

@mcp.tool()
async def servicenow_criar_historia(
    titulo: str,
    descricao: str,
    pontos_historia: int = 3,
    epico_sys_id: Optional[str] = "",
    atribuido_a: Optional[str] = "",
    prioridade: str = "3"
) -> Dict[str, Any]:
    """Cria uma nova história de usuário (User Story) na tabela 'rm_story'."""
    payload: Dict[str, Any] = {
        "short_description": titulo,
        "description": descricao,
        "story_points": str(pontos_historia),
        "priority": prioridade
    }
    if epico_sys_id:
        payload["epic"] = epico_sys_id
    if atribuido_a:
        payload["assigned_to"] = atribuido_a

    return await servicenow_criar_registro("rm_story", payload)


@mcp.tool()
async def servicenow_atualizar_historia(
    sys_id: str,
    dados_json: Dict[str, Any]
) -> Dict[str, Any]:
    """Atualiza campos de uma história de usuário existente (rm_story)."""
    return await servicenow_atualizar_registro("rm_story", sys_id, dados_json)


@mcp.tool()
async def servicenow_listar_historias(
    filtro_query: Optional[str] = "",
    limite: int = 20
) -> Dict[str, Any]:
    """Lista histórias de usuário no ServiceNow com opções de filtros."""
    campos = "number,short_description,story_points,state,priority,epic,assigned_to,sys_created_on"
    return await servicenow_consultar_tabela("rm_story", query=filtro_query or "", limite=limite, campos=campos, incluir_display_value=True)


@mcp.tool()
async def servicenow_criar_dependencia_historia(
    historia_sucessora_sys_id: str,
    historia_predecessora_sys_id: str
) -> Dict[str, Any]:
    """Cria uma dependência entre duas histórias de usuário (rm_story_dependency)."""
    payload = {
        "story": historia_sucessora_sys_id,
        "prerequisite_story": historia_predecessora_sys_id
    }
    return await servicenow_criar_registro("rm_story_dependency", payload)


@mcp.tool()
async def servicenow_excluir_dependencia_historia(
    dependencia_sys_id: str,
    confirmar: bool = True
) -> Dict[str, Any]:
    """Exclui uma dependência entre histórias de usuário."""
    return await servicenow_excluir_registro("rm_story_dependency", dependencia_sys_id, confirmar=confirmar)


@mcp.tool()
async def servicenow_criar_epico(
    titulo: str,
    descricao: str = "",
    projeto_sys_id: str = ""
) -> Dict[str, Any]:
    """Cria um novo Épico na tabela 'rm_epic' do Agile Development."""
    payload = {"short_description": titulo, "description": descricao}
    if projeto_sys_id:
        payload["project"] = projeto_sys_id
    return await servicenow_criar_registro("rm_epic", payload)


@mcp.tool()
async def servicenow_atualizar_epico(
    sys_id: str,
    dados_json: Dict[str, Any]
) -> Dict[str, Any]:
    """Atualiza um Épico existente no ServiceNow (rm_epic)."""
    return await servicenow_atualizar_registro("rm_epic", sys_id, dados_json)


@mcp.tool()
async def servicenow_listar_epicos(
    limite: int = 15
) -> Dict[str, Any]:
    """Lista Épicos cadastrados na tabela 'rm_epic'."""
    campos = "number,short_description,state,priority,project,sys_created_on"
    return await servicenow_consultar_tabela("rm_epic", limite=limite, campos=campos, incluir_display_value=True)


@mcp.tool()
async def servicenow_criar_tarefa_scrum(
    historia_sys_id: str,
    titulo: str,
    tipo_tarefa: str = "Development",
    horas_estimadas: float = 4.0
) -> Dict[str, Any]:
    """Cria uma tarefa Scrum vinculada a uma história de usuário (tabela rm_scrum_task)."""
    payload = {
        "story": historia_sys_id,
        "short_description": titulo,
        "type": tipo_tarefa,
        "planned_hours": str(horas_estimadas)
    }
    return await servicenow_criar_registro("rm_scrum_task", payload)


@mcp.tool()
async def servicenow_atualizar_tarefa_scrum(
    sys_id: str,
    dados_json: Dict[str, Any]
) -> Dict[str, Any]:
    """Atualiza o estado ou horas de uma tarefa scrum (rm_scrum_task)."""
    return await servicenow_atualizar_registro("rm_scrum_task", sys_id, dados_json)


@mcp.tool()
async def servicenow_listar_tarefas_scrum(
    historia_sys_id: Optional[str] = "",
    limite: int = 20
) -> Dict[str, Any]:
    """Lista tarefas scrum com opção de filtrar por história pai."""
    query = f"story={historia_sys_id}" if historia_sys_id else ""
    campos = "number,short_description,type,state,planned_hours,assigned_to"
    return await servicenow_consultar_tabela("rm_scrum_task", query=query, limite=limite, campos=campos, incluir_display_value=True)


@mcp.tool()
async def servicenow_criar_projeto(
    nome_projeto: str,
    descricao: str = "",
    gerente_sys_id: str = "",
    prioridade: str = "3"
) -> Dict[str, Any]:
    """Cria um novo projeto formal no ServiceNow (tabela pm_project)."""
    payload = {
        "short_description": nome_projeto,
        "description": descricao,
        "priority": prioridade
    }
    if gerente_sys_id:
        payload["project_manager"] = gerente_sys_id
    return await servicenow_criar_registro("pm_project", payload)


@mcp.tool()
async def servicenow_atualizar_projeto(
    sys_id: str,
    dados_json: Dict[str, Any]
) -> Dict[str, Any]:
    """Atualiza dados e status de um projeto existente (pm_project)."""
    return await servicenow_atualizar_registro("pm_project", sys_id, dados_json)


@mcp.tool()
async def servicenow_listar_projetos(
    limite: int = 15
) -> Dict[str, Any]:
    """Lista projetos cadastrados na tabela 'pm_project'."""
    campos = "number,short_description,status,percent_complete,project_manager,phase,priority"
    return await servicenow_consultar_tabela("pm_project", limite=limite, campos=campos, incluir_display_value=True)


# =====================================================================
# 6. FLUXOS DE TRABALHO & SCRIPTS (WORKFLOWS & SCRIPT INCLUDES)
# =====================================================================

@mcp.tool()
async def servicenow_listar_fluxos_trabalho(
    filtro_nome: Optional[str] = "",
    limite: int = 20
) -> Dict[str, Any]:
    """Lista fluxos de trabalho tradicionais cadastrados em 'wf_workflow'."""
    query = f"nameLIKE{filtro_nome}" if filtro_nome else ""
    campos = "sys_id,name,description,table,sys_created_on"
    return await servicenow_consultar_tabela("wf_workflow", query=query, limite=limite, campos=campos)


@mcp.tool()
async def servicenow_obter_fluxo_trabalho(
    sys_id: str
) -> Dict[str, Any]:
    """Obtém detalhes de um fluxo de trabalho específico em 'wf_workflow'."""
    return await servicenow_obter_registro_por_id("wf_workflow", sys_id)


@mcp.tool()
async def servicenow_criar_fluxo_trabalho(
    nome: str,
    tabela_alvo: str,
    descricao: str = ""
) -> Dict[str, Any]:
    """Cria uma definição de fluxo de trabalho na tabela 'wf_workflow'."""
    payload = {"name": nome, "table": tabela_alvo, "description": descricao}
    return await servicenow_criar_registro("wf_workflow", payload)


@mcp.tool()
async def servicenow_atualizar_fluxo_trabalho(
    sys_id: str,
    dados_json: Dict[str, Any]
) -> Dict[str, Any]:
    """Atualiza propriedades de um fluxo de trabalho."""
    return await servicenow_atualizar_registro("wf_workflow", sys_id, dados_json)


@mcp.tool()
async def servicenow_excluir_fluxo_trabalho(
    sys_id: str,
    confirmar: bool = False
) -> Dict[str, Any]:
    """Exclui um fluxo de trabalho da tabela 'wf_workflow' (exige confirmar=True)."""
    return await servicenow_excluir_registro("wf_workflow", sys_id, confirmar=confirmar)


@mcp.tool()
async def servicenow_listar_script_includes(
    filtro_nome: Optional[str] = "",
    limite: int = 20
) -> Dict[str, Any]:
    """Lista Script Includes de desenvolvedor no ServiceNow (tabela sys_script_include)."""
    query = "active=true"
    if filtro_nome:
        query += f"^nameLIKE{filtro_nome}^ORapi_nameLIKE{filtro_nome}"

    campos = "sys_id,name,api_name,client_callable,access,sys_scope"
    return await servicenow_consultar_tabela("sys_script_include", query=query, limite=limite, campos=campos)


@mcp.tool()
async def servicenow_obter_script_include(
    sys_id: str
) -> Dict[str, Any]:
    """Obtém o código JavaScript e configurações de um Script Include específico (sys_script_include)."""
    campos = "sys_id,name,api_name,script,description,client_callable,access"
    return await servicenow_obter_registro_por_id("sys_script_include", sys_id, campos=campos)


@mcp.tool()
async def servicenow_criar_script_include(
    nome: str,
    codigo_javascript: str,
    descricao: str = "",
    chamavel_pelo_cliente: bool = False
) -> Dict[str, Any]:
    """Cria um novo Script Include com código JavaScript no ServiceNow (sys_script_include)."""
    payload = {
        "name": nome,
        "script": codigo_javascript,
        "description": descricao,
        "client_callable": "true" if chamavel_pelo_cliente else "false",
        "active": "true",
        "access": "package_private"
    }
    return await servicenow_criar_registro("sys_script_include", payload)


@mcp.tool()
async def servicenow_atualizar_script_include(
    sys_id: str,
    codigo_javascript: Optional[str] = None,
    dados_json: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """Atualiza o código ou configurações de um Script Include existente."""
    payload = dados_json or {}
    if codigo_javascript is not None:
        payload["script"] = codigo_javascript

    return await servicenow_atualizar_registro("sys_script_include", sys_id, payload)


@mcp.tool()
async def servicenow_excluir_script_include(
    sys_id: str,
    confirmar: bool = False
) -> Dict[str, Any]:
    """Exclui um Script Include da instância (exige confirmar=True)."""
    return await servicenow_excluir_registro("sys_script_include", sys_id, confirmar=confirmar)


# =====================================================================
# 7. CONJUNTOS DE ALTERAÇÕES (UPDATE SETS / CHANGESETS)
# =====================================================================

@mcp.tool()
async def servicenow_listar_conjuntos_alteracoes(
    filtro_nome: Optional[str] = "",
    limite: int = 15
) -> Dict[str, Any]:
    """Lista Update Sets / Conjuntos de Alterações no ServiceNow (tabela sys_update_set)."""
    query = f"nameLIKE{filtro_nome}" if filtro_nome else ""
    campos = "sys_id,name,state,is_default,release_date,sys_created_by,sys_created_on"
    return await servicenow_consultar_tabela("sys_update_set", query=query, limite=limite, campos=campos)


@mcp.tool()
async def servicenow_obter_detalhes_conjunto_alteracoes(
    sys_id: str
) -> Dict[str, Any]:
    """Obtém os detalhes e arquivos XML contidos em um Update Set (sys_update_set)."""
    update_set = await servicenow_obter_registro_por_id("sys_update_set", sys_id)
    arquivos = await servicenow_consultar_tabela("sys_update_xml", query=f"update_set={sys_id}", limite=30, campos="sys_id,name,type,target_name,action")

    return {
        "status": "sucesso",
        "update_set": update_set.get("registro", {}),
        "total_alteracoes": arquivos.get("total_retornado", 0),
        "alteracoes": arquivos.get("dados", [])
    }


@mcp.tool()
async def servicenow_criar_conjunto_alteracoes(
    nome: str,
    descricao: str = ""
) -> Dict[str, Any]:
    """Cria um novo Update Set em estado 'in progress' (sys_update_set)."""
    payload = {
        "name": nome,
        "description": descricao,
        "state": "in progress"
    }
    return await servicenow_criar_registro("sys_update_set", payload)


@mcp.tool()
async def servicenow_atualizar_conjunto_alteracoes(
    sys_id: str,
    dados_json: Dict[str, Any]
) -> Dict[str, Any]:
    """Atualiza o estado ou nome de um Update Set (ex: mudar state para 'complete')."""
    return await servicenow_atualizar_registro("sys_update_set", sys_id, dados_json)


@mcp.tool()
async def servicenow_confirmar_conjunto_alteracoes(
    sys_id: str
) -> Dict[str, Any]:
    """Marca um Update Set como concluído ('complete') pronto para exportação/deploy."""
    return await servicenow_atualizar_registro("sys_update_set", sys_id, {"state": "complete"})


@mcp.tool()
async def servicenow_publicar_conjunto_alteracoes(
    sys_id: str
) -> Dict[str, Any]:
    """Publica ou exporta o Update Set marcando-o como concluído."""
    return await servicenow_confirmar_conjunto_alteracoes(sys_id)


@mcp.tool()
async def servicenow_adicionar_arquivo_conjunto_alteracoes(
    update_set_sys_id: str,
    nome_registro: str,
    tipo: str,
    payload_xml: str
) -> Dict[str, Any]:
    """Registra uma alteração XML dentro de um Update Set (tabela sys_update_xml)."""
    payload = {
        "update_set": update_set_sys_id,
        "name": nome_registro,
        "type": tipo,
        "payload": payload_xml,
        "action": "INSERT_OR_UPDATE"
    }
    return await servicenow_criar_registro("sys_update_xml", payload)


# =====================================================================
# 8. BASE DE CONHECIMENTO (KNOWLEDGE BASE EXPANDIDA)
# =====================================================================

@mcp.tool()
async def servicenow_criar_base_conhecimento(
    titulo: str,
    descricao: str = ""
) -> Dict[str, Any]:
    """Cria uma nova Base de Conhecimento (tabela kb_knowledge_base)."""
    payload = {"title": titulo, "description": descricao}
    return await servicenow_criar_registro("kb_knowledge_base", payload)


@mcp.tool()
async def servicenow_listar_bases_conhecimento(
    limite: int = 10
) -> Dict[str, Any]:
    """Lista as Bases de Conhecimento disponíveis no ServiceNow (kb_knowledge_base)."""
    campos = "sys_id,title,description,active"
    return await servicenow_consultar_tabela("kb_knowledge_base", query="active=true", limite=limite, campos=campos)


@mcp.tool()
async def servicenow_criar_categoria_conhecimento(
    base_conhecimento_sys_id: str,
    rotulo_categoria: str
) -> Dict[str, Any]:
    """Cria uma categoria em uma Base de Conhecimento (tabela kb_category)."""
    payload = {
        "parent_table": "kb_knowledge_base",
        "parent_id": base_conhecimento_sys_id,
        "label": rotulo_categoria
    }
    return await servicenow_criar_registro("kb_category", payload)


@mcp.tool()
async def servicenow_criar_artigo_conhecimento(
    titulo: str,
    conteudo_html: str,
    base_conhecimento_sys_id: Optional[str] = "",
    topico: Optional[str] = "General"
) -> Dict[str, Any]:
    """Cria um novo artigo na Base de Conhecimento (tabela kb_knowledge)."""
    payload: Dict[str, Any] = {
        "short_description": titulo,
        "text": conteudo_html,
        "topic": topico,
        "workflow_state": "draft"
    }
    if base_conhecimento_sys_id:
        payload["kb_knowledge_base"] = base_conhecimento_sys_id

    return await servicenow_criar_registro("kb_knowledge", payload)


@mcp.tool()
async def servicenow_atualizar_artigo_conhecimento(
    sys_id: str,
    dados_json: Dict[str, Any]
) -> Dict[str, Any]:
    """Atualiza o texto ou metadados de um artigo da Base de Conhecimento."""
    return await servicenow_atualizar_registro("kb_knowledge", sys_id, dados_json)


@mcp.tool()
async def servicenow_publicar_artigo_conhecimento(
    sys_id: str
) -> Dict[str, Any]:
    """Publica formalmente um artigo de conhecimento (workflow_state='published')."""
    return await servicenow_atualizar_registro("kb_knowledge", sys_id, {"workflow_state": "published"})


@mcp.tool()
async def servicenow_listar_artigos_conhecimento(
    termo_busca: Optional[str] = "",
    apenas_publicados: bool = True,
    limite: int = 15
) -> Dict[str, Any]:
    """Lista artigos da base de conhecimento com opções de filtragem."""
    query = "workflow_state=published" if apenas_publicados else ""
    if termo_busca:
        termo_filter = f"short_descriptionLIKE{termo_busca}^ORtextLIKE{termo_busca}"
        query = f"{query}^{termo_filter}" if query else termo_filter

    campos = "number,short_description,topic,category,author,sys_view_count,workflow_state"
    return await servicenow_consultar_tabela("kb_knowledge", query=query, limite=limite, campos=campos, incluir_display_value=True)


@mcp.tool()
async def servicenow_obter_artigo_conhecimento(
    sys_id_ou_numero: str
) -> Dict[str, Any]:
    """Obtém o conteúdo completo de um artigo de conhecimento por sys_id ou número (ex: KB0000008)."""
    if sys_id_ou_numero.startswith("KB"):
        res = await servicenow_consultar_tabela("kb_knowledge", query=f"number={sys_id_ou_numero}", limite=1, incluir_display_value=True)
        dados = res.get("dados", [])
        if dados:
            return {"status": "sucesso", "artigo": dados[0]}
        return {"status": "erro", "mensagem": f"Artigo {sys_id_ou_numero} não encontrado."}

    return await servicenow_obter_registro_por_id("kb_knowledge", sys_id_ou_numero, incluir_display_value=True)


@mcp.tool()
async def servicenow_consultar_base_conhecimento(
    termo_busca: str,
    limite: int = 5
) -> Dict[str, Any]:
    """Alias compatível para pesquisar artigos na base de conhecimento."""
    return await servicenow_listar_artigos_conhecimento(termo_busca=termo_busca, limite=limite)


# =====================================================================
# 9. USUÁRIOS, GRUPOS E MEMBROS (IDENTITY & MEMBERSHIP)
# =====================================================================

@mcp.tool()
async def servicenow_criar_usuario(
    login: str,
    nome_completo: str,
    email: str,
    cargo: str = "",
    departamento: str = ""
) -> Dict[str, Any]:
    """Cria um novo usuário na tabela 'sys_user'."""
    payload = {
        "user_name": login,
        "name": nome_completo,
        "email": email,
        "title": cargo,
        "department": departamento,
        "active": "true"
    }
    return await servicenow_criar_registro("sys_user", payload)


@mcp.tool()
async def servicenow_atualizar_usuario(
    sys_id: str,
    dados_json: Dict[str, Any]
) -> Dict[str, Any]:
    """Atualiza campos de um usuário existente na tabela 'sys_user'."""
    return await servicenow_atualizar_registro("sys_user", sys_id, dados_json)


@mcp.tool()
async def servicenow_obter_usuario(
    login_ou_email_ou_sys_id: str
) -> Dict[str, Any]:
    """Obtém detalhes de um usuário por login (user_name), e-mail ou sys_id."""
    if len(login_ou_email_ou_sys_id) == 32 and re.match(r'^[0-9a-fA-F]{32}$', login_ou_email_ou_sys_id):
        return await servicenow_obter_registro_por_id("sys_user", login_ou_email_ou_sys_id, incluir_display_value=True)

    query = f"user_name={login_ou_email_ou_sys_id}^ORemail={login_ou_email_ou_sys_id}"
    res = await servicenow_consultar_tabela("sys_user", query=query, limite=1, incluir_display_value=True)
    dados = res.get("dados", [])
    if dados:
        return {"status": "sucesso", "usuario": dados[0]}
    return {"status": "erro", "mensagem": f"Usuário {login_ou_email_ou_sys_id} não encontrado."}


@mcp.tool()
async def servicenow_listar_usuarios(
    filtro_termo: Optional[str] = "",
    limite: int = 20
) -> Dict[str, Any]:
    """Lista usuários no ServiceNow com opções de filtros."""
    query = "active=true"
    if filtro_termo:
        query += f"^user_nameLIKE{filtro_termo}^ORnameLIKE{filtro_termo}^ORemailLIKE{filtro_termo}"

    campos = "sys_id,user_name,name,email,title,department,active"
    return await servicenow_consultar_tabela("sys_user", query=query, limite=limite, campos=campos, incluir_display_value=True)


@mcp.tool()
async def servicenow_buscar_usuario(
    termo_busca: str,
    limite: int = 10
) -> Dict[str, Any]:
    """Alias compatível para buscar usuários."""
    return await servicenow_listar_usuarios(filtro_termo=termo_busca, limite=limite)


@mcp.tool()
async def servicenow_criar_grupo(
    nome_grupo: str,
    descricao: str = "",
    email: str = "",
    gerente_sys_id: str = ""
) -> Dict[str, Any]:
    """Cria um novo grupo de suporte/atendimento na tabela 'sys_user_group'."""
    payload = {
        "name": nome_grupo,
        "description": descricao,
        "email": email,
        "active": "true"
    }
    if gerente_sys_id:
        payload["manager"] = gerente_sys_id
    return await servicenow_criar_registro("sys_user_group", payload)


@mcp.tool()
async def servicenow_atualizar_grupo(
    sys_id: str,
    dados_json: Dict[str, Any]
) -> Dict[str, Any]:
    """Atualiza dados de um grupo existente na tabela 'sys_user_group'."""
    return await servicenow_atualizar_registro("sys_user_group", sys_id, dados_json)


@mcp.tool()
async def servicenow_listar_grupos(
    filtro_nome: Optional[str] = "",
    limite: int = 20
) -> Dict[str, Any]:
    """Lista grupos de atendimento cadastrados na tabela 'sys_user_group'."""
    query = "active=true"
    if filtro_nome:
        query += f"^nameLIKE{filtro_nome}"

    campos = "sys_id,name,description,email,manager"
    return await servicenow_consultar_tabela("sys_user_group", query=query, limite=limite, campos=campos, incluir_display_value=True)


@mcp.tool()
async def servicenow_buscar_grupo(
    nome_grupo: str,
    limite: int = 10
) -> Dict[str, Any]:
    """Alias compatível para buscar grupos."""
    return await servicenow_listar_grupos(filtro_nome=nome_grupo, limite=limite)


@mcp.tool()
async def servicenow_adicionar_membros_grupo(
    grupo_sys_id: str,
    usuario_sys_id: str
) -> Dict[str, Any]:
    """Adiciona um usuário como membro de um grupo de atendimento (tabela sys_user_grmember)."""
    payload = {
        "group": grupo_sys_id,
        "user": usuario_sys_id
    }
    return await servicenow_criar_registro("sys_user_grmember", payload)


@mcp.tool()
async def servicenow_remover_membros_grupo(
    grupo_sys_id: str,
    usuario_sys_id: str
) -> Dict[str, Any]:
    """Remove a vinculação de um usuário com um grupo na tabela 'sys_user_grmember'."""
    query = f"group={grupo_sys_id}^user={usuario_sys_id}"
    membros = await servicenow_consultar_tabela("sys_user_grmember", query=query, limite=5)
    dados = membros.get("dados", [])
    if not dados:
        return {"status": "erro", "mensagem": "Vínculo de membro não encontrado entre este usuário e grupo."}

    removidos = []
    for m in dados:
        r = await servicenow_excluir_registro("sys_user_grmember", m.get("sys_id"), confirmar=True)
        removidos.append(r)

    return {"status": "sucesso", "remocoes": removidos}


@mcp.tool()
async def servicenow_atribuir_chamado(
    tabela: str,
    sys_id: str,
    grupo_ou_sys_id: Optional[str] = None,
    analista_ou_sys_id: Optional[str] = None,
    nota_atribuicao: Optional[str] = None
) -> Dict[str, Any]:
    """Atribui automaticamente um chamado a um grupo e/ou analista específico."""
    payload: Dict[str, Any] = {}

    if grupo_ou_sys_id:
        if len(grupo_ou_sys_id) == 32 and re.match(r'^[0-9a-fA-F]{32}$', grupo_ou_sys_id):
            payload["assignment_group"] = grupo_ou_sys_id
        else:
            grupos = await servicenow_listar_grupos(filtro_nome=grupo_ou_sys_id, limite=1)
            dados = grupos.get("dados", [])
            if dados:
                payload["assignment_group"] = dados[0].get("sys_id")
            else:
                payload["assignment_group"] = grupo_ou_sys_id

    if analista_ou_sys_id:
        if len(analista_ou_sys_id) == 32 and re.match(r'^[0-9a-fA-F]{32}$', analista_ou_sys_id):
            payload["assigned_to"] = analista_ou_sys_id
        else:
            users = await servicenow_listar_usuarios(filtro_termo=analista_ou_sys_id, limite=1)
            dados = users.get("dados", [])
            if dados:
                payload["assigned_to"] = dados[0].get("sys_id")
            else:
                payload["assigned_to"] = analista_ou_sys_id

    if nota_atribuicao:
        payload["work_notes"] = f"[ATRIBUIÇÃO AUTOMÁTICA MCP]\n{nota_atribuicao}"

    return await servicenow_atualizar_registro(tabela, sys_id, payload)


# =====================================================================
# 10. GESTÃO DE PROBLEMAS (PROBLEM MANAGEMENT)
# =====================================================================

@mcp.tool()
async def servicenow_criar_problema(
    titulo: str,
    descricao: str,
    urgencia_1_a_3: str = "2",
    impacto_1_a_3: str = "2",
    causa_raiz_conhecida: Optional[str] = "",
    solucao_contorno_workaround: Optional[str] = "",
    cmdb_ci: Optional[str] = ""
) -> Dict[str, Any]:
    """Abre um novo registro formal de Problema (tabela 'problem')."""
    payload: Dict[str, Any] = {
        "short_description": titulo,
        "description": descricao,
        "urgency": str(urgencia_1_a_3),
        "impact": str(impacto_1_a_3),
        "state": "101",
    }
    if causa_raiz_conhecida:
        payload["cause_notes"] = causa_raiz_conhecida
    if solucao_contorno_workaround:
        payload["work_around"] = solucao_contorno_workaround
    if cmdb_ci:
        payload["cmdb_ci"] = cmdb_ci

    return await servicenow_criar_registro("problem", payload)


@mcp.tool()
async def servicenow_vincular_incidente_problema(
    incidente_sys_id: str,
    problema_sys_id: str
) -> Dict[str, Any]:
    """Associa um incidente a um problema pai existente (campo problem_id)."""
    payload = {
        "problem_id": problema_sys_id,
        "work_notes": f"Incidente associado ao Problema pai ({problema_sys_id}) pelo Agente SOAR."
    }
    return await servicenow_atualizar_registro("incident", incidente_sys_id, payload)


# =====================================================================
# 11. CMDB, RELACIONAMENTOS, ANEXOS & AUDITORIA
# =====================================================================

@mcp.tool()
async def servicenow_consultar_cmdb(
    termo_busca: str,
    classe_ci: str = "cmdb_ci",
    limite: int = 10
) -> Dict[str, Any]:
    """Pesquisa ativos na base CMDB (servidores, firewalls, VMs, roteadores)."""
    query = f"nameLIKE{termo_busca}^ORip_addressLIKE{termo_busca}^ORfqdnLIKE{termo_busca}"
    campos = "sys_id,name,ip_address,sys_class_name,operational_status,assigned_to,owned_by,location"
    return await servicenow_consultar_tabela(tabela=classe_ci, query=query, limite=limite, campos=campos, incluir_display_value=True)


@mcp.tool()
async def servicenow_obter_relacionamentos_ci(
    ci_sys_id: str,
    limite: int = 20
) -> Dict[str, Any]:
    """Consulta relacionamentos upstream e downstream de um CI na tabela 'cmdb_rel_ci'."""
    query = f"parent={ci_sys_id}^ORchild={ci_sys_id}"
    campos = "parent,type,child,connection_strength"
    res = await servicenow_consultar_tabela("cmdb_rel_ci", query=query, limite=limite, campos=campos, incluir_display_value=True)
    return {
        "status": "sucesso",
        "ci_sys_id": ci_sys_id,
        "total_relacionamentos": res.get("total_retornado", 0),
        "relacionamentos": res.get("dados", [])
    }


@mcp.tool()
async def servicenow_anexar_arquivo(
    tabela: str,
    sys_id: str,
    nome_arquivo: str,
    conteudo_texto_ou_base64: str,
    eh_base64: bool = False
) -> Dict[str, Any]:
    """Faz upload de arquivo/evidência forense como anexo em um registro (Attachment API)."""
    url_path = "/api/now/attachment/file"
    params = {
        "table_name": tabela,
        "table_sys_id": sys_id,
        "file_name": nome_arquivo
    }

    if eh_base64:
        try:
            raw_bytes = base64.b64decode(conteudo_texto_ou_base64)
            content_type = "application/octet-stream"
        except Exception as e:
            return {"status": "erro", "mensagem": f"Falha ao decodificar base64: {e}"}
    else:
        raw_bytes = conteudo_texto_ou_base64.encode("utf-8")
        content_type = "text/plain"

    headers = {"Content-Type": content_type, "Accept": "application/json"}
    try:
        response = await sn_client.request("POST", path=url_path, params=params, content=raw_bytes, headers_override=headers)
        if response.status_code in (200, 201):
            res = response.json().get("result", {})
            return {
                "status": "anexado",
                "attachment_sys_id": res.get("sys_id"),
                "file_name": res.get("file_name"),
                "size_bytes": res.get("size_bytes"),
                "detalhes": res
            }
        return _format_error(response.status_code, response.text)
    except Exception as e:
        return {"status": "erro", "mensagem": f"Erro no upload de anexo: {str(e)}"}


@mcp.tool()
async def servicenow_listar_anexos(
    tabela: str,
    sys_id: str
) -> Dict[str, Any]:
    """Lista anexos vinculados a um registro específico (tabela sys_attachment)."""
    query = f"table_name={tabela}^table_sys_id={sys_id}"
    campos = "sys_id,file_name,size_bytes,content_type,sys_created_on,sys_created_by"
    return await servicenow_consultar_tabela("sys_attachment", query=query, limite=30, campos=campos, incluir_display_value=True)


@mcp.tool()
async def servicenow_consultar_auditoria(
    tabela: str,
    sys_id: str,
    limite: int = 20
) -> Dict[str, Any]:
    """Consulta o histórico forense de alterações na tabela 'sys_audit' para um registro."""
    query = f"tablename={tabela}^documentkey={sys_id}"
    campos = "fieldname,oldvalue,newvalue,user,record_checkpoint,sys_created_on"
    return await servicenow_consultar_tabela("sys_audit", query=query, limite=limite, campos=campos, ordenar_por="sys_created_on", incluir_display_value=True)


@mcp.tool()
async def servicenow_testar_conexao() -> Dict[str, Any]:
    """Testa conectividade e validação da sessão com a instância do ServiceNow (dev420110)."""
    params = {
        "sysparm_query": f"user_name={SN_USER}",
        "sysparm_fields": "sys_id,user_name,name,email,active,locked_out",
        "sysparm_limit": 1
    }
    try:
        response = await sn_client.request("GET", "/api/now/table/sys_user", params=params)
        if response.status_code == 200:
            usuarios = response.json().get("result", [])
            user_info = usuarios[0] if usuarios else {"info": "Usuário autenticado com sucesso"}
            return {
                "status": "online",
                "instancia": SN_INSTANCE,
                "url": SN_URL,
                "usuario_conectado": SN_USER,
                "detalhes_usuario": user_info
            }
        return _format_error(response.status_code, response.text)
    except Exception as e:
        return {"status": "offline", "instancia": SN_INSTANCE, "url": SN_URL, "erro": str(e)}


if __name__ == "__main__":
    mcp.run()
