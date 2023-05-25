import pytest
from fastapi.testclient import TestClient
from whisper_api import app


"""
Test that the frontend files are served correctly.
"""

client = TestClient(app)


def test_index_html():
    """
    Test that the index.html file is served correctly.
    """
    response = client.get("/index.html")
    assert response.status_code == 200
    assert response.headers["content-type"] == "text/html; charset=utf-8"


def test_script_js():
    """
    Test that the script.js file is served correctly.
    """
    response = client.get("/script.js")
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/javascript"


def test_styles_css():
    """
    Test that the styles.css file is served correctly.
    """
    response = client.get("/styles.css")
    assert response.status_code == 200
    assert response.headers["content-type"] == "text/css; charset=utf-8"


def test_not_found():
    """
    Test that a 404 error is returned when a file is not found.
    """
    response = client.get("/not_found")
    assert response.status_code == 404
