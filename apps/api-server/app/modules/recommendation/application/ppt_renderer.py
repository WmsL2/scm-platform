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
    ) -> bytes:
        presentation = Presentation(str(template_path)) if template_path else Presentation()
        if template_path is None:
            presentation.slide_width = _SLIDE_WIDTH
            presentation.slide_height = _SLIDE_HEIGHT

        images = product_images or {}
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
        title = self._text_value(product, "product_name", "推荐商品")
        details = [
            ("SKU", self._text_value(product, "sku", "—")),
            ("品牌", self._text_value(product, "brand", "—")),
            ("型号", self._text_value(product, "model", "—")),
            ("商品配置", self._text_value(product, "product_specification", "—")),
            ("协议价", self._candidate_price(item)),
            ("配送", self._text_value(manual, "delivery_status", "以项目要求为准")),
            ("库存", self._text_value(manual, "inventory_status", "待业务确认")),
            ("履约", self._text_value(manual, "fulfillment_cycle", "待业务确认")),
        ]
        evidence = self._text_value(manual, "evidence", "")
        if evidence:
            details.append(("备注", evidence))
        slide = self._base_page(presentation, title)
        self._add_left_details(slide, details)
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
        slide = self._base_page(presentation, name)
        self._add_left_details(slide, details)
        image_bytes = [
            images.get(self._text_value(self._mapping(item.get("product_snapshot")), "id", ""))
            for item in items
        ]
        self._add_package_images(slide, [item for item in image_bytes if item])

    def _base_page(self, presentation: Any, title: str) -> Any:
        slide = presentation.slides.add_slide(presentation.slide_layouts[6])
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

    def _add_left_details(self, slide: Any, details: list[tuple[str, str]]) -> None:
        content = "\n".join(f"{label}：{value}" for label, value in details)
        self._text(
            slide,
            0.3,
            1.05,
            4.7,
            5.95,
            content,
            12,
            _DARK,
            valign=MSO_ANCHOR.TOP,
        )

    def _add_product_image(self, slide: Any, content: bytes | None) -> None:
        if content is None or not self._add_contained_image(slide, content, 6.1, 1.0, 6.35, 5.85):
            self._text(
                slide,
                6.1,
                3.45,
                6.35,
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
        slots = ((6.0, 1.05), (9.25, 1.05), (6.0, 4.05), (9.25, 4.05))
        for content, (left, top) in zip(images[:4], slots, strict=False):
            self._add_contained_image(slide, content, left, top, 2.85, 2.5)

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

    def _candidate_price(self, item: Mapping[str, object]) -> str:
        manual = self._mapping(item.get("manual"))
        value = manual.get("campaign_price")
        if value is None:
            value = self._mapping(item.get("prices")).get("agreement_price")
        return self._money(value)

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
