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

## Output layout

By default every PDF gets its own folder inside the workspace (repository) that is open,
so images never pile up next to the source file:

```
<workspace>/extracted/<pdf-name>/
├── <pdf-name>.md
├── image-001.png
└── image-002.png
```

Image links in the markdown are relative (`![](image-001.png)`), so a folder can be moved
as a unit and still renders correctly.

| Parameter        | Default                                          | Meaning                                                 |
| ---------------- | ------------------------------------------------ | ------------------------------------------------------- |
| `file_path`      | —                                                | absolute path to the PDF                                |
| `image_path`     | `<workspace>/extracted/<pdf-name>/`              | image directory; setting it restores upstream behaviour |
| `save_path`      | `<workspace>/extracted/<pdf-name>/<pdf-name>.md` | markdown file; setting it restores upstream behaviour   |
| `workspace_root` | auto-detected                                    | repository root                                         |
| `output_dir`     | `extracted`                                      | subfolder holding all extractions                       |
| `overwrite`      | `false`                                          | replace a previous extraction of the same PDF           |

The workspace is resolved from `workspace_root`, then `PYMUPDF4LLM_WORKSPACE`,
`OPENCODE_PROJECT_DIR` / `OPENCODE_DIRECTORY`, the git root of the working directory, the git
root of the PDF's ancestors, and finally the working directory. `$HOME` is never used, so an
MCP client that starts the server from the home directory gets a clear error instead of files
scattered outside the project.

Extracting the same PDF twice is refused until `overwrite=true`, which deletes only the files
inside that one extraction folder. The source PDF is never modified.

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
