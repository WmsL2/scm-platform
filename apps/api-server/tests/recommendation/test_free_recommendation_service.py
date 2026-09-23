from __future__ import annotations

import uuid
from contextlib import asynccontextmanager
from io import BytesIO
from typing import AsyncIterator

import pytest
from openpyxl import Workbook

from app.common.contracts import AppError
from app.modules.bid.application import service as service_module
from app.modules.bid.application.service import BidProjectService
from app.modules.bid.domain.lifecycle import BidFileType, BidImportStatus, BidProjectType
from app.modules.bid.infrastructure.models import BidProjectFile, BidProjectItem


class FakeStorage:
    def __init__(self) -> None:
        self.saved: dict[str, bytes] = {}
        self.deleted: list[str] = []

    async def save(self, name: str, content: bytes) -> str:
        key = f"saved/{len(self.saved) + 1}.xlsx"
        self.saved[key] = content
        return key

    async def read(self, key: str) -> bytes:
        return self.saved[key]

    async def delete(self, key: str) -> None:
        self.deleted.append(key)
        self.saved.pop(key, None)


class FakeSession:
    def __init__(self) -> None:
        self.added: list[object] = []

    def add(self, value: object) -> None:
        self.added.append(value)

    async def flush(self) -> None:
        for value in self.added:
            if isinstance(value, BidProjectFile) and value.id is None:
                value.id = uuid.uuid4()


def _workbook(headers: list[str] | None = None) -> bytes:
    workbook = Workbook()
    workbook.active.title = "推荐清单"
    workbook.active.append(headers or ["品牌", "名称", "毛利"])
    output = BytesIO()
    workbook.save(output)
    workbook.close()
    return output.getvalue()


def _transaction(*, fail_after_yield: bool = False):
    @asynccontextmanager
    async def scope(_: object) -> AsyncIterator[None]:
        yield
        if fail_after_yield:
            raise RuntimeError("commit failed")

    return scope


@pytest.fixture
def issue_code(monkeypatch: pytest.MonkeyPatch) -> None:
    async def fake_issue(_: object, __: str) -> str:
        return "BID-TEST-1"

    monkeypatch.setattr(service_module.BusinessSequenceService, "issue_code", fake_issue)


@pytest.mark.asyncio
async def test_filter_template_is_rejected_before_storage(
    monkeypatch: pytest.MonkeyPatch, issue_code: None
) -> None:
    storage = FakeStorage()
    monkeypatch.setattr(service_module, "transaction_scope", _transaction())
    service = BidProjectService(FakeSession(), storage)  # type: ignore[arg-type]

    with pytest.raises(AppError, match="筛选推品项目不接受自由推品模板"):
        await service.create(
            project_name="筛选",
            buyer_name="客户",
            start_at=None,
            deadline_at=None,
            remark=None,
            filename="buyer.xlsx",
            file_bytes=_workbook(),
            recommendation_template_filename="recommendation.xlsx",
            recommendation_template_bytes=_workbook(),
            actor_id=uuid.uuid4(),
        )
    assert storage.saved == {}


@pytest.mark.asyncio
async def test_filter_without_customer_excel_is_rejected(
    monkeypatch: pytest.MonkeyPatch, issue_code: None
) -> None:
    storage = FakeStorage()
    monkeypatch.setattr(service_module, "transaction_scope", _transaction())
    service = BidProjectService(FakeSession(), storage)  # type: ignore[arg-type]

    with pytest.raises(AppError, match="必须上传客户需求 Excel"):
        await service.create(
            project_name="筛选",
            buyer_name="客户",
            start_at=None,
            deadline_at=None,
            remark=None,
            filename=None,
            file_bytes=None,
            actor_id=uuid.uuid4(),
        )
    assert storage.saved == {}


