from app.main import app
from app.modules.bid.api.router import router as bid_router


def test_bid_project_core_routes_are_registered() -> None:
    paths = app.openapi()["paths"]
    assert "post" in paths["/api/v1/bid-projects"]
    assert "get" in paths["/api/v1/bid-projects"]
    assert "get" in paths["/api/v1/bid-projects/{project_id}/items"]
    assert "get" in paths["/api/v1/bid-projects/{project_id}/files/{file_id}/download"]
    assert "post" in paths["/api/v1/bid-projects/{project_id}/exports"]
    assert "put" in paths["/api/v1/bid-projects/{project_id}/recommendation-scope"]


def test_bid_export_commits_its_session_before_sending_the_response() -> None:
    route = next(
        route
        for route in bid_router.routes
        if getattr(route, "path", None) == "/bid-projects/{project_id}/exports"
        and "POST" in getattr(route, "methods", set())
    )
    session_dependency = next(
        dependency for dependency in route.dependant.dependencies if dependency.name == "session"
    )

    assert session_dependency.scope == "function"
