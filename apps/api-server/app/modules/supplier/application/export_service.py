# mypy: ignore-errors
import asyncio
from io import BytesIO

import xlsxwriter
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.contracts import AppError
from app.modules.supplier.domain.rules import ArchiveStatus, CooperationStatus
from app.modules.supplier.infrastructure.repository import SupplierRepository

ARCHIVE_LABELS = {
    ArchiveStatus.DRAFT: "草稿",
    ArchiveStatus.PENDING: "待归档",
    ArchiveStatus.ARCHIVED: "已归档",
}
COOPERATION_LABELS = {
    CooperationStatus.NORMAL: "正常合作",
    CooperationStatus.STOPPED: "已停止合作",
    CooperationStatus.BLACKLIST: "黑名单",
}
HEADERS = (
    "供应商编码",
    "供应商名称",
    "主营品牌",
    "主要优势",
    "联系人",
    "联系电话",
    "归档状态",
    "合作状态",
    "创建时间",
    "更新时间",
)


class SupplierExportService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def export(
        self, supplier_ids: list
    ) -> bytes:
        suppliers = await SupplierRepository(self.session).selected_active(supplier_ids)
        by_id = {supplier.id: supplier for supplier in suppliers}
        selected = [by_id.get(supplier_id) for supplier_id in supplier_ids]
        if len(by_id) != len(supplier_ids) or any(item is None for item in selected):
            raise AppError(
                "SUPPLIER_EXPORT_SELECTION_STALE",
                "所选供应商已发生变化，请刷新列表后重新选择",
                409,
            )
        return await asyncio.to_thread(self._build, selected)

    @staticmethod
    def _build(suppliers: list) -> bytes:
        output = BytesIO()
        workbook = xlsxwriter.Workbook(output, {"in_memory": True})
        sheet = workbook.add_worksheet("供应商")
        header = workbook.add_format({"bold": True, "align": "center", "valign": "vcenter"})
        text = workbook.add_format({"text_wrap": True, "valign": "top"})
        code = workbook.add_format({"num_format": "@", "valign": "top"})
        date = workbook.add_format({"num_format": "yyyy-mm-dd hh:mm:ss", "valign": "top"})
        for column, value in enumerate(HEADERS):
            sheet.write(0, column, value, header)
        for row, supplier in enumerate(suppliers, 1):
            contacts = [contact for contact in supplier.contacts if not contact.is_deleted]
            names = "；".join(contact.contact_name or "" for contact in contacts)
            phones = "；".join(contact.contact_phone or "" for contact in contacts)
            values = (
                supplier.supplier_code,
                supplier.supplier_name,
                supplier.main_brands,
                supplier.advantage,
                names,
                phones,
                ARCHIVE_LABELS[supplier.archive_status],
                COOPERATION_LABELS[supplier.cooperation_status],
            )
            for column, value in enumerate(values):
                sheet.write(row, column, value or "", code if column in (0, 5) else text)
            sheet.write_datetime(row, 8, supplier.created_at, date)
            sheet.write_datetime(row, 9, supplier.updated_at, date)
        sheet.freeze_panes(1, 0)
        sheet.autofilter(0, 0, max(len(suppliers), 1), len(HEADERS) - 1)
        sheet.set_column(0, 0, 18, code)
        sheet.set_column(1, 1, 24, text)
        sheet.set_column(2, 5, 28, text)
        sheet.set_column(6, 7, 14, text)
        sheet.set_column(8, 9, 20, date)
        workbook.close()
        return output.getvalue()
