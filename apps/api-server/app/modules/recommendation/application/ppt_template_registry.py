from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from app.common.contracts import AppError
from app.core.config import PROJECT_ROOT, get_settings
from app.modules.recommendation.application.ppt_template_manifest import PPTX_SLOT_MANIFESTS


@dataclass(frozen=True, slots=True)
class PptTemplateDefinition:
    code: str
    name: str
    description: str
    version: str
    preview_url: str | None


# The four business assets are private, authorised deployment assets. They are never
# checked into this repository and cannot be selected through a user-provided path.
PPT_TEMPLATES: tuple[PptTemplateDefinition, ...] = (
    PptTemplateDefinition(
        "SYSTEM_DEFAULT",
        "系统默认版",
        "白底商品参数与主图版式",
        "1",
        "/ppt-template-previews/system-default.svg",
    ),
    PptTemplateDefinition(
        "JD_DETAIL_RED",
        "京东红白商品详版",
        "红白封面与商品图文分栏",
        "3",
        "/ppt-template-previews/jd-detail-red.svg",
    ),
    PptTemplateDefinition(
        "JD_FESTIVE_RED",
        "京东节庆红色版",
        "节庆红色封面和商品信息页",
        "3",
        "/ppt-template-previews/jd-festive-red.svg",
    ),
    PptTemplateDefinition(
        "CATALOG_MINIMAL",
        "极简商品画册版",
        "大幅商品图与右侧参数",
        "3",
        "/ppt-template-previews/catalog-minimal.svg",
    ),
    PptTemplateDefinition(
        "UNION_QUOTE_WHITE",
        "工会简洁报价版",
        "左侧报价参数、中央分隔线与右侧主图",
        "3",
        "/ppt-template-previews/union-quote-white.svg",
    ),
)


def list_ppt_templates() -> tuple[PptTemplateDefinition, ...]:
    return PPT_TEMPLATES


def get_ppt_template(code: str | None) -> PptTemplateDefinition:
    normalized = (code or "SYSTEM_DEFAULT").strip().upper()
    for template in PPT_TEMPLATES:
        if template.code == normalized:
            return template
    raise AppError("PPT_TEMPLATE_INVALID", "不支持的 PPT 模板编号", 422)


def resolve_ppt_template_asset(template: PptTemplateDefinition) -> Path:
    """Return an approved business template, or fail explicitly without fallback."""
    manifest = PPTX_SLOT_MANIFESTS.get(template.code)
    if manifest is None:
        raise AppError("PPT_TEMPLATE_ASSET_UNAVAILABLE", "所选 PPT 模板资产不可用", 409)
    if template.version != manifest.asset_version:
        raise AppError("PPT_TEMPLATE_ASSET_VERSION_MISMATCH", "PPT 模板资产版本不匹配", 409)
    settings = get_settings()
    asset_root = settings.ppt_template_asset_dir
    if asset_root is None and settings.app_env.lower() in {"development", "test"}:
        asset_root = PROJECT_ROOT / ".codex-assets" / "ppt-template-sources"
    path = asset_root / manifest.clean_filename if asset_root is not None else None
    if path is None or not path.is_file():
        raise AppError("PPT_TEMPLATE_ASSET_UNAVAILABLE", "所选 PPT 模板资产不可用", 409)
    return path


def is_ppt_template_available(template: PptTemplateDefinition) -> bool:
    """Report whether this deployment can render the requested built-in template."""
    if template.code == "SYSTEM_DEFAULT":
        return True
    try:
        resolve_ppt_template_asset(template)
    except AppError:
        return False
    return True
