from pathlib import Path
from typing import Annotated, Any

import pymupdf4llm
from mcp.server.fastmcp import FastMCP
from pydantic import Field

mcp = FastMCP("pymupdf4llm-mcp")


@mcp.tool(
    description=(
        "Converts a PDF file to markdown format via pymupdf4llm. "
        "See [pymupdf.readthedocs.io/en/latest/pymupdf4llm](https://pymupdf.readthedocs.io/en/latest/pymupdf4llm/) for more. "
        "The `file_path`, `image_path`, and `save_path` parameters should be the absolute path to the PDF file, not a relative path. "
        "This tool will also convert the PDF to images and save them in the `image_path` directory. "
        "For larger PDF files, use `save_path` to save the markdown file then read it partially. "
    )
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


@mcp.tool(
    description=(
        "Checks a PDF file's fonts for reliability issues that can cause silent text corruption during extraction. "
        "Some PDFs contain fonts with broken ToUnicode mappings that cause every text extractor to produce wrong "
        "characters (e.g., Greek letters extracted as Latin letters, arrows extracted as 'o'). "
        "This tool inspects font metadata and reports which pages have unreliable fonts, so you can fall back to "
        "OCR or vision-based extraction for those pages. Run this before convert_pdf_to_markdown to check if the "
        "extraction will be accurate. "
        "The `file_path` parameter should be the absolute path to the PDF file. "
    )
)
def check_font_reliability(
    file_path: Annotated[str, Field(description="Absolute path to the PDF file to check")],
    pages: Annotated[
        str | None,
        Field(
            description="Optional. Comma-separated page numbers (0-indexed) to check. "
            "If not provided, all pages are checked. Example: '0,1,2' for first three pages."
        ),
    ] = None,
) -> dict[str, Any]:
    file_path: Path = Path(file_path).expanduser().resolve()
    if not file_path.exists():
        return {
            "error": f"File not found: {file_path}",
            "success": False,
        }

    try:
        from pymupdf4llm.helpers.font_analysis import analyze_fonts
    except ImportError:
        return {
            "error": "Font analysis module not available. Requires pymupdf4llm with font_analysis support.",
            "success": False,
        }

    page_indices = None
    if pages:
        try:
            page_indices = [int(p.strip()) for p in pages.split(",")]
        except ValueError:
            return {
                "error": f"Invalid pages parameter: {pages}. Use comma-separated integers like '0,1,2'.",
                "success": False,
            }

    try:
        reports = analyze_fonts(file_path.as_posix(), pages=page_indices)

        unreliable_pages = []
        all_warnings = []

        for report in reports:
            if report.unreliable:
                unreliable_pages.append(report.page)
                for w in report.warnings:
                    all_warnings.append({
                        "page": report.page,
                        "font": w.font_name,
                        "category": w.category,
                        "message": w.message,
                    })

        return {
            "success": True,
            "total_pages_checked": len(reports),
            "unreliable_pages": unreliable_pages,
            "is_reliable": len(unreliable_pages) == 0,
            "warnings": all_warnings,
            "tips": (
                "All pages appear reliable for text extraction."
                if not unreliable_pages
                else f"Pages {unreliable_pages} have unreliable fonts. "
                "Consider using OCR or vision-based extraction for these pages."
            ),
        }
    except Exception as e:
        return {
            "error": f"Failed to analyze fonts: {e!s}",
            "success": False,
        }
