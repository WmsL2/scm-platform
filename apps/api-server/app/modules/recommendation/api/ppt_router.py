import uuid
from io import BytesIO
from typing import Annotated
from urllib.parse import quote

from fastapi import APIRouter, Depends, status
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.contracts import ApiResponse, success
from app.core.database import SessionLocal, get_db_session
from app.modules.auth.dependencies import require_permission, require_permission_before_response
from app.modules.auth.schemas import CurrentUser
from app.modules.recommendation.application.ppt_service import PptSolutionService
from app.modules.recommendation.ppt_schemas import (
    PptGenerationCreateRequest,
    PptGenerationTaskResponse,
    PptPackageCreateRequest,
    PptPackageResponse,
    PptPriceBandAvailabilityResponse,
    PptRecommendationConfigResponse,
    PptRecommendationConfigUpdateRequest,
    PptSolutionPlanResponse,
    PptTemplateResponse,
)
from app.modules.system.task_schemas import AsyncTaskCreate, AsyncTaskKind, AsyncTaskResponse
from app.modules.system.task_service import AsyncTaskService

router = APIRouter(prefix="/ppt-solution-projects", tags=["ppt-solution"])
SessionDep = Annotated[AsyncSession, Depends(get_db_session, scope="function")]


@router.get(
    "/{project_id}/recommendation-config",
    response_model=ApiResponse[PptRecommendationConfigResponse | None],
)
async def get_recommendation_config(
    project_id: uuid.UUID,
    _: Annotated[CurrentUser, Depends(require_permission("recommendation:detail"))],
    session: SessionDep,
) -> ApiResponse[PptRecommendationConfigResponse | None]:
    return success(await PptSolutionService(session).config(project_id))


@router.put(
    "/{project_id}/recommendation-config",
    response_model=ApiResponse[PptRecommendationConfigResponse],
)
async def put_recommendation_config(
    project_id: uuid.UUID,
    payload: PptRecommendationConfigUpdateRequest,
    current: Annotated[CurrentUser, Depends(require_permission("recommendation:run"))],
    session: SessionDep,
) -> ApiResponse[PptRecommendationConfigResponse]:
    result = await PptSolutionService(session).save_config(project_id, payload, current.user_id)
    return success(result)


@router.get("/runs/{run_id}/plans", response_model=ApiResponse[list[PptSolutionPlanResponse]])
async def list_plans(
    run_id: uuid.UUID,
    _: Annotated[CurrentUser, Depends(require_permission("recommendation:detail"))],
    session: SessionDep,
) -> ApiResponse[list[PptSolutionPlanResponse]]:
    return success(await PptSolutionService(session).list_plans(run_id))


@router.post("/plans/{plan_id}/select", response_model=ApiResponse[PptSolutionPlanResponse])
async def select_plan(
    plan_id: uuid.UUID,
    current: Annotated[CurrentUser, Depends(require_permission("recommendation:review"))],
    session: SessionDep,
) -> ApiResponse[PptSolutionPlanResponse]:
    return success(await PptSolutionService(session).select_plan(plan_id, current.user_id))


@router.get(
    "/runs/{run_id}/plan-availability",
    response_model=ApiResponse[list[PptPriceBandAvailabilityResponse]],
)
async def get_plan_availability(
    run_id: uuid.UUID,
    _: Annotated[CurrentUser, Depends(require_permission("recommendation:detail"))],
    session: SessionDep,
) -> ApiResponse[list[PptPriceBandAvailabilityResponse]]:
    return success(await PptSolutionService(session).plan_availability(run_id))


@router.post(
    "/runs/{run_id}/commands/retry-plans",
    response_model=ApiResponse[AsyncTaskResponse],
    status_code=status.HTTP_202_ACCEPTED,
)
async def retry_incomplete_plans(
    run_id: uuid.UUID,
    current: Annotated[CurrentUser, Depends(require_permission("recommendation:run"))],
    session: SessionDep,
) -> ApiResponse[AsyncTaskResponse]:
    """Retry only missing slots from this Run's immutable candidate snapshot."""
    run = await PptSolutionService(session).repository.run(run_id)
    if run is None:
        from app.common.contracts import AppError

        raise AppError("RECOMMENDATION_RUN_NOT_FOUND", "推品任务不存在", 404)
    return success(
        await AsyncTaskService(session).enqueue(
            AsyncTaskCreate(
                project_id=run.project_id,
                run_id=run_id,
                task_kind=AsyncTaskKind.TYPE5_RECOMMENDATION_GENERATION,
                created_by=current.user_id,
                payload_json={"retry_plans": True},
            )
        )
    )


