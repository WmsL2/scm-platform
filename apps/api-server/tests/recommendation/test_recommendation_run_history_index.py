from app.modules.recommendation.infrastructure.models import RecommendationRun


def test_run_history_index_matches_project_filter_and_created_at_sort() -> None:
    index_columns = {
        index.name: tuple(column.name for column in index.columns)
        for index in RecommendationRun.__table__.indexes
    }

    assert index_columns["ix_scm_recommendation_run_project_created_at"] == (
        "project_id",
        "created_at",
    )
