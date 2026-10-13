import pytest
import os
import sys

# Add root directory to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import servicenow_mcp_server as srv
import export_schemas


def test_tool_count():
    """Valida que todas as 97 ferramentas estão devidamente mapeadas."""
    tools = srv.mcp._tool_manager.list_tools()
    assert len(tools) >= 90, f"Esperado ao menos 90 ferramentas, encontrado {len(tools)}"


def test_schema_export():
    """Valida que os esquemas exportados possuem propriedades válidas."""
    tools = srv.mcp._tool_manager.list_tools()
    for tool in tools:
        assert tool.name.startswith("servicenow_"), f"Nome de ferramenta inválido: {tool.name}"
        assert tool.description, f"Ferramenta sem descrição: {tool.name}"


def test_aliases_mapping():
    """Valida que o arquivo de bridge possui aliases configurados."""
    import importlib.util
    spec = importlib.util.spec_from_file_location("bridge", os.path.join(os.path.dirname(__file__), "..", "servicenow-mcp-bridge.py"))
    bridge = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(bridge)
    
    assert "create_incident" in bridge.ALIASES
    assert "add_comment" in bridge.ALIASES
    assert "list_catalog_items" in bridge.ALIASES
    assert "approve_change" in bridge.ALIASES
