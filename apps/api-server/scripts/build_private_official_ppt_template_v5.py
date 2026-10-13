"""Create the private runtime asset for formal Type-5 template 1.

This script must run only in an authorised private workspace.  It never writes
the original or any customer asset into version control.
"""

from __future__ import annotations

from os import replace
from pathlib import Path
from tempfile import NamedTemporaryFile

from app.modules.recommendation.application.ppt_official_template_v5 import (
    standardize_jd_detail_red_v5,
    validate_jd_detail_red_v5_runtime,
    verify_no_sample_media,
)
from app.modules.recommendation.application.ppt_template_manifest import get_pptx_manifest


def build_runtime_asset(original: Path, runtime: Path) -> None:
    """Validate a private candidate completely before atomically publishing it."""
    manifest = get_pptx_manifest("JD_DETAIL_RED", "5")
    if manifest is None:
        raise RuntimeError("JD_DETAIL_RED v5 manifest is unavailable")
    runtime.parent.mkdir(parents=True, exist_ok=True)
    with NamedTemporaryFile(dir=runtime.parent, suffix=".pptx", delete=False) as handle:
        candidate = Path(handle.name)
    try:
        standardize_jd_detail_red_v5(original, candidate)
        verify_no_sample_media(original, candidate)
        validate_jd_detail_red_v5_runtime(candidate, manifest)
        replace(candidate, runtime)
    except Exception:
        candidate.unlink(missing_ok=True)
        raise


def main() -> None:
    root = Path(__file__).resolve().parents[3]
    original = root / ".codex-assets" / "official-ppt" / "originals" / "模版1.pptx"
    runtime = (
        root / ".codex-assets" / "official-ppt" / "runtime" / "JD_DETAIL_RED_OFFICIAL_CLEAN_v5.pptx"
    )
    if not original.is_file():
        raise SystemExit(f"private original is unavailable: {original}")
    build_runtime_asset(original, runtime)
    print(runtime)


if __name__ == "__main__":
    main()
