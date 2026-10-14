from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.contracts import AppError
from app.core.transaction import transaction_scope
from app.modules.bid.infrastructure.models import BidProject
from app.modules.system.models import MappingAnalysisCache
from app.modules.system.task_schemas import AsyncTaskCreate, AsyncTaskKind, AsyncTaskResponse
from app.modules.system.task_service import AsyncTaskService


class MappingAnalysisService:
    """Queue and cache workbook analysis without doing workbook I/O in HTTP."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def cached_or_enqueue(
        self,
        *,
        project_id: UUID,
        file_id: UUID,
        analysis_key: str,
        payload_json: dict[str, object],
        actor_id: UUID,
    ) -> dict[str, object] | AsyncTaskResponse:
        async with transaction_scope(self.session):
            cache: MappingAnalysisCache | None = await self.session.scalar(
                select(MappingAnalysisCache).where(
                    MappingAnalysisCache.project_id == project_id,
                    MappingAnalysisCache.file_id == file_id,
                    MappingAnalysisCache.analysis_key == analysis_key,
                )
            )
            if cache is not None:
                if cache.status == "SUCCEEDED" and cache.result_json is not None:
                    return cache.result_json
                return await AsyncTaskService(self.session).get(cache.async_task_id)
            # Lock the parent before inserting an absent cache key. Locking a
            # nonexistent unique key first can deadlock concurrent cache misses.
            await self.session.scalar(
                select(BidProject).where(BidProject.id == project_id).with_for_update()
            )
            second_cache: MappingAnalysisCache | None = await self.session.scalar(
                select(MappingAnalysisCache)
                .where(
                    MappingAnalysisCache.project_id == project_id,
                    MappingAnalysisCache.file_id == file_id,
                    MappingAnalysisCache.analysis_key == analysis_key,
                )
                .with_for_update()
            )
            if second_cache is not None:
                if second_cache.status == "SUCCEEDED" and second_cache.result_json is not None:
                    return second_cache.result_json
                queue = AsyncTaskService(self.session)
                return queue._response(await queue._task_for_update(second_cache.async_task_id))
            task = await AsyncTaskService(self.session).enqueue(
                AsyncTaskCreate(
                    project_id=project_id,
                    task_kind=AsyncTaskKind.MAPPING_STRUCTURE_ANALYSIS,
                    created_by=actor_id,
                    payload_json={
                        **payload_json,
                        "cache_key": analysis_key,
                        "file_id": str(file_id),
                    },
                )
            )
            self.session.add(
                MappingAnalysisCache(
                    project_id=project_id,
                    file_id=file_id,
                    async_task_id=task.id,
                    analysis_key=analysis_key,
                    status="PENDING",
                )
            )
            await self.session.flush()
            return task

    async def require_cached(
        self, project_id: UUID, file_id: UUID, analysis_key: str
    ) -> dict[str, object]:
        cache = await self.session.scalar(
            select(MappingAnalysisCache).where(
                MappingAnalysisCache.project_id == project_id,
                MappingAnalysisCache.file_id == file_id,
                MappingAnalysisCache.analysis_key == analysis_key,
                MappingAnalysisCache.status == "SUCCEEDED",
            )
        )
        if cache is None and analysis_key.startswith("RECOMMENDATION_TEMPLATE_STRUCTURE:"):
            prefix, sheet_name, header = analysis_key.rsplit(":", 2)
            fallback = await self.session.scalar(
                select(MappingAnalysisCache).where(
                    MappingAnalysisCache.project_id == project_id,
                    MappingAnalysisCache.file_id == file_id,
                    MappingAnalysisCache.analysis_key == f"{prefix}::{header}",
                    MappingAnalysisCache.status == "SUCCEEDED",
                )
            )
            if (
                fallback
                and fallback.result_json
                and fallback.result_json.get("sheet_name") == sheet_name
            ):
                cache = fallback
        if cache is None or cache.result_json is None:
            raise AppError("MAPPING_ANALYSIS_REQUIRED", "请先打开并完成模板结构解析后再保存", 409)
        return cache.result_json

    async def mark_running(self, task_id: UUID) -> MappingAnalysisCache:
        async with transaction_scope(self.session):
            cache = await self._cache_for_task(task_id, lock=True)
            cache.status = "RUNNING"
            return cache

    async def succeed(self, task_id: UUID, result: dict[str, object]) -> None:
        async with transaction_scope(self.session):
            cache = await self._cache_for_task(task_id, lock=True)
            cache.status = "SUCCEEDED"
            cache.result_json = result
            cache.error_message = None

    async def fail(self, task_id: UUID, message: str) -> None:
        async with transaction_scope(self.session):
            cache = await self._cache_for_task(task_id, lock=True)
            cache.status = "FAILED"
            cache.error_message = message[:2000]

    async def _cache_for_task(self, task_id: UUID, *, lock: bool) -> MappingAnalysisCache:
        statement = select(MappingAnalysisCache).where(
            MappingAnalysisCache.async_task_id == task_id
        )
        if lock:
            statement = statement.with_for_update()
        cache = await self.session.scalar(statement)
        if cache is None:
            raise RuntimeError(f"mapping cache missing for task {task_id}")
        return cache
