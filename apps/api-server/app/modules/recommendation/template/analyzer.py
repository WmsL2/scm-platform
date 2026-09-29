from __future__ import annotations

from dataclasses import dataclass
from io import BytesIO

from openpyxl import load_workbook

from app.common.contracts import AppError
from app.modules.catalog.application.product_export_columns import PRODUCT_EXPORT_COLUMNS

_EXACT_AUTO_MAPPING = {column.header: column.key for column in PRODUCT_EXPORT_COLUMNS}
_SAFE_ALIASES = {
    "一级类目": "category_level1_name",
    "二级类目": "category_level2_name",
    "三级类目": "category_level3_name",
    "品牌": "brand",
    "SKU": "sku",
    "名称": "product_name",
    "京东价": "jd_price",
    "大客户协议价": "agreement_price",
    "毛利": "profit",
    "毛利率": "gross_margin",
    "折扣率": "discount_rate",
    "采销": "purchasing_agent",
    "是否厂直": "factory_direct",
    "是否支持京东或者顺丰物流": "supports_jd_or_sf",
}


@dataclass(frozen=True)
class TemplateAnalysis:
    sheet_name: str
    header_row: int
    data_start_row: int
    mapping_json: dict[str, object]


@dataclass(frozen=True)
class TemplateColumn:
    column_index: int
    header: str
    duplicate: bool


@dataclass(frozen=True)
class TemplateStructure:
    sheet_names: list[str]
    sheet_name: str
    header_row: int
    max_row: int
    columns: list[TemplateColumn]


def analyze_template(file_bytes: bytes) -> TemplateAnalysis:
    """Read only deterministic workbook structure; never infers business semantics from style."""
    try:
        workbook = load_workbook(BytesIO(file_bytes), read_only=False, data_only=False)
    except Exception as exc:
        raise AppError("RECOMMENDATION_TEMPLATE_INVALID", "推荐模板无法读取", 422) from exc
    try:
        for sheet in workbook.worksheets:
            for row_number, row in enumerate(sheet.iter_rows(max_row=min(sheet.max_row, 50)), 1):
                headers = [
                    str(cell.value).strip() if cell.value is not None else "" for cell in row
                ]
                # Mapping is column-oriented: duplicate template columns and repeated
                # product fields are both valid export requirements.
                columns = [
                    {"column_index": index, "field_key": _EXACT_AUTO_MAPPING.get(header)
                    or _SAFE_ALIASES.get(header)}
                    for index, header in enumerate(headers, start=1)
                    if _EXACT_AUTO_MAPPING.get(header) or _SAFE_ALIASES.get(header)
                ]
                if columns:
                    return TemplateAnalysis(
                        sheet.title,
                        row_number,
                        row_number + 1,
                        {"version": 2, "columns": columns},
                    )
        sheet = workbook.worksheets[0]
        return TemplateAnalysis(sheet.title, 1, 2, {})
    finally:
        workbook.close()


def inspect_template_structure(
    file_bytes: bytes, *, sheet_name: str | None, header_row: int
) -> TemplateStructure:
    """Return the exact stored workbook headers for deterministic UI selection."""
    try:
        workbook = load_workbook(BytesIO(file_bytes), read_only=True, data_only=False)
    except Exception as exc:
        raise AppError("RECOMMENDATION_TEMPLATE_INVALID", "推荐模板无法读取", 422) from exc
    try:
        selected_sheet = sheet_name or workbook.sheetnames[0]
        if selected_sheet not in workbook.sheetnames:
            raise AppError("RECOMMENDATION_TEMPLATE_MAPPING_INVALID", "模板工作表不存在", 422)
        sheet = workbook[selected_sheet]
        if header_row < 1 or header_row > sheet.max_row:
            raise AppError("RECOMMENDATION_TEMPLATE_MAPPING_INVALID", "模板表头行不存在", 422)
        headers = [
            str(cell.value).strip() if cell.value is not None else "" for cell in sheet[header_row]
        ]
        counts = {header: headers.count(header) for header in set(headers) if header}
        columns = [
            TemplateColumn(
                column_index=index,
                header=header,
                duplicate=counts[header] > 1,
            )
            for index, header in enumerate(headers, start=1)
            if header
        ]
        return TemplateStructure(
            sheet_names=list(workbook.sheetnames),
            sheet_name=selected_sheet,
            header_row=header_row,
            max_row=sheet.max_row,
            columns=columns,
        )
    finally:
        workbook.close()


