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

mcp = FastMCP("pymupdf4llm-mcp")


def _convert_into_workspace(
    file_path: Path,
    workspace_root: str | None,
    output_dir: str,
    overwrite: bool,
) -> dict[str, Any]:
    """Write the markdown and every image into one folder inside the workspace."""
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
    result["markdown_content"] = content if len(content) <= 10000 else content[:10000] + "\n\n... (truncated)"
    return result


@mcp.tool(
    description=(
        "Converts a PDF file to markdown format via pymupdf4llm. "
        "See [pymupdf.readthedocs.io/en/latest/pymupdf4llm](https://pymupdf.readthedocs.io/en/latest/pymupdf4llm/) for more. "
        "By default the markdown and every extracted image go into one per-PDF folder inside "
        "the current workspace: `<workspace>/extracted/<pdf-name>/`, with relative image links. "
        "An existing extraction is never replaced unless `overwrite` is true. "
        "Passing `image_path` or `save_path` keeps the original behaviour and writes exactly where told. "
        "Parameters are absolute paths. For larger PDF files, use `save_path` to save the markdown file then read it partially. "
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
            description="Optional. Absolute path to the markdown file to write. "
            "If neither image_path nor save_path is given, the markdown is written to "
            "<workspace>/extracted/<pdf-name>/<pdf-name>.md.",
        ),
    ] = None,
    workspace_root: Annotated[
        str | None,
        Field(
            description="Optional. Workspace/repository root. Auto-detected from the environment or git when omitted."
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
    file_path: Path = Path(file_path).expanduser().resolve()
    if not file_path.exists():
        return {
            "error": f"File not found: {file_path}",
            "success": False,
        }

    if image_path is None and save_path is None:
        try:
            return _convert_into_workspace(file_path, workspace_root, output_dir, overwrite)
        except Exception as e:
            return {
                "error": f"Failed to convert PDF to markdown: {e!s}",
                "success": False,
            }

    image_path = Path(image_path).expanduser().resolve() if image_path else file_path.parent
    try:
        content = pymupdf4llm.to_markdown(file_path, write_images=True, image_path=image_path.as_posix())
        if save_path:
            save_path: Path = Path(save_path).expanduser().resolve()
            save_path.parent.mkdir(parents=True, exist_ok=True)
            with open(save_path, "w", encoding="utf-8") as f:
                f.write(content)
            return {
                "success": True,
                "markdown_path": save_path.expanduser().resolve().absolute().as_posix(),
            }
        else:
            if len(content) > 10000:
                # Truncate the content to avoid too long response
                content = content[:10000] + "\n\n... (truncated)"
                tips = (
                    "The content is too long. Please use `save_path` to save the markdown file and read it partially."
                )
            else:
                tips = "All content is returned. "

            return {
                "success": True,
                "markdown_content": content,
                "tips": tips,
            }
    except Exception as e:
        return {
            "error": f"Failed to convert PDF to markdown: {e!s}",
            "success": False,
        }
