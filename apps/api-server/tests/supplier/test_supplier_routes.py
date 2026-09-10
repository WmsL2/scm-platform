from app.main import app


def test_final_app_exposes_supplier_recovery_commands() -> None:
    paths = app.openapi()["paths"]
    for command in ("resume", "unblacklist"):
        path = f"/api/v1/suppliers/{{supplier_id}}/commands/{command}"
        assert "post" in paths[path]
