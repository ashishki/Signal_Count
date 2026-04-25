from pathlib import Path


CI_PATH = Path(".github/workflows/ci.yml")


def test_ci_workflow_targets_python_app_and_tests() -> None:
    content = CI_PATH.read_text(encoding="utf-8")

    assert 'python-version: "3.11"' in content
    assert "pip install -r requirements-dev.txt -e ." in content
    assert "ruff check app/ tests/" in content
    assert "ruff format --check app/ tests/" in content
    assert "python -m pytest tests/ -q --tb=short" in content


def test_ci_workflow_uses_placeholder_env_values() -> None:
    content = CI_PATH.read_text(encoding="utf-8")

    assert 'SIGNAL_COUNT_ENV: "test"' in content
    assert 'LLM_API_KEY: "test-key"' in content
    assert "${{ secrets." in content
    assert "sk-" not in content
