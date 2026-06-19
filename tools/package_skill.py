#!/usr/bin/env python3
"""Package this repository as an Agent Skill zip."""

from __future__ import annotations

from pathlib import Path
import shutil
import zipfile


ROOT = Path(__file__).resolve().parents[1]
SKILL_NAME = "youtube-video-context"
DIST = ROOT / "dist"
ARCHIVE = DIST / f"{SKILL_NAME}.zip"

INCLUDE = [
    "SKILL.md",
    "agents",
    "references",
    "scripts/ingest_youtube_video.py",
]


def add_path(archive: zipfile.ZipFile, source: Path, arc_prefix: Path) -> None:
    if source.is_dir():
        for child in sorted(source.rglob("*")):
            if child.is_file() and "__pycache__" not in child.parts:
                archive.write(child, arc_prefix / child.relative_to(ROOT))
        return
    archive.write(source, arc_prefix / source.relative_to(ROOT))


def main() -> int:
    DIST.mkdir(exist_ok=True)
    if ARCHIVE.exists():
        ARCHIVE.unlink()

    with zipfile.ZipFile(ARCHIVE, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for item in INCLUDE:
            add_path(archive, ROOT / item, Path(SKILL_NAME))

    print(ARCHIVE)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
