# ruff: noqa: E501,E701
# mypy: ignore-errors
from dataclasses import dataclass
from decimal import Decimal
from typing import Callable

from app.modules.catalog.infrastructure.models import Product
from app.modules.supplier.infrastructure.models import Supplier


@dataclass(frozen=True)
class ProductExportColumn:
    key: str
    header: str
    value: Callable[[Product, Supplier], object | None]


def _percent(value: object | None) -> str | None:
    if value is None:
        return None
    scaled = Decimal(str(value)) * Decimal("100")
    return f"{scaled.normalize():f}%"


def _decimal(value: object | None) -> str | None:
    return None if value is None else str(value)


_FIELDS = (
    ("company_name", "所属公司"), ("listed_at", "上架日期"), ("brand", "品牌"),
    ("image_reference", "图片"), ("model", "型号"), ("sku", "sku"),
    ("product_name", "商品名称"), ("category_level1_name", "一级类目"),
    ("category_level2_name", "二级类目"), ("category_level3_name", "三级类目"),
    ("item_number", "货号"), ("jd_same_product_url", "链接"), ("cost_price", "成本价"),
    ("market_price", "市场价"), ("jd_price", "京东价"), ("agreement_price", "协议价"),
    ("agreement_purchase_price", "协议价采购价"), ("profit", "利润"),
    ("jd_margin", "京东价毛利（30-50）"), ("deduction_review", "扣点复核"),
    ("gross_margin", "毛利率"), ("purchasing_agent", "采销员"),
    ("supplier_name", "供应商"), ("barcode_text", "69码"),
    ("certification_3c_code", "3c编码"), ("product_specification", "产品规格"),
    ("selling_points", "卖点"), ("packaging_list", "包装清单"),
    ("warranty_period", "质保期"), ("restricted_regions", "限售区域"),
    ("jd_self_operated_price", "京东自营前台价"), ("storefront_type", "自营旗舰店/官方旗舰店"),
    ("reference_url", "参考链接"), ("sales_volume", "销量"), ("positive_rating", "好评率"),
    ("discount_rate", "折扣率"), ("price_inflation_rate", "价格虚高比例"),
    ("tax_code", "税收编码"), ("invoice_name", "开票名称"), ("tax_category", "税收分类"),
    ("shipping_courier", "发货快递"), ("after_sales_policy", "售后政策"), ("remark", "备注"),
)
_DECIMALS = {"cost_price", "market_price", "jd_price", "agreement_price", "agreement_purchase_price", "profit", "jd_self_operated_price"}
_PERCENTS = {"jd_margin", "deduction_review", "gross_margin", "positive_rating", "discount_rate", "price_inflation_rate"}

def _value(key: str) -> Callable[[Product, Supplier], object | None]:
    if key == "supplier_name": return lambda _product, supplier: supplier.supplier_name
    if key in _PERCENTS: return lambda product, _supplier: _percent(getattr(product, key))
    if key in _DECIMALS: return lambda product, _supplier: _decimal(getattr(product, key))
    return lambda product, _supplier: getattr(product, key)

PRODUCT_EXPORT_COLUMNS = tuple(ProductExportColumn(key, header, _value(key)) for key, header in _FIELDS)
PRODUCT_EXPORT_COLUMN_KEYS = tuple(column.key for column in PRODUCT_EXPORT_COLUMNS)
