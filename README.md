# 🚀 ServiceNow MCP Server (Model Context Protocol)

[![License: Apache 2.0](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](LICENSE)
[![Python: 3.10+](https://img.shields.io/badge/Python-3.10%2B-brightgreen.svg)](https://www.python.org/)
[![MCP](https://img.shields.io/badge/MCP-2025--11--25-orange.svg)](https://modelcontextprotocol.io/)
[![Tools: 97](https://img.shields.io/badge/Tools-97%20Enterprise%20Tools-purple.svg)](#-matriz-completa-das-97-ferramentas)
[![Docker](https://img.shields.io/badge/Docker-Ready-2496ED.svg)](Dockerfile)

**Conecte seu assistente de Inteligência Artificial (Antigravity IDE, Claude Desktop, Cursor, VS Code) diretamente ao ServiceNow.**  
Execute tarefas complexas de ITSM, Gerenciamento de Mudanças (GMUD), Catálogo de Serviços, Gestão Ágil, Workflows, Script Includes, Update Sets, CMDB e Resposta a Incidentes (SecOps/SOAR) através de linguagem natural.

---

## 🌟 Principais Recursos

- **97 Ferramentas Empresariais Nativas em Português:** Nomenclatura semântica clara e padronizada com o ecossistema corporativo.
- **Suporte Transparente a Aliases em Inglês:** Compatibilidade total com clientes e playbooks em inglês (`create_incident`, `approve_change`, `create_story`, `list_catalog_items`).
- **Autenticação Avançada com Session Token (`X-UserToken` / `g_ck`):** Conecta perfeitamente mesmo em Personal Developer Instances (PDIs) que restringem Basic Auth direta na Table API.
- **Cobertura Ponta a Ponta do ServiceNow:**
  - 🎫 **ITSM Completo:** Incidentes, Resoluções, Notas Técnicas e Comentários Públicos.
  - 🛒 **Catálogo de Serviços:** Itens, Categorias, Variáveis de Formulário e Auditoria de Otimização.
  - 🔄 **GMUD & Mudanças:** Abertura, Tarefas Técnicas, Tramitação e Aprovação/Rejeição formal.
  - 🏃 **Ágil / Scrum & Projetos:** Histórias (`rm_story`), Épicos, Dependências, Tarefas Scrum e Projetos (`pm_project`).
  - ⚙️ **Desenvolvimento:** Script Includes JavaScript, Update Sets (`sys_update_set`) e Workflows.
  - 🖥️ **CMDB & Topologia:** Mapeamento de CIs e rastreamento de relacionamentos upstream/downstream.
  - 📎 **Attachment & Auditoria:** Upload/download de evidências forenses e histórico `sys_audit`.
- **Stdio Bridge com Redirecionamento Seguro:** Tratamento de logs limpo em `logs/` para não interferir na comunicação JSON-RPC.

---

## 📊 Matriz Completa das 97 Ferramentas

### 1. Incidentes (`incident`)
| Ferramenta (Português) | Alias (Inglês) | Descrição |
| :--- | :--- | :--- |
| `servicenow_criar_incidente` | `create_incident` | Cria novo incidente formal no ServiceNow. |
| `servicenow_atualizar_incidente` | `update_incident` | Atualiza campos e estados do incidente. |
| `servicenow_adicionar_comentario` | `add_comment` | Adiciona comentário público visível ao solicitante (`comments`). |
| `servicenow_adicionar_nota_tecnica` | - | Adiciona anotação de trabalho interna (`work_notes`). |
| `servicenow_resolver_incidente` | `resolve_incident` | Resolve incidente com código de fechamento e notas. |
| `servicenow_listar_incidentes` | `list_incidents` | Lista incidentes com suporte a filtros codificados. |
| `servicenow_abrir_incidente_seguranca` | - | Abertura automatizada de P1/SecOps com dados de IoCs. |
| `servicenow_fechar_incidente` | - | Alias direto para resolução/fechamento. |

### 2. Catálogo de Serviços (`sc_cat_item`, `sc_category`, `sc_catalog`)
| Ferramenta (Português) | Alias (Inglês) | Descrição |
| :--- | :--- | :--- |
| `servicenow_listar_itens_catalogo` | `list_catalog_items` | Lista itens do catálogo de serviços ativos. |
| `servicenow_obter_item_catalogo` | `get_catalog_item` | Detalhes completos de um item específico por `sys_id`. |
| `servicenow_atualizar_item_catalogo` | `update_catalog_item` | Atualiza propriedades, preços e disponibilidades. |
| `servicenow_listar_categorias_catalogo` | `list_catalog_categories` | Lista categorias de itens de catálogo. |
| `servicenow_criar_categoria_catalogo` | `create_catalog_category` | Cria uma nova categoria no catálogo. |
| `servicenow_atualizar_categoria_catalogo` | `update_catalog_category` | Atualiza dados de uma categoria existente. |
| `servicenow_mover_item_catalogo` | `move_catalog_item` | Move um item de catálogo entre categorias. |
| `servicenow_criar_variavel_item_catalogo` | `create_catalog_item_variable` | Cria nova variável/campo de formulário no item. |
| `servicenow_listar_variaveis_item_catalogo` | `list_catalog_item_variables` | Lista todas as variáveis de formulário de um item. |
| `servicenow_atualizar_variavel_item_catalogo` | `update_catalog_item_variable` | Atualiza propriedades de uma variável. |
| `servicenow_listar_catalogos` | `list_catalogs` | Lista os portais de catálogos corporativos. |
| `servicenow_obter_recomendacoes_otimizacao_catalogo` | `get_optimization_recommendations` | Analisa e recomenda correções para itens sem descrição. |

### 3. Gestão de Mudanças (GMUD) (`change_request`, `change_task`)
| Ferramenta (Português) | Alias (Inglês) | Descrição |
| :--- | :--- | :--- |
| `servicenow_criar_solicitacao_mudanca` | `create_change_request` | Cria solicitação de mudança (Normal, Padrão ou Emergencial). |
| `servicenow_atualizar_solicitacao_mudanca` | `update_change_request` | Atualiza dados e fases da GMUD. |
| `servicenow_listar_solicitacoes_mudanca` | `list_change_requests` | Lista GMUDs com opções de filtragem por estado/risco. |
| `servicenow_obter_detalhes_mudanca` | `get_change_request_details` | Detalhes completos por número (ex: `CHG0040007`) ou sys_id. |
| `servicenow_adicionar_tarefa_mudanca` | `add_change_task` | Adiciona tarefa técnica de implementação à GMUD. |
| `servicenow_enviar_mudanca_aprovacao` | `submit_change_for_approval` | Tramita a GMUD para autorização. |
| `servicenow_aprovar_mudanca` | `approve_change` | Aprova formalmente a mudança no registro de aprovação. |
| `servicenow_rejeitar_mudanca` | `reject_change` | Rejeita formalmente a GMUD com justificativa. |
| `servicenow_criar_gmud` | - | Alias direto para abertura de mudança com plano de rollback. |

### 4. Gestão Ágil & Projetos (`rm_story`, `rm_epic`, `rm_scrum_task`, `pm_project`)
| Ferramenta (Português) | Alias (Inglês) | Descrição |
| :--- | :--- | :--- |
| `servicenow_criar_historia` | `create_story` | Cria história de usuário no módulo Agile Development. |
| `servicenow_atualizar_historia` | `update_story` | Atualiza status, sprint e story points da história. |
| `servicenow_listar_historias` | `list_stories` | Lista histórias com opções de filtragem. |
| `servicenow_criar_dependencia_historia` | `create_story_dependency` | Cria dependência predecessora entre duas histórias. |
| `servicenow_excluir_dependencia_historia` | `delete_story_dependency` | Remove vínculo de dependência entre histórias. |
| `servicenow_criar_epico` | `create_epic` | Cria novo Épico corporativo. |
| `servicenow_atualizar_epico` | `update_epic` | Atualiza dados de um Épico. |
| `servicenow_listar_epicos` | `list_epics` | Lista os Épicos cadastrados. |
| `servicenow_criar_tarefa_scrum` | `create_scrum_task` | Cria tarefa técnica vinculada a uma história. |
| `servicenow_atualizar_tarefa_scrum` | `update_scrum_task` | Atualiza horas e estado da tarefa scrum. |
| `servicenow_listar_tarefas_scrum` | `list_scrum_tasks` | Lista tarefas scrum por história. |
| `servicenow_criar_projeto` | `create_project` | Cria projeto no Project Management (`pm_project`). |
| `servicenow_atualizar_projeto` | `update_project` | Atualiza porcentagem e fases do projeto. |
| `servicenow_listar_projetos` | `list_projects` | Lista projetos ativos e percentuais concluídos. |

### 5. Fluxos de Trabalho & Script Includes (`wf_workflow`, `sys_script_include`)
| Ferramenta (Português) | Alias (Inglês) | Descrição |
| :--- | :--- | :--- |
| `servicenow_listar_fluxos_trabalho` | `list_workflows` | Lista definições de workflows tradicionais. |
| `servicenow_obter_fluxo_trabalho` | `get_workflow` | Detalhes e etapas do workflow. |
| `servicenow_criar_fluxo_trabalho` | `create_workflow` | Cria nova definição de workflow. |
| `servicenow_atualizar_fluxo_trabalho` | `update_workflow` | Atualiza propriedades do workflow. |
| `servicenow_excluir_fluxo_trabalho` | `delete_workflow` | Remove fluxo de trabalho (`confirmar=True`). |
| `servicenow_listar_script_includes` | `list_script_includes` | Lista bibliotecas JavaScript do sistema. |
| `servicenow_obter_script_include` | `get_script_include` | Obtém o código JavaScript e escopo da biblioteca. |
| `servicenow_criar_script_include` | `create_script_include` | Cria novo Script Include JavaScript. |
| `servicenow_atualizar_script_include` | `update_script_include` | Atualiza o código JavaScript de uma biblioteca. |
| `servicenow_excluir_script_include` | `delete_script_include` | Remove biblioteca Script Include (`confirmar=True`). |

### 6. Update Sets / Conjuntos de Alterações (`sys_update_set`)
| Ferramenta (Português) | Alias (Inglês) | Descrição |
| :--- | :--- | :--- |
| `servicenow_listar_conjuntos_alteracoes` | `list_changesets` | Lista Update Sets da instância. |
| `servicenow_obter_detalhes_conjunto_alteracoes` | `get_changeset_details` | Lista arquivos XML gravados no Update Set. |
| `servicenow_criar_conjunto_alteracoes` | `create_changeset` | Cria novo Update Set para empacotamento de código. |
| `servicenow_atualizar_conjunto_alteracoes` | `update_changeset` | Atualiza descrição e status do Update Set. |
| `servicenow_confirmar_conjunto_alteracoes` | `commit_changeset` | Conclui e fecha o Update Set para migração. |
| `servicenow_publicar_conjunto_alteracoes` | `publish_changeset` | Exporta e disponibiliza o conjunto de alterações. |
| `servicenow_adicionar_arquivo_conjunto_alteracoes` | `add_file_to_changeset` | Associa arquivo técnico ao conjunto. |

### 7. Base de Conhecimento (`kb_knowledge_base`, `kb_knowledge`)
| Ferramenta (Português) | Alias (Inglês) | Descrição |
| :--- | :--- | :--- |
| `servicenow_criar_base_conhecimento` | `create_knowledge_base` | Cria uma nova base de conhecimento. |
| `servicenow_listar_bases_conhecimento` | `list_knowledge_bases` | Lista bases de conhecimento cadastradas. |
| `servicenow_criar_categoria_conhecimento` | `create_knowledge_category` | Cria categoria em uma base de conhecimento. |
| `servicenow_criar_artigo_conhecimento` | `create_article` | Cria novo artigo de conhecimento HTML/texto. |
| `servicenow_atualizar_artigo_conhecimento` | `update_article` | Atualiza o conteúdo ou título do artigo. |
| `servicenow_publicar_artigo_conhecimento` | `publish_article` | Publica o artigo formalmente (`workflow_state=published`). |
| `servicenow_listar_artigos_conhecimento` | `list_articles` | Pesquisa e lista artigos por palavra-chave. |
| `servicenow_obter_artigo_conhecimento` | `get_article` | Detalhes e conteúdo na íntegra de um artigo. |
| `servicenow_consultar_base_conhecimento` | - | Alias de busca rápida por texto livre. |

### 8. Usuários, Grupos e Governança (`sys_user`, `sys_user_group`)
| Ferramenta (Português) | Alias (Inglês) | Descrição |
| :--- | :--- | :--- |
| `servicenow_criar_usuario` | `create_user` | Cria novo usuário no sistema. |
| `servicenow_atualizar_usuario` | `update_user` | Atualiza atributos de um usuário. |
| `servicenow_obter_usuario` | `get_user` | Detalhes de usuário por login, e-mail ou sys_id. |
| `servicenow_listar_usuarios` | `list_users` | Lista usuários ativos com opções de filtro. |
| `servicenow_buscar_usuario` | - | Busca rápida de usuários por termo livre. |
| `servicenow_criar_grupo` | `create_group` | Cria novo grupo de atendimento. |
| `servicenow_atualizar_grupo` | `update_group` | Atualiza informações de um grupo. |
| `servicenow_listar_grupos` | `list_groups` | Lista grupos de atendimento cadastrados. |
| `servicenow_buscar_grupo` | - | Busca rápida de grupos por nome. |
| `servicenow_adicionar_membros_grupo` | `add_group_members` | Adiciona usuários a um grupo (`sys_user_grmember`). |
| `servicenow_remover_membros_grupo` | `remove_group_members` | Remove usuários de um grupo. |
| `servicenow_atribuir_chamado` | - | Atribui chamados automaticamente a grupos e analistas. |

### 9. Problemas, CMDB, Anexos, Auditoria e Diagnóstico
| Ferramenta (Português) | Alias (Inglês) | Descrição |
| :--- | :--- | :--- |
| `servicenow_criar_problema` | - | Cria novo registro de Problema formal (`problem`). |
| `servicenow_vincular_incidente_problema` | - | Associa incidente a um problema pai existente. |
| `servicenow_consultar_cmdb` | - | Pesquisa ativos de infraestrutura e serviços (CMDB). |
| `servicenow_obter_relacionamentos_ci` | - | Mapeia topologia e conexões upstream/downstream em `cmdb_rel_ci`. |
| `servicenow_anexar_arquivo` | - | Upload de logs/evidências via Attachment API. |
| `servicenow_listar_anexos` | - | Lista anexos vinculados a qualquer registro. |
| `servicenow_consultar_auditoria` | - | Histórico forense detalhado de alterações na tabela `sys_audit`. |
| `servicenow_consultar_tabela` | - | Consulta genérica à Table API com queries codificadas. |
| `servicenow_obter_registro_por_id` | - | Busca registro por sys_id em qualquer tabela. |
| `servicenow_criar_registro` | - | Criação genérica de registro via POST. |
| `servicenow_atualizar_registro` | - | Atualização genérica de registro via PATCH. |
| `servicenow_excluir_registro` | - | Exclusão com proteção de confirmação (`confirmar=True`). |
| `servicenow_descrever_campos_tabela` | - | Dicionário de dados da tabela em `sys_dictionary`. |
| `servicenow_listar_tabelas` | - | Lista tabelas da instância em `sys_db_object`. |
| `servicenow_obter_estatisticas_tabela` | - | Cálculos e contagens agregadas na Aggregate API. |
| `servicenow_testar_conexao` | - | Valida status online, sessão e permissões do usuário. |

---

## 🛠️ Instalação e Configuração

### Pré-requisitos
- **Python 3.10+**
- Uma instância do ServiceNow (comercial ou Personal Developer Instance - PDI)
- Credenciais de usuário (recomendado perfil `admin` ou papéis `itil` / `rest_api_explorer`)

### 1. Clonar o Repositório
```bash
git clone https://github.com/nks1097/ServiceNow-MCP-Server.git
cd ServiceNow-MCP-Server
```

### 2. Instalar Dependências
```bash
pip install -r requirements.txt
```

### 3. Configurar Variáveis de Ambiente
Copie o arquivo de exemplo e insira suas credenciais:
```bash
cp .env.example .env
```

Edite o arquivo `.env`:
```env
SN_INSTANCE=devXXXXX
SN_USER=admin
SN_PASS=seu_token_ou_senha_aqui
SN_TIMEOUT=30.0
SN_VERIFY_SSL=true
```

---

## 💻 Como Configurar nos Clientes MCP

### 🤖 Google Antigravity IDE
Adicione ao seu arquivo de configuração `mcp_config.json`:
```json
{
  "mcpServers": {
    "servicenow": {
      "command": "python",
      "args": [
        "c:/caminho/para/ServiceNow-MCP-Server/servicenow-mcp-bridge.py"
      ],
      "env": {
        "SN_INSTANCE": "devXXXXX",
        "SN_USER": "admin",
        "SN_PASS": "sua_senha",
        "PYTHONIOENCODING": "utf-8",
        "FASTMCP_LOG_LEVEL": "CRITICAL"
      }
    }
  }
}
```

### 💬 Claude Desktop (`claude_desktop_config.json`)
```json
{
  "mcpServers": {
    "servicenow": {
      "command": "python",
      "args": [
        "c:/caminho/para/ServiceNow-MCP-Server/servicenow-mcp-bridge.py"
      ],
      "env": {
        "SN_INSTANCE": "devXXXXX",
        "SN_USER": "admin",
        "SN_PASS": "sua_senha"
      }
    }
  }
}
```

### ⚡ Cursor (`.cursor/mcp.json`)
```json
{
  "mcpServers": {
    "servicenow": {
      "command": "python",
      "args": ["servicenow-mcp-bridge.py"],
      "env": {
        "SN_INSTANCE": "devXXXXX",
        "SN_USER": "admin",
        "SN_PASS": "sua_senha"
      }
    }
  }
}
```

---

## 🐳 Executando com Docker

Se preferir rodar isolado em container:

```bash
# Construir e rodar com Docker Compose
docker-compose up --build -d
```

Ou usando o `Makefile`:
```bash
make docker-build
make docker-run
```

---

## 🔒 Segurança e Melhores Práticas

- **Proteção de Credenciais:** O arquivo `.env` está explicitamente no `.gitignore` para impedir que senhas vazem para repositórios públicos.
- **Auditoria de Sessão:** O servidor realiza login limpo e renova dinamicamente tokens de sessão (`g_ck`) em caso de timeout.
- **Operações Destrutivas:** Ferramentas que excluem dados (`servicenow_excluir_registro`, `servicenow_excluir_script_include`, etc.) exigem explicitamente o parâmetro `confirmar=True` como salvaguarda contra comandos acidentais.

---

## 👤 Autor

Desenvolvido por **Natanael Krindges**  
- **GitHub:** [@nks1097](https://github.com/nks1097)  
- **E-mail:** natanael1097@gmail.com

---

## 📄 Licença

Distribuído sob a licença **Apache 2.0**. Consulte o arquivo [LICENSE](LICENSE) para mais detalhes.
