from __future__ import annotations

import argparse
import asyncio
import json

from app.core.database import SessionLocal, close_database
from app.modules.catalog.application.stale_cleanup import ProductImportStaleCleanupService


async def _run(*, older_than_hours: int, task_limit: int) -> None:
    try:
        async with SessionLocal() as session:
            report = await ProductImportStaleCleanupService(session).run(
                older_than_hours=older_than_hours, task_limit=task_limit
            )
        print(json.dumps(report.__dict__, ensure_ascii=False, sort_keys=True))
    finally:
        await close_database()


def main() -> int:
    parser = argparse.ArgumentParser(description="Delete stale Product Import staging tasks.")
    parser.add_argument("--older-than-hours", type=int, default=5)
    parser.add_argument("--task-limit", type=int, default=100)
    args = parser.parse_args()
    if args.older_than_hours <= 0 or args.task_limit <= 0:
        parser.error("--older-than-hours and --task-limit must be positive")
    asyncio.run(_run(older_than_hours=args.older_than_hours, task_limit=args.task_limit))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
