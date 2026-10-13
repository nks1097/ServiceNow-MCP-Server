FROM python:3.11-slim

LABEL maintainer="Natanael Krindges <natanael1097@gmail.com>"
LABEL description="ServiceNow Enterprise Model Context Protocol (MCP) Server"

ENV PYTHONUNBUFFERED=1 \
    PYTHONIOENCODING=utf-8 \
    FASTMCP_LOG_LEVEL=INFO

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy source code and schemas
COPY servicenow_mcp_server.py .
COPY servicenow-mcp-bridge.py .
COPY export_schemas.py .
COPY schemas/ ./schemas/

# Default entrypoint for stdio MCP
ENTRYPOINT ["python", "servicenow-mcp-bridge.py"]
