import pytest

from unittest.mock import Mock, patch

from fastapi.testclient import TestClient

from main import app, calculate_match, find_skills, skill_is_present

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
        files={"resume_file": ("resume.pdf", b"", "application/pdf")},
    )
    assert response.status_code == 400
    assert "empty" in response.json()["detail"].lower()


def test_pdf_rejects_invalid_pdf_content():
    response = client.post(
        "/analyze-pdf",
        data={"job_description": "Python developer with FastAPI skills"},
        files={
            "resume_file": (
                "resume.pdf",
                b"not a PDF",
                "application/pdf",
            )
        },
    )
    assert response.status_code == 400
    assert "valid PDF" in response.json()["detail"]


def test_skill_alias_matches_fast_api():
    assert skill_is_present("I built an API with Fast API.", "fastapi")


def test_skill_matching_uses_word_boundaries():
    assert not skill_is_present("I use javascript.", "java")


def test_find_skills_excludes_learning_goals():
    matching, missing = find_skills(
        "Currently learning Python. Built a project using FastAPI.",
        ["python", "fastapi"],
    )
    assert "fastapi" in matching
    assert "python" in missing


def test_find_skills_excludes_explicit_negative_evidence():
    matching, missing = find_skills(
        "I have no experience with Python. I use SQL in projects.",
        ["python", "sql"],
    )
    assert "sql" in matching
    assert "python" in missing


def test_calculate_match_percentage():
    assert calculate_match(["python", "sql"], ["python", "sql", "fastapi"]) == pytest.approx(200 / 3)


def test_calculate_match_deduplicates_required_skills():
    assert calculate_match(["python"], ["python", "python"]) == 100.0


def test_calculate_match_returns_zero_without_requirements():
    assert calculate_match(["python"], []) == 0.0


@patch("main.OpenAI")
@patch.dict("os.environ", {"GROQ_API_KEY": "test-key"})
def test_ask_returns_analysis_when_ai_succeeds(mock_openai):
    mock_client = Mock()
    mock_openai.return_value = mock_client
    mock_client.chat.completions.create.return_value.choices = [
        Mock(message=Mock(content="Test analysis"))
    ]

    response = client.post(
        "/ask",
        json={
            "resume": "Python and FastAPI project experience",
            "job_description": "Python developer with FastAPI skills",
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["answer"] == "Test analysis"
    assert "match_percentage" in body
    assert "processing_time_seconds" in body


@patch("main.OpenAI")
@patch.dict("os.environ", {"GROQ_API_KEY": "test-key"})
def test_ask_returns_502_when_ai_provider_fails(mock_openai):
    mock_client = Mock()
    mock_openai.return_value = mock_client
    mock_client.chat.completions.create.side_effect = RuntimeError("provider error")

    response = client.post(
        "/ask",
        json={
            "resume": "Python and FastAPI project experience",
            "job_description": "Python developer with FastAPI skills",
        },
    )

    assert response.status_code == 502
    assert "Groq AI request failed" in response.json()["detail"]

def test_pdf_rejects_oversized_file():
    response = client.post(
        "/analyze-pdf",
        data={"job_description": "Python developer with FastAPI skills"},
        files={
            "resume_file": (
                "large.pdf",
                b"%PDF-" + b"A" * (5 * 1024 * 1024),
                "application/pdf",
            )
        },
    )

    assert response.status_code == 400
    assert "5 MB" in response.json()["detail"]
