
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)


def test_home_endpoint():
    response = client.get("/")
    assert response.status_code == 200


def test_ask_rejects_empty_resume():
    response = client.post(
        "/ask",
        json={
            "resume": "",
            "job_description": "Python developer with FastAPI skills",
        },
    )
    assert response.status_code == 422


def test_ask_rejects_empty_job_description():
    response = client.post(
        "/ask",
        json={
            "resume": "Python, FastAPI and SQL",
            "job_description": "",
        },
    )
    assert response.status_code == 422


def test_pdf_rejects_invalid_file_extension():
    response = client.post(
        "/analyze-pdf",
        data={"job_description": "Python developer with FastAPI skills"},
        files={"resume_file": ("resume.txt", b"not a PDF", "text/plain")},
    )
    assert response.status_code == 400


def test_pdf_rejects_empty_file():
    response = client.post(
        "/analyze-pdf",
        data={"job_description": "Python developer with FastAPI skills"},
        files={"resume_file": ("resume.txt", b"not a PDF", "text/plain")},
    )
    assert response.status_code == 400


def test_pdf_rejects_invalid_pdf_content():
    response = client.post(
        "/analyze-pdf",
        data={"job_description": "Python developer with FastAPI skills"},
        files={"resume_file": ("resume.txt", b"not a PDF", "text/plain")},
    )
    assert response.status_code == 400