@router.get("/runs/{run_id}/packages", response_model=ApiResponse[list[PptPackageResponse]])
async def list_packages(
    run_id: uuid.UUID,
    _: Annotated[CurrentUser, Depends(require_permission("recommendation:detail"))],
    session: SessionDep,
) -> ApiResponse[list[PptPackageResponse]]:
    return success(await PptSolutionService(session).list_packages(run_id))


@router.post("/runs/{run_id}/packages", response_model=ApiResponse[PptPackageResponse])
async def create_package(
    run_id: uuid.UUID,
    payload: PptPackageCreateRequest,
    current: Annotated[CurrentUser, Depends(require_permission("recommendation:review"))],
    session: SessionDep,
) -> ApiResponse[PptPackageResponse]:
    return success(
        await PptSolutionService(session).create_package(run_id, payload, current.user_id)
    )


@router.delete("/packages/{package_id}", response_model=ApiResponse[bool])
async def delete_package(
    package_id: uuid.UUID,
    current: Annotated[CurrentUser, Depends(require_permission("recommendation:review"))],
    session: SessionDep,
) -> ApiResponse[bool]:
    return success(await PptSolutionService(session).delete_package(package_id, current.user_id))


@router.post(
    "/{project_id}/runs/{run_id}/generations",
    response_model=ApiResponse[AsyncTaskResponse],
    status_code=status.HTTP_202_ACCEPTED,
)
async def create_generation(
    project_id: uuid.UUID,
    run_id: uuid.UUID,
    payload: PptGenerationCreateRequest,
    current: Annotated[
        CurrentUser, Depends(require_permission_before_response("recommendation:export"))
    ],
) -> ApiResponse[AsyncTaskResponse]:
    async with SessionLocal.begin() as task_session:
        await AsyncTaskService(task_session).ensure_available(
            project_id, AsyncTaskKind.TYPE5_PPT_GENERATION
        )
        task = await PptSolutionService(task_session).create_generation(
            project_id,
            run_id,
            current.user_id,
            use_default_template=payload.use_default_template,
            template_code=payload.template_code,
        )
        async_task = await AsyncTaskService(task_session).enqueue(
            AsyncTaskCreate(
                project_id=project_id,
                run_id=run_id,
                task_kind=AsyncTaskKind.TYPE5_PPT_GENERATION,
                created_by=current.user_id,
                payload_json={"ppt_generation_task_id": str(task.id)},
            )
        )
    return success(async_task)


@router.get("/templates", response_model=ApiResponse[list[PptTemplateResponse]])
async def list_templates(
    _: Annotated[CurrentUser, Depends(require_permission("recommendation:detail"))],
) -> ApiResponse[list[PptTemplateResponse]]:
    return success(PptSolutionService.list_templates())


@router.get(
    "/{project_id}/generations", response_model=ApiResponse[list[PptGenerationTaskResponse]]
)
async def list_generations(
    project_id: uuid.UUID,
    _: Annotated[CurrentUser, Depends(require_permission("recommendation:detail"))],
    session: SessionDep,
) -> ApiResponse[list[PptGenerationTaskResponse]]:
    return success(await PptSolutionService(session).list_generations(project_id))


@router.get("/generations/{task_id}/files/{file_id}/download")
async def download_generation(
    task_id: uuid.UUID,
    file_id: uuid.UUID,
    _: Annotated[CurrentUser, Depends(require_permission("recommendation:export"))],
    session: SessionDep,
) -> StreamingResponse:
    file, content = await PptSolutionService(session).download(task_id, file_id)
    disposition = (
        'attachment; filename="ppt-solution.pptx"; '
        f"filename*=UTF-8''{quote(file.original_filename, safe='')}"
    )
    return StreamingResponse(
        BytesIO(content),
        media_type="application/vnd.openxmlformats-officedocument.presentationml.presentation",
        headers={"Content-Disposition": disposition},
    )
