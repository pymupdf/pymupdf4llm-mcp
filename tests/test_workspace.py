from pathlib import Path

import pymupdf
import pytest

from pymupdf4llm_mcp import workspace
from pymupdf4llm_mcp.app import convert_pdf_to_markdown


def _swatch(path: Path) -> Path:
    pix = pymupdf.Pixmap(pymupdf.csRGB, pymupdf.IRect(0, 0, 120, 80), 0)
    pix.set_rect(pix.irect, (30, 120, 200))
    pix.save(path)
    return path


def _make_pdf(path: Path, swatch: Path, pages: int = 2) -> None:
    doc = pymupdf.open()
    for page_no in range(pages):
        page = doc.new_page()
        page.insert_text((72, 72), f"page {page_no + 1}", fontsize=18)
        page.insert_image(pymupdf.Rect(72, 140, 272, 260), filename=str(swatch))
    doc.save(path)
    doc.close()


def test_each_pdf_gets_its_own_folder(tmp_path):
    repo = tmp_path / "repo"
    papers = repo / "papers"
    papers.mkdir(parents=True)
    swatch = _swatch(tmp_path / "swatch.png")
    _make_pdf(papers / "paper_01.pdf", swatch)
    _make_pdf(papers / "paper_02.pdf", swatch)

    results = [convert_pdf_to_markdown((papers / name).as_posix(), workspace_root=repo.as_posix())
               for name in ("paper_01.pdf", "paper_02.pdf")]

    for result, stem in zip(results, ("paper_01", "paper_02"), strict=True):
        assert result["success"] is True, result
        md = Path(result["markdown_path"])
        assert md == repo / "extracted" / stem / f"{stem}.md"
        assert md.parent == Path(result["image_dir"])
        assert result["image_count"] == 2
        assert result["images"] == ["image-001.png", "image-002.png"]
        for image in result["images"]:
            assert (md.parent / image).is_file()

    # nothing beside the source PDFs
    assert sorted(p.name for p in papers.iterdir()) == ["paper_01.pdf", "paper_02.pdf"]


def test_markdown_references_are_relative(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    swatch = _swatch(tmp_path / "swatch.png")
    pdf = tmp_path / "paper.pdf"
    _make_pdf(pdf, swatch, pages=1)

    result = convert_pdf_to_markdown(pdf.as_posix(), workspace_root=repo.as_posix())
    assert result["success"] is True
    assert "![](image-001.png)" in result["markdown_content"]
    assert str(tmp_path) not in result["markdown_content"]


def test_pdf_outside_the_workspace_still_lands_in_it(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    outside = tmp_path / "outside"
    outside.mkdir()
    swatch = _swatch(tmp_path / "swatch.png")
    _make_pdf(outside / "external.pdf", swatch, pages=1)

    result = convert_pdf_to_markdown((outside / "external.pdf").as_posix(), workspace_root=repo.as_posix())

    assert result["success"] is True
    assert Path(result["markdown_path"]) == repo / "extracted" / "external" / "external.md"
    assert not any(p.suffix in {".png", ".md"} for p in outside.iterdir())


def test_filename_with_spaces_and_special_characters(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    swatch = _swatch(tmp_path / "swatch.png")
    pdf = tmp_path / "nama jurnal (2024) & co.pdf"
    _make_pdf(pdf, swatch, pages=1)

    result = convert_pdf_to_markdown(pdf.as_posix(), workspace_root=repo.as_posix())

    assert result["success"] is True
    folder = repo / "extracted" / "nama jurnal (2024) & co"
    assert Path(result["markdown_path"]) == folder / "nama jurnal (2024) & co.md"
    for image in result["images"]:
        assert (folder / image).is_file()


def test_existing_extraction_is_not_replaced_without_overwrite(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    swatch = _swatch(tmp_path / "swatch.png")
    pdf = tmp_path / "paper.pdf"
    _make_pdf(pdf, swatch, pages=1)

    first = convert_pdf_to_markdown(pdf.as_posix(), workspace_root=repo.as_posix())
    assert first["success"] is True
    md = Path(first["markdown_path"])
    md.write_text("do not lose me", encoding="utf-8")

    blocked = convert_pdf_to_markdown(pdf.as_posix(), workspace_root=repo.as_posix())
    assert blocked["success"] is False
    assert md.read_text(encoding="utf-8") == "do not lose me"

    replaced = convert_pdf_to_markdown(pdf.as_posix(), workspace_root=repo.as_posix(), overwrite=True)
    assert replaced["success"] is True
    assert md.read_text(encoding="utf-8") != "do not lose me"
    assert replaced["images"] == ["image-001.png"]


def test_undetectable_workspace_errors(tmp_path, monkeypatch):
    monkeypatch.setattr(workspace, "find_repo_root", lambda start: None)
    monkeypatch.setattr(workspace.Path, "home", staticmethod(lambda: tmp_path))
    monkeypatch.chdir(tmp_path)
    swatch = _swatch(tmp_path / "swatch.png")
    pdf = tmp_path / "paper.pdf"
    _make_pdf(pdf, swatch, pages=1)

    result = convert_pdf_to_markdown(pdf.as_posix())

    assert result["success"] is False
    assert "could not be detected" in result["error"]
    assert not (tmp_path / "extracted").exists()


def test_explicit_paths_keep_upstream_behaviour(tmp_path):
    swatch = _swatch(tmp_path / "swatch.png")
    pdf = tmp_path / "paper.pdf"
    _make_pdf(pdf, swatch, pages=1)
    images = tmp_path / "images"
    md = tmp_path / "out.md"

    result = convert_pdf_to_markdown(pdf.as_posix(), image_path=images.as_posix(), save_path=md.as_posix())

    assert result == {"success": True, "markdown_path": md.as_posix()}
    assert md.is_file()
    # upstream naming is preserved when the caller owns the directory
    assert any(p.name.startswith("paper.pdf-") for p in images.iterdir())
    assert not (tmp_path / "extracted").exists()


@pytest.mark.parametrize("output_dir", ["extracted", "research/extracted"])
def test_output_dir_nesting(tmp_path, output_dir):
    repo = tmp_path / "repo"
    repo.mkdir()
    swatch = _swatch(tmp_path / "swatch.png")
    pdf = tmp_path / "paper.pdf"
    _make_pdf(pdf, swatch, pages=1)

    result = convert_pdf_to_markdown(pdf.as_posix(), workspace_root=repo.as_posix(), output_dir=output_dir)

    assert result["success"] is True
    assert Path(result["markdown_path"]) == repo / output_dir / "paper" / "paper.md"
