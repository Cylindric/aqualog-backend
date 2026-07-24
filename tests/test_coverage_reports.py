from pathlib import Path

from fastapi.testclient import TestClient

from src.app import create_app
from src.config import Settings


def test_coverage_route_serves_generated_report_index(tmp_path: Path):
    reports_dir = tmp_path / "coverage"
    reports_dir.mkdir(parents=True, exist_ok=True)
    index_file = reports_dir / "index.html"
    index_file.write_text("<html><body>coverage-report</body></html>", encoding="utf-8")

    app = create_app(Settings(app_env="test", coverage_reports_dir=str(reports_dir)))

    with TestClient(app) as client:
        response = client.get("/coverage")

    assert response.status_code == 200
    assert "coverage-report" in response.text


def test_coverage_route_returns_not_found_for_missing_files(tmp_path: Path):
    reports_dir = tmp_path / "coverage"
    reports_dir.mkdir(parents=True, exist_ok=True)

    app = create_app(Settings(app_env="test", coverage_reports_dir=str(reports_dir)))

    with TestClient(app) as client:
        response = client.get("/coverage/missing.html")

    assert response.status_code == 404


def test_coverage_route_is_not_exposed_outside_dev_or_test(tmp_path: Path):
    reports_dir = tmp_path / "coverage"
    reports_dir.mkdir(parents=True, exist_ok=True)
    (reports_dir / "index.html").write_text("<html><body>hidden</body></html>", encoding="utf-8")

    app = create_app(
        Settings(
            app_env="prod",
            coverage_reports_dir=str(reports_dir),
            test_database_url=f"sqlite+pysqlite:///{tmp_path}/coverage-gate.db",
        )
    )

    with TestClient(app) as client:
        response = client.get("/coverage")

    assert response.status_code == 404
