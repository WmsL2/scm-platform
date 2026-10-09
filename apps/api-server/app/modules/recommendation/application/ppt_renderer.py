from __future__ import annotations

from collections.abc import Mapping
from decimal import Decimal, InvalidOperation
from io import BytesIO
from pathlib import Path
from typing import Any

from PIL import Image, UnidentifiedImageError
from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import MSO_ANCHOR, PP_ALIGN
from pptx.util import Inches, Pt

from app.common.contracts import AppError
from app.modules.recommendation.application.ppt_template_registry import get_ppt_template

_DARK = RGBColor(31, 45, 61)  # type: ignore[no-untyped-call]
_GREY = RGBColor(96, 112, 128)  # type: ignore[no-untyped-call]
_LINE = RGBColor(146, 156, 168)  # type: ignore[no-untyped-call]
_FONT = "Microsoft YaHei"
_SLIDE_WIDTH = Inches(13.333333)
_SLIDE_HEIGHT = Inches(7.5)


class PptRenderer:
    """Render the fixed, editable product-page format used by Type-5 proposals.

    The system default follows the supplied customer references: white 16:9 canvas,
    title at the top, specifications on the left, a vertical divider, and product
    imagery on the right. Each confirmed product or package owns one page. A customer
    template is retained and generated pages are appended after it.
    """

    def render(
        self,
        source: Mapping[str, object],
        *,
        template_path: Path | None = None,
        product_images: Mapping[str, bytes] | None = None,
        template_code: str = "SYSTEM_DEFAULT",
        template_version: str | None = None,
    ) -> bytes:
        template = get_ppt_template(template_code)
        if template_version is not None and template.version != template_version:
            raise AppError("PPT_TEMPLATE_VERSION_UNAVAILABLE", "所选 PPT 模板版本不可用", 409)
        self._template_code = template.code
        presentation = Presentation(str(template_path)) if template_path else Presentation()
        if template_path is None:
            presentation.slide_width = _SLIDE_WIDTH
            presentation.slide_height = _SLIDE_HEIGHT

        images = product_images or {}
        if template.code != "SYSTEM_DEFAULT":
            self._add_cover(presentation, source, template.code, template.name)
        for package in self._mappings(source.get("packages")):
            self._add_package_page(presentation, package, images)
        for product in self._mappings(source.get("single_products")):
            self._add_product_page(presentation, product, images)

        output = BytesIO()
        presentation.save(output)
        return output.getvalue()

    @staticmethod
    def _mapping(value: object) -> Mapping[str, object]:
        return value if isinstance(value, Mapping) else {}

    @classmethod
    def _mappings(cls, value: object) -> list[Mapping[str, object]]:
        return [cls._mapping(item) for item in value] if isinstance(value, list) else []

    def _add_product_page(
        self,
        presentation: Any,
        item: Mapping[str, object],
        images: Mapping[str, bytes],
    ) -> None:
        product = self._mapping(item.get("product"))
        manual = self._mapping(item.get("manual"))
        prices = self._mapping(item.get("prices"))
        title = self._text_value(product, "product_name", "推荐商品")
        price_label, display_price = self._display_price(item)
        details = [
            ("SKU", self._text_value(product, "sku", "—")),
            ("品牌", self._text_value(product, "brand", "—")),
            ("型号", self._text_value(product, "model", "—")),
            ("商品配置", self._text_value(product, "product_specification", "—")),
            ("卖点", self._text_value(product, "selling_points", "待确认")),
            ("市场价", self._money(prices.get("market_price"))),
            ("京东价", self._money(prices.get("jd_price"))),
            ("协议价", self._money(prices.get("agreement_price"))),
            (price_label, display_price),
            ("配送", self._text_value(manual, "delivery_status", "以项目要求为准")),
            ("快递", self._text_value(product, "shipping_courier", "待确认")),
            ("质保", self._text_value(product, "warranty_period", "待确认")),
            ("库存", self._text_value(manual, "inventory_status", "待业务确认")),
            ("履约", self._text_value(manual, "fulfillment_cycle", "待业务确认")),
        ]
        evidence = self._text_value(manual, "evidence", "")
        if evidence:
            details.append(("备注", evidence))
        for page_no, page_details in enumerate(self._paginate_details(details), start=1):
            page_title = title if page_no == 1 else f"{title}（详情续页 {page_no}）"
            slide = self._base_page(presentation, page_title)
            self._add_left_details(slide, page_details)
            if page_no == 1:
                self._add_product_image(slide, images.get(self._text_value(product, "id", "")))

    def _add_package_page(
        self,
        presentation: Any,
        package: Mapping[str, object],
        images: Mapping[str, bytes],
    ) -> None:
        name = self._text_value(package, "name", "商品组合方案")
        items = self._mappings(package.get("items"))
        composition = (
            "\n".join(
                self._package_item_line(index, item) for index, item in enumerate(items, start=1)
            )
            or "—"
        )
        details = [
            ("套装组成", composition),
            ("价格档位", self._money(package.get("price_tier"))),
            ("套装总价", self._money(package.get("total_price"))),
            ("方案说明", self._text_value(package, "reason", "人工确认的组合方案")),
        ]
        image_bytes = [
            images.get(self._text_value(self._mapping(item.get("product_snapshot")), "id", ""))
            for item in items
        ]
        for page_no, page_details in enumerate(self._paginate_details(details), start=1):
            page_title = name if page_no == 1 else f"{name}（详情续页 {page_no}）"
            slide = self._base_page(presentation, page_title)
            self._add_left_details(slide, page_details)
            if page_no == 1:
                self._add_package_images(slide, [item for item in image_bytes if item])

    def _base_page(self, presentation: Any, title: str) -> Any:
        slide = presentation.slides.add_slide(presentation.slide_layouts[6])
        # The renderer stores the selected layout only for the duration of render().
        # It is deliberately not inferred from a file name or a user-provided path.
        code = getattr(self, "_template_code", "SYSTEM_DEFAULT")
        if code in {"JD_DETAIL_RED", "JD_FESTIVE_RED"}:
            return self._red_page(slide, title, festive=code == "JD_FESTIVE_RED")
        if code == "CATALOG_MINIMAL":
            return self._catalog_page(slide, title)
        if code == "UNION_QUOTE_WHITE":
            return self._union_page(slide, title)
        background = slide.background.fill
        background.solid()
        background.fore_color.rgb = RGBColor(255, 255, 255)  # type: ignore[no-untyped-call]
        title_size = 24 if len(title) <= 48 else 20
        self._text(slide, 0.17, 0.2, 11.6, 0.75, f"商品名称：{title}", title_size, _DARK)
        divider = slide.shapes.add_shape(
            MSO_SHAPE.RECTANGLE,
            Inches(5.58),
            Inches(0.75),
            Inches(0.01),
            Inches(6.0),
        )
        divider.fill.solid()
        divider.fill.fore_color.rgb = _LINE
        divider.line.fill.background()
        return slide

    def _add_cover(
        self, presentation: Any, source: Mapping[str, object], code: str, name: str
    ) -> None:
        slide = presentation.slides.add_slide(presentation.slide_layouts[6])
        project = self._mapping(source.get("project"))
        title = self._text_value(project, "project_name", "商品推荐方案")
        fill = slide.background.fill
        fill.solid()
        fill.fore_color.rgb = RGBColor(190, 25, 38) if "RED" in code else RGBColor(250, 250, 248)  # type: ignore[no-untyped-call]
        color = RGBColor(255, 255, 255) if "RED" in code else _DARK  # type: ignore[no-untyped-call]
        self._text(slide, 0.8, 2.35, 11.5, 0.7, title, 30, color, align=PP_ALIGN.CENTER)
        self._text(slide, 0.8, 3.25, 11.5, 0.35, name, 15, color, align=PP_ALIGN.CENTER)

    def _red_page(self, slide: Any, title: str, *, festive: bool) -> Any:
        fill = slide.background.fill
        fill.solid()
        if festive:
            fill.fore_color.rgb = RGBColor(168, 15, 32)  # type: ignore[no-untyped-call]
            for left, top, size in ((11.3, 0.0, 2.0), (0.0, 5.3, 2.2)):
                ornament = slide.shapes.add_shape(
                    MSO_SHAPE.OVAL, Inches(left), Inches(top), Inches(size), Inches(size)
                )
                ornament.fill.solid()
                ornament.fill.fore_color.rgb = RGBColor(204, 38, 49)  # type: ignore[no-untyped-call]
                ornament.line.fill.background()
            self._text(slide, 6.0, 0.52, 6.5, 0.5, title, 22, RGBColor(255, 255, 255))  # type: ignore[no-untyped-call]
            panel = slide.shapes.add_shape(
                MSO_SHAPE.ROUNDED_RECTANGLE,
                Inches(5.75),
                Inches(1.12),
                Inches(6.75),
                Inches(5.9),
            )
            panel.fill.solid()
            panel.fill.fore_color.rgb = RGBColor(255, 244, 230)  # type: ignore[no-untyped-call]
            panel.line.fill.background()
        else:
            fill.fore_color.rgb = RGBColor(255, 247, 247)  # type: ignore[no-untyped-call]
            banner = slide.shapes.add_shape(
                MSO_SHAPE.RECTANGLE, 0, 0, Inches(13.333), Inches(0.82)
            )
            banner.fill.solid()
            banner.fill.fore_color.rgb = RGBColor(190, 38, 38)  # type: ignore[no-untyped-call]
            banner.line.fill.background()
            self._text(slide, 0.45, 0.17, 12.0, 0.42, title, 22, RGBColor(255, 255, 255))  # type: ignore[no-untyped-call]
        return slide

    def _catalog_page(self, slide: Any, title: str) -> Any:
        fill = slide.background.fill
        fill.solid()
        fill.fore_color.rgb = RGBColor(250, 250, 248)  # type: ignore[no-untyped-call]
        self._text(slide, 6.35, 0.25, 5.7, 0.72, title, 20 if len(title) <= 42 else 16, _DARK)
        return slide

    def _union_page(self, slide: Any, title: str) -> Any:
        fill = slide.background.fill
        fill.solid()
        fill.fore_color.rgb = RGBColor(255, 255, 255)  # type: ignore[no-untyped-call]
        self._text(slide, 0.17, 0.2, 11.6, 0.75, f"商品名称：{title}", 24, _DARK)
        divider = slide.shapes.add_shape(
            MSO_SHAPE.RECTANGLE, Inches(5.58), Inches(0.75), Inches(0.01), Inches(6.0)
        )
        divider.fill.solid()
        divider.fill.fore_color.rgb = _LINE
        divider.line.fill.background()
        return slide

    def _add_left_details(self, slide: Any, details: list[tuple[str, str]]) -> None:
        content = "\n".join(f"{label}：{value}" for label, value in details)
        code = getattr(self, "_template_code", "SYSTEM_DEFAULT")
        if code == "CATALOG_MINIMAL":
            left, top, width, height = 6.35, 1.25, 5.55, 5.55
        elif code == "JD_DETAIL_RED":
            left, top, width, height = 6.45, 1.25, 5.75, 4.95
        elif code == "JD_FESTIVE_RED":
            left, top, width, height = 6.0, 1.25, 6.25, 4.8
        else:
            left, top, width, height = 0.3, 1.05, 4.7, 5.95
        self._text(
            slide,
            left,
            top,
            width,
            height,
            content,
            12,
            _DARK,
            valign=MSO_ANCHOR.TOP,
        )

    def _add_product_image(self, slide: Any, content: bytes | None) -> None:
        code = getattr(self, "_template_code", "SYSTEM_DEFAULT")
        if code == "CATALOG_MINIMAL":
            left, top, width, height = 0.55, 1.1, 5.3, 5.8
        elif code == "JD_DETAIL_RED":
            left, top, width, height = 0.45, 0.95, 5.3, 4.65
        elif code == "JD_FESTIVE_RED":
            left, top, width, height = 0.75, 1.0, 4.75, 5.2
        else:
            left, top, width, height = 6.1, 1.0, 6.35, 5.85
        if content is None or not self._add_contained_image(
            slide, content, left, top, width, height
        ):
            self._text(
                slide,
                left,
                top + height / 2 - 0.18,
                width,
                0.35,
                "商品图片待补充",
                14,
                _GREY,
                align=PP_ALIGN.CENTER,
            )

    def _add_package_images(self, slide: Any, images: list[bytes]) -> None:
        if not images:
            self._add_product_image(slide, None)
            return
        if len(images) == 1:
            self._add_product_image(slide, images[0])
            return
        for content, (left, top, width, height) in zip(
            images[:4], self._package_image_slots(), strict=False
        ):
            self._add_contained_image(slide, content, left, top, width, height)

    def _package_image_slots(self) -> tuple[tuple[float, float, float, float], ...]:
        code = getattr(self, "_template_code", "SYSTEM_DEFAULT")
        if code == "JD_DETAIL_RED":
            return (
                (0.45, 0.95, 2.45, 2.0),
                (3.12, 0.95, 2.45, 2.0),
                (0.45, 3.2, 2.45, 2.0),
                (3.12, 3.2, 2.45, 2.0),
            )
        if code == "JD_FESTIVE_RED":
            return (
                (0.75, 1.05, 2.15, 2.2),
                (3.15, 1.05, 2.15, 2.2),
                (0.75, 3.65, 2.15, 2.2),
                (3.15, 3.65, 2.15, 2.2),
            )
        if code == "CATALOG_MINIMAL":
            return (
                (0.55, 1.15, 2.35, 2.45),
                (3.15, 1.15, 2.35, 2.45),
                (0.55, 4.0, 2.35, 2.45),
                (3.15, 4.0, 2.35, 2.45),
            )
        return (
            (6.0, 1.05, 2.85, 2.5),
            (9.25, 1.05, 2.85, 2.5),
            (6.0, 4.05, 2.85, 2.5),
            (9.25, 4.05, 2.85, 2.5),
        )

    @staticmethod
    def _paginate_details(details: list[tuple[str, str]]) -> list[list[tuple[str, str]]]:
        pages: list[list[tuple[str, str]]] = [[]]
        used = 0
        for label, value in details:
            remaining = value or "—"
            continuation = 1
            while remaining:
                chunk, remaining = remaining[:140], remaining[140:]
                page_label = label if continuation == 1 else f"{label}（续）"
                line_size = len(page_label) + len(chunk) + 2
                if used and used + line_size > 560:
                    pages.append([])
                    used = 0
                pages[-1].append((page_label, chunk))
                used += line_size
                continuation += 1
        return pages

    def _add_contained_image(
        self,
        slide: Any,
        content: bytes,
        left: float,
        top: float,
        width: float,
        height: float,
    ) -> bool:
        try:
            with Image.open(BytesIO(content)) as image:
                image_width, image_height = image.size
        except (UnidentifiedImageError, OSError, ValueError):
            return False
        scale = min(width / image_width, height / image_height)
        rendered_width = image_width * scale
        rendered_height = image_height * scale
        image_left = left + (width - rendered_width) / 2
        image_top = top + (height - rendered_height) / 2
        slide.shapes.add_picture(
            BytesIO(content),
            Inches(image_left),
            Inches(image_top),
            width=Inches(rendered_width),
            height=Inches(rendered_height),
        )
        return True

    def _text(
        self,
        slide: Any,
        left: float,
        top: float,
        width: float,
        height: float,
        value: str,
        size: int,
        color: RGBColor,
        *,
        align: PP_ALIGN = PP_ALIGN.LEFT,
        valign: MSO_ANCHOR = MSO_ANCHOR.MIDDLE,
    ) -> None:
        box = slide.shapes.add_textbox(Inches(left), Inches(top), Inches(width), Inches(height))
        frame = box.text_frame
        frame.clear()
        frame.word_wrap = True
        frame.vertical_anchor = valign
        paragraph = frame.paragraphs[0]
        paragraph.alignment = align
        run = paragraph.add_run()
        run.text = value
        run.font.name = _FONT
        run.font.size = Pt(size)
        run.font.color.rgb = color

    @staticmethod
    def _text_value(values: Mapping[str, object], field: str, default: str) -> str:
        value = values.get(field)
        return str(value).strip() if value is not None and str(value).strip() else default

    def _display_price(self, item: Mapping[str, object]) -> tuple[str, str]:
        manual = self._mapping(item.get("manual"))
        value = manual.get("campaign_price")
        if value is not None and str(value).strip():
            return "人工确认活动价", self._money(value)
        return "当前协议价", self._money(self._mapping(item.get("prices")).get("agreement_price"))

    @staticmethod
    def _money(value: object) -> str:
        try:
            amount = Decimal(str(value))
        except (InvalidOperation, TypeError, ValueError):
            return "—"
        return f"¥ {amount:,.2f}"

    def _product_label(self, product: Mapping[str, object]) -> str:
        name = self._text_value(product, "product_name", "未命名商品")
        brand = self._text_value(product, "brand", "")
        model = self._text_value(product, "model", "")
        suffix = " / ".join(value for value in (brand, model) if value)
        return f"{name}（{suffix}）" if suffix else name

    def _package_item_line(self, index: int, item: Mapping[str, object]) -> str:
        product = self._mapping(item.get("product_snapshot"))
        return f"{index}. {self._product_label(product)} × {item.get('quantity') or 1}"
