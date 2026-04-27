from fastapi import FastAPI

from app import __doc__ as app_package_doc
from app.main import app


def test_package_layout_imports() -> None:
    assert app_package_doc is not None


def test_fastapi_app_exists() -> None:
    assert isinstance(app, FastAPI)
