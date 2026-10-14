"""Focused MySQL acceptance for project-scoped durable task locking."""

from __future__ import annotations

import asyncio
import uuid

import pytest
from sqlalchemy import delete

from app.common.contracts import AppError
from app.core.database import SessionLocal
from app.modules.bid.domain.lifecycle import BidImportStatus, BidProjectStatus, BidProjectType
from app.modules.bid.infrastructure.models import BidProject, BidProjectEvent
from app.modules.system.models import AsyncTask
from app.modules.system.task_schemas import AsyncTaskCreate, AsyncTaskKind
from app.modules.system.task_service import AsyncTaskService


@pytest.mark.asyncio
async def test_project_lock_allows_only_one_active_heavy_task() -> None:
    project_id, actor_id = uuid.uuid4(), uuid.uuid4()
    token = uuid.uuid4().hex
    async with SessionLocal() as session:
        session.add(
            BidProject(
                id=project_id,
                project_code=f"Q{token[:12]}",
                project_name=f"queue lock test {token}",
                buyer_name="queue test",
                status=BidProjectStatus.IMPORTED.value,
                import_status=BidImportStatus.PARSED.value,
                project_type=BidProjectType.FILTER_RECOMMENDATION.value,
                created_by=actor_id,
            )
        )
        await session.commit()

    async def enqueue() -> object:
        async with SessionLocal() as session:
            try:
                return await AsyncTaskService(session).enqueue(
                    AsyncTaskCreate(
                        project_id=project_id,
                        task_kind=AsyncTaskKind.TYPE1_MATCH,
                        created_by=actor_id,
                    )
                )
            except AppError as exc:
                return exc

    try:
        results = await asyncio.gather(enqueue(), enqueue())
        errors = [result for result in results if isinstance(result, AppError)]
        tasks = [result for result in results if not isinstance(result, AppError)]
        assert len(tasks) == 1
        assert len(errors) == 1
        assert errors[0].code == "ASYNC_TASK_ALREADY_ACTIVE"
        assert errors[0].status_code == 409
    finally:
        async with SessionLocal() as session:
            await session.execute(delete(AsyncTask).where(AsyncTask.project_id == project_id))
            await session.execute(
                delete(BidProjectEvent).where(BidProjectEvent.project_id == project_id)
            )
            await session.execute(delete(BidProject).where(BidProject.id == project_id))
            await session.commit()
