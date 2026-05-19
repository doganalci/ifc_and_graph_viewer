"""Dataset kök yolu ve türetilmiş alt yolların çözümlenmesi."""
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()


@dataclass
class DatasetPaths:
    root: Path
    db: Path
    ifc_dir: Path
    baseline_dir: Path
    violated_dir: Path
    imports_dir: Path
    exports_dir: Path
    data_dir: Path

    @property
    def is_valid(self) -> bool:
        return self.db.exists()

    @classmethod
    def from_root(cls, root: str | Path) -> "DatasetPaths":
        r = Path(root).expanduser().resolve()
        return cls(
            root=r,
            db=r / "violation_pool.sqlite",
            ifc_dir=r / "ifc_models",
            baseline_dir=r / "ifc_models" / "baseline",
            violated_dir=r / "ifc_models" / "violated",
            imports_dir=r / "ifc_models" / "imports",
            exports_dir=r / "exports",
            data_dir=r / "data",
        )


def default_root() -> str:
    return os.getenv("VIEWER_DATASET_ROOT", "../codex1")


def codex1_candidates() -> list[Path]:
    """Komşu codex1 deposunun olası yerleri (en olası ilk)."""
    here = Path(__file__).resolve().parent.parent
    return [
        here.parent / "codex1",
        here / ".." / "codex1",
        Path.cwd() / ".." / "codex1",
        Path("/home/user/codex1"),
    ]


def first_valid_codex1() -> Path | None:
    for c in codex1_candidates():
        p = DatasetPaths.from_root(c)
        if p.is_valid:
            return p.root
    return None


def find_run_export(paths: "DatasetPaths", run_id: str) -> Path | None:
    """exports/violations_<name>_<id[:8]>.xlsx eşleşmesini bul."""
    if not paths.exports_dir.exists():
        return None
    prefix = run_id[:8]
    for f in paths.exports_dir.glob(f"violations_*_{prefix}.xlsx"):
        return f
    return None


def resolve_artifact(paths: DatasetPaths, file_path: str | None) -> Path | None:
    """Codex1 görece yollarını dataset köküne göre çöz."""
    if not file_path:
        return None
    p = Path(file_path)
    if p.is_absolute() and p.exists():
        return p
    candidate = (paths.root / p).resolve()
    if candidate.exists():
        return candidate
    name = Path(file_path).name
    for d in (paths.violated_dir, paths.baseline_dir, paths.imports_dir):
        c = d / name
        if c.exists():
            return c
    return None
