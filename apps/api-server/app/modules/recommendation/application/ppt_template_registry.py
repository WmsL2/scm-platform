from __future__ import annotations

from dataclasses import dataclass, replace
from pathlib import Path

from app.common.contracts import AppError
from app.core.config import PROJECT_ROOT, get_settings
from app.modules.recommendation.application.ppt_template_manifest import get_pptx_manifest


@dataclass(frozen=True, slots=True)
class PptTemplateDefinition:
    code: str
    name: str
    description: str
    version: str
    preview_url: str | None
    single_product_only: bool = False


# The four business assets are reviewed, public distribution assets. They cannot be
# selected through a user-provided path; deployments may only override their root.
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

PPT_V5_TEMPLATES: tuple[PptTemplateDefinition, ...] = (
    PptTemplateDefinition(
        "JD_DETAIL_RED",
        "京东红白商品详版",
        "正式客户版，当前仅支持单品生成",
        "5",
        "/ppt-template-previews/jd-detail-red.svg",
        single_product_only=True,
    ),
    PptTemplateDefinition(
        "JD_FESTIVE_RED",
        "京东节庆红色版",
        "正式两页客户版，当前仅支持单品生成",
        "5",
        "/ppt-template-previews/jd-festive-red.svg",
        single_product_only=True,
    ),
    PptTemplateDefinition(
        "UNION_QUOTE_WHITE",
        "工会简洁报价版",
        "正式客户版，支持单品与 2 至 4 件组合方案",
        "5",
        "/ppt-template-previews/union-quote-white.svg",
        single_product_only=False,
    ),
)


def is_local_v5_default_enabled() -> bool:
    """Allow the local replacement only in an explicit development environment."""
    settings = get_settings()
    return (
        settings.app_env.strip().lower() in {"development", "dev", "local"}
        and settings.ppt_local_v5_default_enabled
    )


def list_ppt_templates() -> tuple[PptTemplateDefinition, ...]:
    if not is_local_v5_default_enabled():
        return PPT_TEMPLATES
    replacements = {template.code: template for template in PPT_V5_TEMPLATES}
    return tuple(replacements.get(template.code, template) for template in PPT_TEMPLATES)


def get_ppt_template(code: str | None, version: str | None = None) -> PptTemplateDefinition:
    normalized = (code or "SYSTEM_DEFAULT").strip().upper()
    choices = [
        template
        for template in PPT_TEMPLATES + PPT_V5_TEMPLATES
        if template.code == normalized
    ]
    if choices:
        if version is None:
            if is_local_v5_default_enabled():
                local_v5 = next(
                    (template for template in choices if template.version == "5"),
                    None,
                )
                if local_v5 is not None:
                    return local_v5
            return choices[0]
        for template in choices:
            if version == template.version:
                return template
        if get_pptx_manifest(normalized, version) is not None:
            return replace(choices[0], version=version)
        raise AppError("PPT_TEMPLATE_VERSION_UNAVAILABLE", "所选 PPT 模板版本不可用", 409)
    raise AppError("PPT_TEMPLATE_INVALID", "不支持的 PPT 模板编号", 422)


def is_ppt_template_enabled_for_new_task(template: PptTemplateDefinition) -> bool:
    """Gate v5 task creation without invalidating persisted historical tasks."""
    return template.version != "5" or get_settings().ppt_v5_preview_enabled


def resolve_ppt_template_asset(template: PptTemplateDefinition) -> Path:
    """Return an approved business template, or fail explicitly without fallback."""
    manifest = get_pptx_manifest(template.code, template.version)
    if manifest is None:
        raise AppError("PPT_TEMPLATE_ASSET_UNAVAILABLE", "所选 PPT 模板资产不可用", 409)
    if template.version != manifest.asset_version:
        raise AppError("PPT_TEMPLATE_ASSET_VERSION_MISMATCH", "PPT 模板资产版本不匹配", 409)
    settings = get_settings()
    # Explicit deployment configuration is strict, so a mount/configuration error
    # continues to fail safely rather than falling back to another source or version.
    # Approved versioned assets, including v5, ship in the repository by default.
    asset_root = settings.ppt_template_asset_dir
    if asset_root is None:
        asset_root = PROJECT_ROOT / "assets" / "ppt-templates"
    path = asset_root / manifest.clean_filename if asset_root is not None else None
    if path is None or not path.is_file():
        raise AppError("PPT_TEMPLATE_ASSET_UNAVAILABLE", "所选 PPT 模板资产不可用", 409)
    return path


def is_ppt_template_available(template: PptTemplateDefinition) -> bool:
    """Report whether this deployment can render the requested built-in template."""
    if template.code == "SYSTEM_DEFAULT":
        return True
    if not is_ppt_template_enabled_for_new_task(template):
        return False
    try:
        resolve_ppt_template_asset(template)
    except AppError:
        return False
    return True
