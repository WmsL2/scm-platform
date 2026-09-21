import pytest
from pydantic import ValidationError

from app.modules.supplier.schemas import (
    SupplierContactInput,
    SupplierCreateRequest,
    SupplierUpdateRequest,
)


def valid_supplier_payload() -> dict[str, object]:
    return {
        "supplier_name": "供应商名称",
        "main_brands": "主营品牌",
        "advantage": "主要优势",
        "contacts": [],
    }


def test_supplier_create_rejects_blank_supplier_name() -> None:
    payload = valid_supplier_payload()
    payload["supplier_name"] = "   "

    with pytest.raises(ValidationError):
        SupplierCreateRequest(**payload)


def test_supplier_update_rejects_blank_supplier_name() -> None:
    with pytest.raises(ValidationError):
        SupplierUpdateRequest(supplier_name="   ")


def test_supplier_requests_allow_blank_optional_business_text() -> None:
    create_request = SupplierCreateRequest(supplier_name="供应商名称")
    update_request = SupplierUpdateRequest(main_brands="   ", advantage=None)

    assert create_request.main_brands is None
    assert create_request.advantage is None
    assert update_request.main_brands is None
    assert update_request.advantage is None


def test_supplier_requests_store_trimmed_required_text() -> None:
    request = SupplierCreateRequest(
        supplier_name="  供应商名称  ",
        main_brands="  主营品牌  ",
        advantage="  主要优势  ",
    )

    assert request.supplier_name == "供应商名称"
    assert request.main_brands == "主营品牌"
    assert request.advantage == "主要优势"
    assert request.archive_status == "DRAFT"


def test_supplier_create_accepts_selected_initial_archive_status() -> None:
    request = SupplierCreateRequest(
        supplier_name="供应商名称",
        main_brands="主营品牌",
        advantage="主要优势",
        archive_status="ARCHIVED",
    )

    assert request.archive_status == "ARCHIVED"


def test_contact_rejects_when_both_values_are_blank() -> None:
    with pytest.raises(ValidationError):
        SupplierContactInput(contact_name="   ", contact_phone="　")


def test_contact_normalizes_blank_optional_value_to_none() -> None:
    contact = SupplierContactInput(contact_name="   ", contact_phone=" 13800000000 ")

    assert contact.contact_name is None
    assert contact.contact_phone == "13800000000"
