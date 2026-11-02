from pathlib import Path
from typing import Annotated, Any

import pymupdf4llm
from mcp.server.fastmcp import FastMCP
from pydantic import Field

from pymupdf4llm_mcp.workspace import (
    detect_workspace,
    prepare_output,
    renumber_images,
    rewrite_refs,
    safe_stem,
    stable_cwd,
)

# Explicit log level: an invalid LOG_LEVEL in the environment otherwise fails
# validation at startup and the server never comes up.
# mcp 2.x drops mcp.server.fastmcp, hence the <2 pin in pyproject.toml.
mcp = FastMCP("pymupdf4llm-mcp", log_level="INFO")

_MAX_INLINE = 10000


def _inline(content: str, tips: str) -> dict[str, Any]:
    if len(content) > _MAX_INLINE:
        content = content[:_MAX_INLINE] + "\n\n... (truncated)"
    return {"success": True, "markdown_content": content, "tips": tips}


def _convert_with_explicit_paths(file_path: Path, image_path: str, save_path: str | None) -> dict[str, Any]:
    """Upstream behaviour, unchanged: caller owns every output location."""
    image_dir = Path(image_path).expanduser().resolve()
    content = pymupdf4llm.to_markdown(file_path, write_images=True, image_path=image_dir.as_posix())
    if save_path:
        md_path = Path(save_path).expanduser().resolve()
        md_path.parent.mkdir(parents=True, exist_ok=True)
        md_path.write_text(content, encoding="utf-8")
        return {"success": True, "markdown_path": md_path.as_posix()}
    return _inline(content, "All content is returned. ")


def _convert_into_workspace(
    file_path: Path,
    workspace_root: str | None,
    output_dir: str,
    overwrite: bool,
) -> dict[str, Any]:
    root = detect_workspace(workspace_root, file_path)
    if root is None:
        return {
            "success": False,
            "error": "Workspace root could not be detected (no git repository and the server runs "
            "from the home directory). Pass workspace_root explicitly or set PYMUPDF4LLM_WORKSPACE.",
        }

    stem = safe_stem(file_path)
    dest, error = prepare_output(root, output_dir, stem, overwrite)
    md_path = dest / f"{stem}.md"
    if error:
        return {"success": False, "error": error, "markdown_path": md_path.as_posix()}

    with stable_cwd(dest):
        content = pymupdf4llm.to_markdown(file_path, write_images=True, image_path=dest.as_posix())
    renamed = renumber_images(dest)
    content, refs, missing = rewrite_refs(content, dest, renamed)
    md_path.write_text(content, encoding="utf-8")

    result: dict[str, Any] = {
        "success": not missing,
        "markdown_path": md_path.as_posix(),
        "workspace_root": root.as_posix(),
        "image_dir": dest.as_posix(),
        "image_count": len(refs),
        "images": refs,
    }
    if missing:
        result["error"] = f"Image references missing on disk: {missing}"
        return result
    result["markdown_content"] = (
        content if len(content) <= _MAX_INLINE else content[:_MAX_INLINE] + "\n\n... (truncated)"
    )
    return result


@mcp.tool(
    description=(
        "Converts a PDF file to markdown format via pymupdf4llm. "
        "See [pymupdf.readthedocs.io/en/latest/pymupdf4llm](https://pymupdf.readthedocs.io/en/latest/pymupdf4llm/) for more. "
        "By default the markdown and every extracted image go into one per-PDF folder inside "
        "the current workspace: `<workspace>/extracted/<pdf-name>/`, with relative image links. "
        "An existing extraction is never replaced unless `overwrite` is true. "
        "Passing `image_path` or `save_path` keeps the original behaviour and writes exactly where told. "
        "Parameters are absolute paths. For larger PDFs, read the returned `markdown_path` file partially."
    )
)
def convert_pdf_to_markdown(
    file_path: Annotated[str, Field(description="Absolute path to the PDF file to convert")],
    image_path: Annotated[
        str | None,
        Field(
            description="Optional. Absolute path to the directory to save the images. "
            "If neither image_path nor save_path is given, images go to "
            "<workspace>/extracted/<pdf-name>/."
        ),
    ] = None,
    save_path: Annotated[
        str | None,
        Field(
            description="Optional. Absolute path of the markdown file to write. "
            "If neither image_path nor save_path is given, the markdown is written to "
            "<workspace>/extracted/<pdf-name>/<pdf-name>.md."
        ),
    ] = None,
    workspace_root: Annotated[
        str | None,
        Field(
            description="Optional. Workspace/repository root. Auto-detected from the environment "
            "or git when omitted."
        ),
    ] = None,
    output_dir: Annotated[
        str,
        Field(description="Subfolder of the workspace that holds all extractions."),
    ] = "extracted",
    overwrite: Annotated[
        bool,
        Field(description="Replace an existing extraction folder for the same PDF."),
    ] = False,
) -> dict[str, Any]:
    path = Path(file_path).expanduser().resolve()
    if not path.exists():
        return {
            "error": f"File not found: {path}",
            "success": False,
        }

    try:
        if image_path is not None or save_path is not None:
            return _convert_with_explicit_paths(path, image_path or path.parent.as_posix(), save_path)
        return _convert_into_workspace(path, workspace_root, output_dir, overwrite)
    except Exception as e:
        return {
            "error": f"Failed to convert PDF to markdown: {e!s}",
            "success": False,
        }
