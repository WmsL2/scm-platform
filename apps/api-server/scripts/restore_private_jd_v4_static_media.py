"""Restore audited static JD media to the private v4 candidate only.

The source is the already-clean private v3 deck, never the customer original.
It restores media referenced by masters/layouts; named slide image slots remain
transparent because they are dynamic product media.
"""

from __future__ import annotations

from pathlib import Path
from tempfile import NamedTemporaryFile
from zipfile import ZIP_DEFLATED, ZipFile

ROOT = Path(__file__).resolve().parents[3]
SOURCE = ROOT / ".codex-assets" / "ppt-template-sources" / "JD_DETAIL_RED_CLEAN_v3.pptx"
TARGET = ROOT / ".codex-assets" / "ppt-v4-review" / "JD_DETAIL_RED_CLEAN_v4.pptx"
OUTPUT = ROOT / ".codex-assets" / "ppt-v4-review" / "JD_DETAIL_RED_CLEAN_v4-static-media.pptx"

MEDIA_MAP = {
    "image2.png": "image2.png",
    "image3.png": "image3.png",
    "image4.png": "image4.png",
    "image6.png": "image6.png",
    "image7.png": "image7.png",
}

RELATION_TARGETS = {
    "ppt/slideLayouts/_rels/slideLayout12.xml.rels": ("image1.png", "image1.jpeg"),
    "ppt/slideLayouts/_rels/slideLayout13.xml.rels": ("image1.png", "image1.jpeg"),
    "ppt/slideLayouts/_rels/slideLayout15.xml.rels": ("image5.png", "image5.jpeg"),
}


def main() -> None:
    if not SOURCE.is_file() or not TARGET.is_file():
        raise SystemExit("private JD source or v4 candidate is unavailable")
    with ZipFile(SOURCE) as clean, ZipFile(TARGET) as candidate:
        source_media = {name: clean.read(f"ppt/media/{name}") for name in MEDIA_MAP.values()}
        source_media["image1.jpeg"] = clean.read("ppt/media/image1.jpeg")
        source_media["image5.jpeg"] = clean.read("ppt/media/image5.jpeg")
        with NamedTemporaryFile(delete=False, suffix=".pptx", dir=OUTPUT.parent) as temporary:
            temporary_path = Path(temporary.name)
        try:
            with ZipFile(temporary_path, "w", ZIP_DEFLATED) as output:
                for member in candidate.infolist():
                    data = candidate.read(member.filename)
                    if member.filename in {"ppt/media/image1.png", "ppt/media/image5.png"}:
                        continue
                    if member.filename.startswith("ppt/media/"):
                        name = member.filename.rsplit("/", 1)[-1]
                        if name in MEDIA_MAP:
                            data = source_media[MEDIA_MAP[name]]
                    if member.filename in RELATION_TARGETS:
                        old, new = RELATION_TARGETS[member.filename]
                        data = data.replace(old.encode(), new.encode())
                    output.writestr(member, data)
                output.writestr("ppt/media/image1.jpeg", source_media["image1.jpeg"])
                output.writestr("ppt/media/image5.jpeg", source_media["image5.jpeg"])
            temporary_path.replace(OUTPUT)
        finally:
            temporary_path.unlink(missing_ok=True)


if __name__ == "__main__":
    main()
