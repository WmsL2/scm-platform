from app.main import app


def test_matching_routes_are_registered() -> None:
    paths = app.openapi()["paths"]

    assert "post" in paths["/api/v1/bid-projects/{project_id}/commands/start-matching"]
    assert "get" in paths["/api/v1/bid-projects/{project_id}/items/{item_id}/candidates"]
    assert "post" in paths["/api/v1/bid-projects/{project_id}/items/{item_id}/selections"]
    assert "post" in paths["/api/v1/bid-projects/{project_id}/items/{item_id}/no-quote"]
