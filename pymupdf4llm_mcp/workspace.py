"""Workspace-scoped output layout for extracted PDFs.

Every PDF gets its own folder under ``<workspace>/extracted/<pdf-stem>/`` holding
the markdown file and all extracted images, with relative image references.
"""

from __future__ import annotations

import os
import re
import threading
from contextlib import contextmanager
from pathlib import Path
from urllib.parse import quote, unquote

IMAGE_REF = re.compile(r"(!\[[^\]]*\]\()([^)]+)(\))")
_UNSAFE = re.compile(r'[\x00-\x1f<>:"|?*]')
_CONVERT_LOCK = threading.Lock()


@contextmanager
def stable_cwd(path: Path):
    """Run inside ``path`` while pymupdf4llm writes its images.

    pymupdf4llm builds image references relative to the process cwd and applies
    its character sanitisation to the whole path, so an output folder (or
    workspace) containing spaces makes it save to a path that does not exist.
    Serialised, because cwd is process-global.
    """
    with _CONVERT_LOCK:
        previous = Path.cwd()
        os.chdir(path)
        try:
            yield
        finally:
            os.chdir(previous)


def find_repo_root(start: Path) -> Path | None:
    """Walk up looking for a .git entry (works for worktrees, where it is a file)."""
    for candidate in (start, *start.parents):
        if (candidate / ".git").exists():
            return candidate
    return None


def detect_workspace(explicit: str | None, pdf: Path) -> Path | None:
    """Resolve the repository root, preferring explicit input over heuristics.

    MCP clients often start servers with cwd set to $HOME, so $HOME is never
    accepted as a workspace: callers must be explicit instead of scattering
    output outside the project.
    """
    for candidate in (
        explicit,
        os.environ.get("PYMUPDF4LLM_WORKSPACE"),
        os.environ.get("OPENCODE_PROJECT_DIR"),
        os.environ.get("OPENCODE_DIRECTORY"),
    ):
        if candidate and Path(candidate).expanduser().is_dir():
            return Path(candidate).expanduser().resolve()

    cwd = Path.cwd().resolve()
    for start in (cwd, *pdf.parents):
        root = find_repo_root(start)
        if root:
            return root.resolve()

    if cwd != Path.home().resolve():
        return cwd
    return None


def safe_stem(pdf: Path) -> str:
    stem = _UNSAFE.sub("_", pdf.stem).strip().rstrip(".")
    return stem or "document"


def prepare_output(root: Path, output_dir: str, stem: str, overwrite: bool) -> tuple[Path, str | None]:
    dest = (root / output_dir.lstrip("/\\") / stem).resolve()
    if dest.exists() and any(dest.iterdir()):
        if not overwrite:
            return dest, f"Extraction already exists: {dest}. Pass overwrite=true to replace it."
        for stale in dest.iterdir():
            if stale.is_file():
                stale.unlink()
    dest.mkdir(parents=True, exist_ok=True)
    return dest, None


def renumber_images(folder: Path) -> dict[str, str]:
    """Rename images to image-001.png, ... and return an old->new name map."""
    files = sorted(p for p in folder.iterdir() if p.is_file() and p.suffix.lower() != ".md")
    renamed: dict[str, str] = {}
    for index, path in enumerate(files, 1):
        new = folder / f"image-{index:03d}{path.suffix.lower()}"
        path.rename(new)
        renamed[path.name] = new.name
    return renamed


def md_ref(name: str) -> str:
    """Portable markdown link target: encode spaces and parentheses."""
    return quote(name, safe="._-~!$&'*+,;=@")


def rewrite_refs(markdown: str, folder: Path, renamed: dict[str, str]) -> tuple[str, list[str], list[str]]:
    """Point every image reference at the file actually written in ``folder``.

    pymupdf4llm emits absolute or cwd-relative paths depending on where the
    process runs, so references are reduced to bare filenames here.
    """
    written = {p.name for p in folder.iterdir() if p.is_file() and p.suffix != ".md"}

    def replace(match: re.Match[str]) -> str:
        target = unquote(match.group(2)).replace("\\", "/").rsplit("/", 1)[-1]
        target = renamed.get(target, target)
        if target not in written:
            return match.group(0)
        return f"{match.group(1)}{md_ref(target)}{match.group(3)}"

    rewritten = IMAGE_REF.sub(replace, markdown)
    refs = [unquote(m.group(2)) for m in IMAGE_REF.finditer(rewritten)]
    missing = [ref for ref in refs if not (folder / ref).is_file()]
    return rewritten, refs, missing