def validate_mapping_contract(
    file_bytes: bytes,
    *,
    sheet_name: str,
    header_row: int,
    data_start_row: int,
    mapping_json: dict[str, object],
) -> None:
    """Validate an explicit mapping against the exact stored workbook."""
    if data_start_row <= header_row:
        raise AppError(
            "RECOMMENDATION_TEMPLATE_MAPPING_INVALID",
            "数据起始行必须位于表头行之后",
            422,
        )
    try:
        workbook = load_workbook(BytesIO(file_bytes), read_only=True, data_only=False)
    except Exception as exc:
        raise AppError("RECOMMENDATION_TEMPLATE_MAPPING_INVALID", "推荐模板无法读取", 422) from exc
    try:
        if sheet_name not in workbook.sheetnames:
            raise AppError("RECOMMENDATION_TEMPLATE_MAPPING_INVALID", "模板工作表不存在", 422)
        sheet = workbook[sheet_name]
        if header_row > sheet.max_row:
            raise AppError("RECOMMENDATION_TEMPLATE_MAPPING_INVALID", "模板表头行不存在", 422)
        headers = [
            str(cell.value).strip() if cell.value is not None else "" for cell in sheet[header_row]
        ]
        resolve_mapping_columns(headers, mapping_json)
    finally:
        workbook.close()


def resolve_mapping_columns(
    headers: list[str], mapping_json: dict[str, object]
) -> list[tuple[str, int]]:
    """Resolve stored mapping JSON to physical Excel columns.

    V2 identifies a destination by its one-based column index, so duplicate
    headers are unambiguous and one product source field may feed many columns.
    The legacy field-to-header document remains readable for existing mappings.
    """
    if mapping_json.get("version") == 2:
        raw_columns = mapping_json.get("columns")
        if not isinstance(raw_columns, list) or not raw_columns:
            raise AppError(
                "RECOMMENDATION_TEMPLATE_MAPPING_INVALID", "模板列映射不能为空", 422
            )
        resolved: list[tuple[str, int]] = []
        seen_indexes: set[int] = set()
        for entry in raw_columns:
            if not isinstance(entry, dict):
                raise AppError(
                    "RECOMMENDATION_TEMPLATE_MAPPING_INVALID", "模板列映射格式无效", 422
                )
            field = entry.get("field_key")
            column_index = entry.get("column_index")
            if (
                not isinstance(field, str)
                or not field.strip()
                or not isinstance(column_index, int)
                or isinstance(column_index, bool)
                or column_index < 1
                or column_index > len(headers)
                or not headers[column_index - 1]
                or column_index in seen_indexes
            ):
                raise AppError(
                    "RECOMMENDATION_TEMPLATE_MAPPING_INVALID", "模板列映射无效或已变更", 422
                )
            seen_indexes.add(column_index)
            resolved.append((field, column_index))
        return resolved

    resolved = []
    for field, source_header in mapping_json.items():
        if not isinstance(field, str) or not isinstance(source_header, str):
            raise AppError(
                "RECOMMENDATION_TEMPLATE_MAPPING_INVALID", "模板映射格式无效", 422
            )
        matches = [
            index for index, header in enumerate(headers, start=1) if header == source_header
        ]
        if len(matches) != 1:
            raise AppError(
                "RECOMMENDATION_TEMPLATE_MAPPING_INVALID", "映射源表头不存在或不唯一", 422
            )
        resolved.append((field, matches[0]))
    return resolved
