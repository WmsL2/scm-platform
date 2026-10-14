"""Transactional domain recovery for durable tasks (no external I/O)."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.bid.infrastructure.models import (
    BidItemSelection,
    BidProject,
    BidProjectEvent,
    BidProjectItem,
    MatchTask,
)
from app.modules.recommendation.infrastructure.models import (
    PptGenerationTask,
    RecommendationCandidate,
    RecommendationRun,
)
from app.modules.system.models import AsyncTask, MappingAnalysisCache
from app.modules.type3_recommendation.infrastructure.models import Type3Candidate, Type3Run

_RUNNING = {"DRAFT", "QUEUED", "ANALYZING", "RETRIEVING", "RANKING"}


async def finish_domain(
    session: AsyncSession, task: AsyncTask, message: str, *, cancelled: bool = False
) -> None:
    """Converge the queue and business records in the caller's transaction."""
    project = await session.get(BidProject, task.project_id)
    if project is None:
        return
    now = datetime.now(UTC).replace(tzinfo=None)
    session.add(
        BidProjectEvent(
            project_id=project.id,
            actor_id=task.created_by,
            event_type="ASYNC_TASK_CANCELLED" if cancelled else "ASYNC_TASK_FAILED",
            from_status=project.status,
            to_status=project.status,
            note=f"任务 {task.id}：{message}",
        )
    )
    if task.task_kind == "MAPPING_STRUCTURE_ANALYSIS":
        cache = await session.scalar(
            select(MappingAnalysisCache).where(MappingAnalysisCache.async_task_id == task.id)
        )
        if cache is not None:
            cache.status, cache.error_message = "FAILED", message
        return
    if task.task_kind == "TYPE5_PPT_GENERATION":
        value = task.payload_json.get("ppt_generation_task_id")
        generation = await session.get(PptGenerationTask, uuid.UUID(str(value))) if value else None
        if generation is not None and generation.status in {"QUEUED", "RUNNING"}:
            generation.status, generation.error = "FAILED", message
            generation.completed_at = now
        return
    if task.task_kind in {"TYPE1_MATCH", "TYPE2_MATCH"}:
        match = await session.get(MatchTask, task.run_id) if task.run_id else None
        if match is not None and match.status in {"PENDING", "RUNNING"}:
            match.status, match.error_message = "FAILED", message
            match.completed_at = now
        has_results = await session.scalar(
            select(func.count())
            .select_from(BidItemSelection)
            .where(
                BidItemSelection.project_item_id.in_(
                    select(BidProjectItem.id).where(BidProjectItem.project_id == project.id)
                )
            )
        )
        target = str(task.payload_json.get("restore_project_status", "IMPORTED"))
        if target not in {"IMPORTED", "SELECTING", "READY"}:
            target = "SELECTING" if has_results else "IMPORTED"
    elif task.task_kind == "TYPE3_CANDIDATE_GENERATION":
        type3_run = await session.get(Type3Run, task.run_id) if task.run_id else None
        if type3_run is not None and type3_run.status in _RUNNING:
            type3_run.status, type3_run.error = "FAILED", message
        has_results = await session.scalar(
            select(func.count())
            .select_from(Type3Candidate)
            .join(Type3Run)
            .where(Type3Run.project_id == project.id)
        )
        target = "SELECTING" if has_results else "IMPORTED"
    else:
        run = await session.get(RecommendationRun, task.run_id) if task.run_id else None
        if run is not None and run.status in _RUNNING:
            run.status = "CANCELLED" if cancelled else "FAILED"
            run.error = message
        has_results = await session.scalar(
            select(func.count())
            .select_from(RecommendationCandidate)
            .join(RecommendationRun)
            .where(RecommendationRun.project_id == project.id)
        )
        target = "SELECTING" if has_results else "IMPORTED"
    if project.status == "MATCHING":
        previous = project.status
        project.status, project.updated_by = target, task.created_by
        session.add(
            BidProjectEvent(
                project_id=project.id,
                actor_id=task.created_by,
                event_type="ASYNC_TASK_PROJECT_RECOVERED",
                from_status=previous,
                to_status=target,
                note=message,
            )
        )


async def prepare_retry(session: AsyncSession, task: AsyncTask) -> None:
    """Use a fresh domain Run so retries never duplicate frozen candidates."""
    project = await session.get(BidProject, task.project_id)
    if project is None:
        raise RuntimeError("task project missing")
    if task.payload_json.get("retry_plans"):
        return
    if task.task_kind == "TYPE3_CANDIDATE_GENERATION" and task.run_id:
        old = await session.get(Type3Run, task.run_id)
        if old is None:
            raise RuntimeError("type3 task run missing")
        new = Type3Run(
            project_id=old.project_id,
            raw_remark_snapshot=old.raw_remark_snapshot,
            sheet_snapshot=old.sheet_snapshot,
            status="QUEUED",
            created_by=task.created_by,
        )
        session.add(new)
        await session.flush()
        task.run_id = new.id
    elif task.task_kind in {"TYPE4_RECOMMENDATION_AGENT", "TYPE5_RECOMMENDATION_GENERATION"}:
        old_run = await session.get(RecommendationRun, task.run_id) if task.run_id else None
        if old_run is None:
            raise RuntimeError("recommendation task run missing")
        new_run = RecommendationRun(
            project_id=old_run.project_id,
            status="QUEUED",
            created_by=task.created_by,
            raw_requirement_snapshot=old_run.raw_requirement_snapshot,
            ppt_config_snapshot=old_run.ppt_config_snapshot,
        )
        session.add(new_run)
        await session.flush()
        task.run_id = new_run.id
    elif task.task_kind in {"TYPE1_MATCH", "TYPE2_MATCH"}:
        task.run_id = uuid.uuid4()
    elif task.task_kind == "TYPE5_PPT_GENERATION":
        value = task.payload_json.get("ppt_generation_task_id")
        old_ppt = await session.get(PptGenerationTask, uuid.UUID(str(value))) if value else None
        if old_ppt is None:
            raise RuntimeError("PPT task missing")
        new_ppt = PptGenerationTask(
            project_id=old_ppt.project_id,
            run_id=old_ppt.run_id,
            template_file_id=old_ppt.template_file_id,
            template_code=old_ppt.template_code,
            template_version=old_ppt.template_version,
            status="QUEUED",
            provider=old_ppt.provider,
            model=old_ppt.model,
            prompt_version=old_ppt.prompt_version,
            created_by=task.created_by,
        )
        session.add(new_ppt)
        await session.flush()
        task.payload_json = {**task.payload_json, "ppt_generation_task_id": str(new_ppt.id)}
    else:
        cache = await session.scalar(
            select(MappingAnalysisCache).where(MappingAnalysisCache.async_task_id == task.id)
        )
        if cache:
            cache.status, cache.error_message = "PENDING", None
        return
    if task.task_kind not in {"TYPE1_MATCH", "TYPE2_MATCH", "TYPE5_PPT_GENERATION"}:
        previous = project.status
        project.status, project.updated_by = "MATCHING", task.created_by
        session.add(
            BidProjectEvent(
                project_id=project.id,
                actor_id=task.created_by,
                event_type="ASYNC_TASK_RETRIED",
                from_status=previous,
                to_status="MATCHING",
                note="从冻结输入创建新的运行记录",
            )
        )
