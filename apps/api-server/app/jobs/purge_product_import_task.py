from __future__ import annotations

import argparse
import asyncio
import json
import uuid

from app.common.contracts import AppError
from app.core.database import SessionLocal, close_database
from app.modules.catalog.application.import_service import ProductImportService


async def _run(task_id: uuid.UUID, minimum_age_hours: int) -> int:
    try:
        async with SessionLocal() as session:
            deleted = await ProductImportService(session).purge_abandoned_task(
                task_id, minimum_age_hours=minimum_age_hours
            )
        print(
            json.dumps(
                {
                    "task_id": str(task_id),
                    "staging_deleted": deleted,
                    "message": (
                        "Staging data deleted"
                        if deleted
                        else "Temporary file deletion failed; task was retained for retry"
                    ),
                },
                ensure_ascii=False,
            )
        )
        return 0 if deleted else 1
    except AppError as exc:
        print(json.dumps({"code": exc.code, "message": exc.message}, ensure_ascii=False))
        return 2
    finally:
        await close_database()


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Manually purge one abandoned Product Import task."
    )
    parser.add_argument("--task-id", required=True, type=uuid.UUID)
    parser.add_argument("--minimum-age-hours", type=int, default=24)
    args = parser.parse_args()
    if args.minimum_age_hours <= 0:
        parser.error("--minimum-age-hours must be positive")
    return asyncio.run(_run(args.task_id, args.minimum_age_hours))


if __name__ == "__main__":
    raise SystemExit(main())
