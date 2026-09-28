import uuid
from io import BytesIO
from typing import Annotated
from urllib.parse import quote

from fastapi import APIRouter, BackgroundTasks, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.contracts import ApiResponse, success
from app.core.database import FunctionSessionDep, get_db_session
from app.infrastructure.adapters import get_task_queue
from app.modules.auth.dependencies import require_permission, require_permission_before_response
from app.modules.auth.schemas import CurrentUser
from app.modules.recommendation.application.ppt_service import PptSolutionService
from app.modules.recommendation.ppt_schemas import (
    PptGenerationCreateRequest,
    PptGenerationTaskResponse,
    PptPackageCreateRequest,
    PptPackageResponse,
)

router = APIRouter(prefix="/ppt-solution-projects", tags=["ppt-solution"])
SessionDep = Annotated[AsyncSession, Depends(get_db_session)]


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
    response_model=ApiResponse[PptGenerationTaskResponse],
)
async def create_generation(
    project_id: uuid.UUID,
    run_id: uuid.UUID,
    payload: PptGenerationCreateRequest,
    current: Annotated[
        CurrentUser, Depends(require_permission_before_response("recommendation:export"))
    ],
    session: FunctionSessionDep,
    background_tasks: BackgroundTasks,
) -> ApiResponse[PptGenerationTaskResponse]:
    service = PptSolutionService(session)
    task = await service.create_generation(
        project_id,
        run_id,
        current.user_id,
        use_default_template=payload.use_default_template,
    )
    background_tasks.add_task(_dispatch_generation, task.id)
    return success(task)


async def _dispatch_generation(task_id: uuid.UUID) -> None:
    from app.core.database import SessionLocal

    async with SessionLocal() as task_session:
        await get_task_queue().enqueue(
            PptSolutionService(task_session).execute_generation,
            task_id,
        )


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
