from app.main import app


def test_bid_project_core_routes_are_registered() -> None:
    paths = app.openapi()["paths"]
    assert "post" in paths["/api/v1/bid-projects"]
    assert "get" in paths["/api/v1/bid-projects"]
    assert "get" in paths["/api/v1/bid-projects/{project_id}/items"]
    assert "get" in paths["/api/v1/bid-projects/{project_id}/files/{file_id}/download"]
    assert "post" in paths["/api/v1/bid-projects/{project_id}/exports"]
