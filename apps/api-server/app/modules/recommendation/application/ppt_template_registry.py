from __future__ import annotations

from dataclasses import dataclass

from app.common.contracts import AppError


@dataclass(frozen=True, slots=True)
class PptTemplateDefinition:
    code: str
    name: str
    description: str
    version: str
    preview_url: str | None


# These are product-owned, code-rendered layouts.  They intentionally do not point
# at BidProjectFile or any arbitrary local path.  The source business decks are not
# distributable repository assets; deployment may add approved assets later without
# changing the frozen code/version contract below.
PPT_TEMPLATES: tuple[PptTemplateDefinition, ...] = (
    PptTemplateDefinition(
        "SYSTEM_DEFAULT", "系统默认版", "白底商品参数与主图版式", "1",
        "/ppt-template-previews/system-default.svg",
    ),
    PptTemplateDefinition(
        "JD_DETAIL_RED", "京东红白商品详版", "红白封面与商品图文分栏", "1",
        "/ppt-template-previews/jd-detail-red.svg",
    ),
    PptTemplateDefinition(
        "JD_FESTIVE_RED", "京东节庆红色版", "节庆红色封面和商品信息页", "1",
        "/ppt-template-previews/jd-festive-red.svg",
    ),
    PptTemplateDefinition(
        "CATALOG_MINIMAL", "极简商品画册版", "大幅商品图与右侧参数", "1",
        "/ppt-template-previews/catalog-minimal.svg",
    ),
    PptTemplateDefinition(
        "UNION_QUOTE_WHITE", "工会简洁报价版", "左侧报价参数、中央分隔线与右侧主图", "1",
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
