import pytest

from app.main import app


@pytest.fixture(autouse=True)
def clear_optional_app_state() -> None:
    yield
    if hasattr(app.state, "chain_receipt_service"):
        delattr(app.state, "chain_receipt_service")