@pytest.mark.asyncio
async def test_free_creation_has_no_items_and_persists_template(
    monkeypatch: pytest.MonkeyPatch, issue_code: None
) -> None:
    storage = FakeStorage()
    session = FakeSession()
    monkeypatch.setattr(service_module, "transaction_scope", _transaction())
    service = BidProjectService(session, storage)  # type: ignore[arg-type]

    response = await service.create(
        project_name="自由推品",
        buyer_name="客户",
        start_at=None,
        deadline_at=None,
        remark="这是至少二十个字符的自由推品需求说明内容",
        filename=None,
        file_bytes=None,
        recommendation_template_filename="recommendation.xlsx",
        recommendation_template_bytes=_workbook(),
        project_type=BidProjectType.FREE_RECOMMENDATION,
        actor_id=uuid.uuid4(),
    )

    assert response.project_type == BidProjectType.FREE_RECOMMENDATION
    assert response.import_status == BidImportStatus.NOT_REQUIRED
    assert [x for x in session.added if isinstance(x, BidProjectItem)] == []
    files = [x for x in session.added if isinstance(x, BidProjectFile)]
    assert len(files) == 1
    assert files[0].file_type == BidFileType.RECOMMENDATION_TEMPLATE.value
    assert files[0].sha256
    assert storage.deleted == []


@pytest.mark.asyncio
async def test_free_create_commit_failure_deletes_new_template(
    monkeypatch: pytest.MonkeyPatch, issue_code: None
) -> None:
    storage = FakeStorage()
    monkeypatch.setattr(service_module, "transaction_scope", _transaction(fail_after_yield=True))
    service = BidProjectService(FakeSession(), storage)  # type: ignore[arg-type]

    with pytest.raises(RuntimeError, match="commit failed"):
        await service.create(
            project_name="自由推品",
            buyer_name="客户",
            start_at=None,
            deadline_at=None,
            remark="这是至少二十个字符的自由推品需求说明内容",
            filename=None,
            file_bytes=None,
            recommendation_template_filename="recommendation.xlsx",
            recommendation_template_bytes=_workbook(),
            project_type=BidProjectType.FREE_RECOMMENDATION,
            actor_id=uuid.uuid4(),
        )
    assert storage.saved == {}
    assert storage.deleted == ["saved/1.xlsx"]


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("remark", "template_name", "template_bytes", "error_code"),
    [
        (None, "recommendation.xlsx", _workbook(), "FREE_RECOMMENDATION_REMARK_REQUIRED"),
        (" 太短 ", "recommendation.xlsx", _workbook(), "FREE_RECOMMENDATION_REMARK_REQUIRED"),
        (
            "这是至少二十个字符的自由推品需求说明内容",
            None,
            None,
            "RECOMMENDATION_TEMPLATE_REQUIRED",
        ),
        (
            "这是至少二十个字符的自由推品需求说明内容",
            "recommendation.xls",
            _workbook(),
            "RECOMMENDATION_TEMPLATE_INVALID",
        ),
    ],
)
async def test_free_create_validation_rejects_invalid_contract(
    monkeypatch: pytest.MonkeyPatch,
    issue_code: None,
    remark: str | None,
    template_name: str | None,
    template_bytes: bytes | None,
    error_code: str,
) -> None:
    storage = FakeStorage()
    monkeypatch.setattr(service_module, "transaction_scope", _transaction())
    service = BidProjectService(FakeSession(), storage)  # type: ignore[arg-type]
    with pytest.raises(AppError) as exc_info:
        await service.create(
            project_name="自由推品",
            buyer_name="客户",
            start_at=None,
            deadline_at=None,
            remark=remark,
            filename=None,
            file_bytes=None,
            recommendation_template_filename=template_name,
            recommendation_template_bytes=template_bytes,
            project_type=BidProjectType.FREE_RECOMMENDATION,
            actor_id=uuid.uuid4(),
        )
    assert exc_info.value.code == error_code
    assert storage.saved == {}


@pytest.mark.asyncio
async def test_ppt_is_rejected_before_sequence_or_storage(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    storage = FakeStorage()
    called = False

    async def unexpected_issue(_: object, __: str) -> str:
        nonlocal called
        called = True
        return "unexpected"

    monkeypatch.setattr(service_module.BusinessSequenceService, "issue_code", unexpected_issue)
    service = BidProjectService(FakeSession(), storage)  # type: ignore[arg-type]
    with pytest.raises(AppError) as exc_info:
        await service.create(
            project_name="PPT",
            buyer_name="客户",
            start_at=None,
            deadline_at=None,
            remark=None,
            filename=None,
            file_bytes=None,
            project_type=BidProjectType.PPT_SOLUTION,
            actor_id=uuid.uuid4(),
        )
    assert exc_info.value.code == "BID_PROJECT_TYPE_NOT_AVAILABLE"
    assert not called
    assert storage.saved == {}
