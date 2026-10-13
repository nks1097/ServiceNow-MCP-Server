#!/usr/bin/env python3
"""
Script para exportar esquemas JSON de todas as ferramentas do Servidor MCP ServiceNow
para o diretório de schemas do Antigravity IDE.
"""

import asyncio
import json
from pathlib import Path
from servicenow_mcp_server import mcp

async def export():
    tools = await mcp.list_tools()
    output_dir = Path(__file__).parent
    
    count = 0
    for t in tools:
        schema_file = output_dir / f"{t.name}.json"
        tool_data = {
            "name": t.name,
            "description": t.description or "",
            "parameters": t.inputSchema
        }
        with open(schema_file, "w", encoding="utf-8") as f:
            json.dump(tool_data, f, ensure_ascii=False, indent=2)
        print(f"Exportado: {schema_file.name}")
        count += 1
        
    print(f"\nTotal de ferramentas exportadas: {count}")

if __name__ == "__main__":
    asyncio.run(export())
