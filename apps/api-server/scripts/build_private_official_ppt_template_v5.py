"""Create private runtime assets for the formal Type-5 templates.

This script must run only in an authorised private workspace.  It never writes
the original or any customer asset into version control.
"""

from __future__ import annotations

from argparse import ArgumentParser
from os import replace
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Callable

from app.modules.recommendation.application.ppt_official_template_catalog_v5 import (
    standardize_catalog_minimal_v5,
    validate_catalog_minimal_v5_runtime,
)
from app.modules.recommendation.application.ppt_official_template_catalog_v5 import (
    verify_no_sample_media as verify_no_catalog_sample_media,
)
from app.modules.recommendation.application.ppt_official_template_festive_v5 import (
    standardize_jd_festive_red_v5,
    validate_jd_festive_red_v5_runtime,
)
from app.modules.recommendation.application.ppt_official_template_festive_v5 import (
    verify_no_sample_media as verify_no_festive_sample_media,
)
from app.modules.recommendation.application.ppt_official_template_v5 import (
    standardize_jd_detail_red_v5,
    validate_jd_detail_red_v5_runtime,
    verify_no_sample_media,
)
from app.modules.recommendation.application.ppt_template_manifest import (
    PptxSlotManifest,
    get_pptx_manifest,
)


def _build_atomic_runtime_asset(
    original: Path,
    runtime: Path,
    *,
    code: str,
    standardize: Callable[[Path, Path], None],
    verify_media: Callable[[Path, Path], None],
    validate_runtime: Callable[[Path, PptxSlotManifest], None],
) -> None:
    """Validate a private candidate completely before atomically publishing it."""
    manifest = get_pptx_manifest(code, "5")
    if manifest is None:
        raise RuntimeError(f"{code} v5 manifest is unavailable")
    runtime.parent.mkdir(parents=True, exist_ok=True)
    with NamedTemporaryFile(dir=runtime.parent, suffix=".pptx", delete=False) as handle:
        candidate = Path(handle.name)
    try:
        standardize(original, candidate)
        verify_media(original, candidate)
        validate_runtime(candidate, manifest)
        replace(candidate, runtime)
    except Exception:
        candidate.unlink(missing_ok=True)
        raise


def build_runtime_asset(original: Path, runtime: Path) -> None:
    """Build template 1 while retaining its existing private build entry point."""
    _build_atomic_runtime_asset(
        original,
        runtime,
        code="JD_DETAIL_RED",
        standardize=standardize_jd_detail_red_v5,
        verify_media=verify_no_sample_media,
        validate_runtime=validate_jd_detail_red_v5_runtime,
    )


def build_jd_festive_red_v5_runtime_asset(original: Path, runtime: Path) -> None:
    """Build the cleaned template 2 asset only after its media contract passes."""
    _build_atomic_runtime_asset(
        original,
        runtime,
        code="JD_FESTIVE_RED",
        standardize=standardize_jd_festive_red_v5,
        verify_media=verify_no_festive_sample_media,
        validate_runtime=validate_jd_festive_red_v5_runtime,
    )


def build_catalog_minimal_v5_runtime_asset(original: Path, runtime: Path) -> None:
    """Build template 3 only inside an authorised private workspace."""
    _build_atomic_runtime_asset(
        original,
        runtime,
        code="CATALOG_MINIMAL",
        standardize=standardize_catalog_minimal_v5,
        verify_media=verify_no_catalog_sample_media,
        validate_runtime=validate_catalog_minimal_v5_runtime,
    )


def main() -> None:
    parser = ArgumentParser()
    parser.add_argument(
        "--template-code",
        choices=("JD_DETAIL_RED", "JD_FESTIVE_RED", "CATALOG_MINIMAL"),
        default="JD_DETAIL_RED",
    )
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[3]
    filenames = {
        "JD_DETAIL_RED": ("模版1.pptx", "JD_DETAIL_RED_OFFICIAL_CLEAN_v5.pptx"),
        "JD_FESTIVE_RED": ("模版2.pptx", "JD_FESTIVE_RED_OFFICIAL_CLEAN_v5.pptx"),
        "CATALOG_MINIMAL": ("模版3.pptx", "CATALOG_MINIMAL_OFFICIAL_CLEAN_v5.pptx"),
    }
    original_filename, runtime_filename = filenames[args.template_code]
    original = root / ".codex-assets" / "official-ppt" / "originals" / original_filename
    runtime = root / ".codex-assets" / "official-ppt" / "runtime" / runtime_filename
    if not original.is_file():
        raise SystemExit(f"private original is unavailable: {original}")
    if args.template_code == "JD_FESTIVE_RED":
        build_jd_festive_red_v5_runtime_asset(original, runtime)
    elif args.template_code == "CATALOG_MINIMAL":
        build_catalog_minimal_v5_runtime_asset(original, runtime)
    else:
        build_runtime_asset(original, runtime)
    print(runtime)


if __name__ == "__main__":
    main()
