"""ساخت بایگانی تحویل (rang-project.zip) از وضعیت نهایی پروژه.

شامل backend، frontend، deploy، exels (با converted/) و فایل‌های ریشه.
شامل نمی‌شود: .git، .env، دیتابیس‌ها، __pycache__، venv و فایل‌های ابزار محلی.

اجرا:  python make_release_zip.py
"""
from __future__ import annotations

import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "rang-project.zip"

INCLUDE_DIRS = ["backend", "frontend", "deploy", "exels"]
INCLUDE_FILES = ["convert_exels.py", "make_release_zip.py", "README.md", "CHANGELOG.md", "LICENSE", "netlify.toml", ".gitignore"]

EXCLUDE_DIR_NAMES = {"__pycache__", ".venv", "venv", "env", ".git", "node_modules", ".pytest_cache"}
EXCLUDE_SUFFIXES = {".pyc", ".pyo", ".db", ".sqlite", ".sqlite3", ".log"}
EXCLUDE_NAMES = {".env", ".env.local", "SesionMiMo.json", "Thumbs.db", ".DS_Store"}


def allowed(path: Path) -> bool:
    if path.name in EXCLUDE_NAMES:
        return False
    if path.suffix.lower() in EXCLUDE_SUFFIXES:
        return False
    return not any(part in EXCLUDE_DIR_NAMES for part in path.parts)


def main() -> None:
    entries: list[Path] = []
    for d in INCLUDE_DIRS:
        base = ROOT / d
        if base.is_dir():
            entries.extend(p for p in base.rglob("*") if p.is_file() and allowed(p.relative_to(ROOT)))
    for f in INCLUDE_FILES:
        p = ROOT / f
        if p.is_file():
            entries.append(p)

    entries.sort(key=lambda p: str(p).lower())
    with zipfile.ZipFile(OUT, "w", zipfile.ZIP_DEFLATED) as zf:
        for p in entries:
            zf.write(p, arcname=str(Path("Rang") / p.relative_to(ROOT)))

    print(f"{OUT.name}: {len(entries)} فایل، {OUT.stat().st_size / 1024:.0f} KB")


if __name__ == "__main__":
    main()
