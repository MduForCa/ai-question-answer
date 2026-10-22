import sys
import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient

# ─── Block AWS call before api.py is imported ─────────────────────
with patch("boto3.client") as mock_boto:
    mock_boto.return_value.get_secret_value.return_value = {
        "SecretString": '{"GROQ_API_KEY": "test-key"}'
    }
    from api import app

client = TestClient(app)


def make_groq_response(content: str):
    """Build a mock Groq response matching the real SDK shape."""
    mock_response = MagicMock()
    mock_response.choices[0].message.content = content
    return mock_response


# ─── Valid question ───────────────────────────────────────────────

def test_valid_question_returns_answer():
    with patch("api.groq_client.chat.completions.create",
               return_value=make_groq_response("A payment is a transfer of value.")):
        response = client.post(
            "/api/ask-one",
            json={"question1": "What is a payment?"},
        )

    assert response.status_code == 200
    assert response.json() == {"answer": "A payment is a transfer of value."}


# ─── Validation ───────────────────────────────────────────────────

def test_empty_question_is_rejected():
    response = client.post(
        "/api/ask-one",
        json={"question1": ""},
    )
    assert response.status_code == 422
    assert response.json()["detail"] == "Question must contain text."


def test_question_exceeding_maximum_length_is_rejected():
    response = client.post(
        "/api/ask-one",
        json={"question1": "A" * 1001},
    )
    assert response.status_code == 422


def test_question_at_maximum_length():
    with patch("api.groq_client.chat.completions.create",
               return_value=make_groq_response("Answer received.")):
        response = client.post(
            "/api/ask-one",
            json={"question1": "A" * 1000},
        )

    assert response.status_code == 200
    assert response.json() == {"answer": "Answer received."}


def test_question_with_surrounding_spaces():
    with patch("api.groq_client.chat.completions.create",
               return_value=make_groq_response("Payment is a transfer of value.")) as mock_groq:
        response = client.post(
            "/api/ask-one",
            json={"question1": " What is a payment?  "},
        )

        # Verify the question was stripped before sending to Groq
        sent_messages = mock_groq.call_args.kwargs["messages"]
        sent_content = sent_messages[-1]["content"]

    assert response.status_code == 200
    assert sent_content == "What is a payment?"


# ─── Groq error handling ──────────────────────────────────────────

def test_groq_returns_empty_answer():
    with patch("api.groq_client.chat.completions.create",
               return_value=make_groq_response("")):
        response = client.post(
            "/api/ask-one",
            json={"question1": "What is a payment?"},
        )

    assert response.status_code == 502
    assert response.json() == {"detail": "Groq did not generate an answer."}


def test_groq_unavailable():
    from groq import APIConnectionError
    with patch("api.groq_client.chat.completions.create",
               side_effect=APIConnectionError(request=MagicMock())):
        response = client.post(
            "/api/ask-one",
            json={"question1": "What is a payment?"},
        )

    assert response.status_code == 503
    assert response.json()["detail"] == (
        "Cannot connect to Groq. Check your API key and network."
    )


def test_groq_api_status_error():
    from groq import APIStatusError
    mock_response = MagicMock()
    mock_response.status_code = 429

    with patch("api.groq_client.chat.completions.create",
               side_effect=APIStatusError(
                   message="Rate limit exceeded",
                   response=mock_response,
                   body={}
               )):
        response = client.post(
            "/api/ask-one",
            json={"question1": "What is a payment?"},
        )

    assert response.status_code == 502
    assert response.json()["detail"] == "Groq returned HTTP 429."


def test_whitespace_only_question_is_rejected():
    response = client.post(
        "/api/ask-one",
        json={"question1": "   "},
    )

    assert response.status_code == 422
    assert response.json()["detail"] == "Question must contain text."