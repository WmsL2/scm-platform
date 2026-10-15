from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "apps" / "api-server"))

from app.modules.recommendation.application.ppt_official_template4_v5 import (
    standardize_union_quote_white_v5,
    verify_no_sample_media,
)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Build private UNION_QUOTE_WHITE v5 runtime asset"
    )
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--specification", type=Path, required=True)
    parser.add_argument(
        "--output",
        type=Path,
        default=ROOT
        / ".codex-assets"
        / "local-v5-runtime"
        / "ppt-templates"
        / "UNION_QUOTE_WHITE_OFFICIAL_CLEAN_v5.pptx",
    )
    args = parser.parse_args()
    standardize_union_quote_white_v5(args.source, args.specification, args.output)
    verify_no_sample_media(args.source, args.output)
    print(args.output.resolve())


if __name__ == "__main__":
    main()
