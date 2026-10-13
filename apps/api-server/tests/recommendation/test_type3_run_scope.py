from datetime import datetime
from types import SimpleNamespace
from typing import cast
from uuid import uuid4

from app.modules.type3_recommendation.application.service import Type3RecommendationService
from app.modules.type3_recommendation.infrastructure.models import Type3Run


def test_type3_run_response_exposes_frozen_sheet_scope() -> None:
    run = cast(
        Type3Run,
        SimpleNamespace(
            id=uuid4(),
            project_id=uuid4(),
            status="WAITING_CONFIRMATION",
            raw_remark_snapshot="",
            parsed_remark=None,
            error=None,
            provider=None,
            model=None,
            prompt_version=None,
            created_at=datetime(2026, 10, 13),
            updated_at=datetime(2026, 10, 13),
            sheet_snapshot=[
                {"sheet_name": "家用电器", "selected_nodes": [{"node_id": "A1"}]},
                {
                    "sheet_name": "个护健康",
                    "selected_nodes": [{"node_id": "A2"}, {"node_id": "A3"}],
                },
            ],
        ),
    )

    response = Type3RecommendationService._run_response(run)

    assert [(item.sheet_name, item.selected_node_count) for item in response.sheet_summaries] == [
        ("家用电器", 1),
        ("个护健康", 2),
    ]
