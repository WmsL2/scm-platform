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


@pytest.mark.parametrize("field_name", ("supplier_name", "main_brands", "advantage"))
def test_supplier_create_rejects_blank_required_text(field_name: str) -> None:
    payload = valid_supplier_payload()
    payload[field_name] = "   "

    with pytest.raises(ValidationError):
        SupplierCreateRequest(**payload)


@pytest.mark.parametrize("field_name", ("supplier_name", "main_brands", "advantage"))
def test_supplier_update_rejects_blank_required_text(field_name: str) -> None:
    with pytest.raises(ValidationError):
        SupplierUpdateRequest(**{field_name: "   "})


def test_supplier_requests_store_trimmed_required_text() -> None:
    request = SupplierCreateRequest(
        supplier_name="  供应商名称  ",
        main_brands="  主营品牌  ",
        advantage="  主要优势  ",
    )

    assert request.supplier_name == "供应商名称"
    assert request.main_brands == "主营品牌"
    assert request.advantage == "主要优势"


def test_contact_rejects_when_both_values_are_blank() -> None:
    with pytest.raises(ValidationError):
        SupplierContactInput(contact_name="   ", contact_phone="　")


def test_contact_normalizes_blank_optional_value_to_none() -> None:
    contact = SupplierContactInput(contact_name="   ", contact_phone=" 13800000000 ")

    assert contact.contact_name is None
    assert contact.contact_phone == "13800000000"
