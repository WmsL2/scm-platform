import asyncio
import uuid
from io import BytesIO

from sqlalchemy.ext.asyncio import AsyncSession

from app.common.contracts import AppError
from app.modules.supplier.application.excel_template import create_supplier_excel_workbook
from app.modules.supplier.infrastructure.models import Supplier
from app.modules.supplier.infrastructure.repository import SupplierRepository


class SupplierExportService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def export(self, supplier_ids: list[uuid.UUID]) -> bytes:
        suppliers = await SupplierRepository(self.session).selected_active(supplier_ids)
        by_id = {supplier.id: supplier for supplier in suppliers}
        selected = [by_id.get(supplier_id) for supplier_id in supplier_ids]
        if len(by_id) != len(supplier_ids) or any(item is None for item in selected):
            raise AppError(
                "SUPPLIER_EXPORT_SELECTION_STALE",
                "所选供应商已发生变化，请刷新列表后重新选择",
                409,
            )
        return await asyncio.to_thread(
            self._build, [supplier for supplier in selected if supplier is not None]
        )

    @staticmethod
    def _build(suppliers: list[Supplier]) -> bytes:
        workbook, worksheet = create_supplier_excel_workbook()
        for supplier in suppliers:
            contacts = [contact for contact in supplier.contacts if not contact.is_deleted]
            names = "；".join(contact.contact_name or "" for contact in contacts)
            phones = "；".join(contact.contact_phone or "" for contact in contacts)
            worksheet.append(
                [
                    supplier.supplier_name or None,
                    supplier.main_brands or None,
                    supplier.advantage or None,
                    names or None,
                    phones or None,
                ]
            )
            worksheet.cell(worksheet.max_row, 5).number_format = "@"
        worksheet.auto_filter.ref = f"A1:E{max(worksheet.max_row, 1)}"
        output = BytesIO()
        workbook.save(output)
        return output.getvalue()
