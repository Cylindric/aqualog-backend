from pathlib import Path


def test_compose_file_defines_api_service_with_dockerfile_build():
    compose = Path("docker-compose.yml").read_text(encoding="utf-8")

    assert "services:" in compose
    assert "api:" in compose
    assert "build:" in compose
    assert "context: ." in compose
    assert "dockerfile: Dockerfile" in compose


def test_compose_file_exposes_default_api_port_mapping():
    compose = Path("docker-compose.yml").read_text(encoding="utf-8")

    assert '${AQUALOG_HOST_PORT:-8000}:8000' in compose


def test_compose_file_defines_overridable_runtime_defaults():
    compose = Path("docker-compose.yml").read_text(encoding="utf-8")

    assert '${AQUALOG_APP_ENV:-dev}' in compose
    assert '${AQUALOG_API_VERSION:-v1}' in compose
    assert '${AQUALOG_LOG_LEVEL:-INFO}' in compose
