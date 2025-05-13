import os
from pathlib import Path
from typing import Annotated, Any

import pymupdf4llm
from mcp.server.fastmcp import FastMCP
from pydantic import Field

PRO_UNLOCKED = False
if pymupdf_pro_password := os.getenv("PYMUPDF_PRO_PASSWORD"):
    import pymupdf.pro

    pymupdf.pro.unlock(pymupdf_pro_password)
    # FIXME: Detect unlock failure
    PRO_UNLOCKED = True

mcp = FastMCP("pymupdf4llm-mcp")


@mcp.tool(
    description=(
        "Converts a PDF file to markdown format via pymupdf4llm. "
        "See [pymupdf.readthedocs.io/en/latest/pymupdf4llm](https://pymupdf.readthedocs.io/en/latest/pymupdf4llm/) for more. "
        "The `file_path`, `image_path`, and `save_path` parameters should be the absolute path to the PDF file, not a relative path. "
        "This tool will also convert the PDF to images and save them in the `image_path` directory. "
        "For larger PDF files, use `save_path` to save the markdown file then read it partially. "
    )
    + "\n**This tool now supports DOC/DOCX, XLS/XLSX, PPT/PPTX, HWP/HWPX as PRO version.**"
    if PRO_UNLOCKED
    else ""
)
def convert_pdf_to_markdown(
    file_path: Annotated[str, Field(description="Absolute path to the PDF file to convert")],
    image_path: Annotated[
        str | None,
        Field(
            description="Optional. Absolute path to the directory to save the images. "
            "If not provided, the images will be saved in the same directory as the PDF file."
        ),
    ] = None,
    save_path: Annotated[
        str | None,
        Field(
            description="Optional. Absolute path to the directory to save the markdown file. "
            "If provided, will return the path to the markdown file. "
            "If not provided, will return the markdown string."
        ),
    ] = None,
) -> dict[str, Any]:
    file_path: Path = Path(file_path).expanduser().resolve()
    if not file_path.exists():
        return {
            "error": f"File not found: {file_path}",
            "success": False,
        }
    image_path = Path(image_path).expanduser().resolve() if image_path else file_path.parent
    try:
        content = pymupdf4llm.to_markdown(file_path, write_images=True, image_path=image_path.as_posix())
        if save_path:
            save_path: Path = Path(save_path).expanduser().resolve()
            save_path.parent.mkdir(parents=True, exist_ok=True)
            content = pymupdf4llm.to_markdown(file_path, write_images=True, image_path=image_path.as_posix())
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
