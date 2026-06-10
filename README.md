# pymupdf4llm-mcp

[![Release](https://img.shields.io/github/v/release/pymupdf/pymupdf4llm-mcp)](https://img.shields.io/github/v/release/pymupdf/pymupdf4llm-mcp)
[![Build status](https://img.shields.io/github/actions/workflow/status/pymupdf/pymupdf4llm-mcp/main.yml?branch=main)](https://github.com/pymupdf/pymupdf4llm-mcp/actions/workflows/main.yml?query=branch%3Amain)
[![Commit activity](https://img.shields.io/github/commit-activity/m/pymupdf/pymupdf4llm-mcp)](https://img.shields.io/github/commit-activity/m/pymupdf/pymupdf4llm-mcp)
[![License](https://img.shields.io/github/license/pymupdf/pymupdf4llm-mcp)](https://img.shields.io/github/license/pymupdf/pymupdf4llm-mcp)

MCP Server for pymupdf4llm, best for export PDF to markdown for LLM.

## Quick Start

Run the following command to run the MCP server:

```bash
uvx pymupdf4llm-mcp@latest stdio # stdio mode
# or
uvx pymupdf4llm-mcp@latest sse # sse mode
```

Configure your cursor/windsurf/... and other MCP client to this server:

```json
{
  "mcpServers": {
    "pymupdf4llm-mcp": {
      "command": "uvx",
      "args": [
        "pymupdf4llm-mcp@latest",
        "stdio"
      ],
      "env": {}
    }
  }
}
```

## Testing

Ensure you have Snapshot installed:

`pip install inline-snapshot`

Then from the root folder of the repo run:

```bash
python -m pytest
```

## Publishing

Assuming you have an access token.

Bump pyproject.toml:3 `version` first, then:

```bash
make build
make publish
```
