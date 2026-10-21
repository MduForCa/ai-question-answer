
import json
from unittest.mock import patch
from fastapi.testclient import TestClient
from api import app


client = TestClient(app)


def test_valid_question_returns_answer():
    ollama_response = {
        "response": "A payment is a transfer of value."
    }

    with patch("api.urlopen") as mock_urlopen:
        mock_urlopen.return_value.__enter__.return_value.read.return_value = (
            json.dumps(ollama_response).encode("utf-8")
        )

        response = client.post(
            "/api/ask-one",
            json={"question1": "What is a payment?"},
        )

    assert response.status_code == 200
    assert response.json() == {
        "answer": "A payment is a transfer of value."
    }

def test_ollama_returns_malformed_json():
    with patch("api.urlopen") as mock_urlopen:
        mock_urlopen.return_value.__enter__.return_value.read.return_value = (
            b"{invalid json}"
        )

        response = client.post(
            "/api/ask-one",
            json={"question1": "What is a payment"},
        )

        assert response.status_code == 502
        assert response.json() == {
            "detail": "Ollama returned an invalid response."
        }


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

def test_ollama_unavailable():
    with patch(
        "api.urlopen",
        side_effect=ConnectionError("Ollama unavailable"),
    ):

        response = client.post(
            "/api/ask-one",
            json={"question1": "What is a payment?"},
        )

    assert response.status_code == 503
    assert response.json()["detail"] == (
        "Cannot connect to Ollama. Check that Ollama is running."
    )


def test_question_with_surrounding_spaces():
    ollama_response = {
        "response": "Payment is a transfer of value."
    }

    with patch("api.urlopen") as mock_urlopen:
        mock_urlopen.return_value.__enter__.return_value.read.return_value = (
            json.dumps(ollama_response).encode("utf-8")
        )

        response = client.post(
            "/api/ask-one",
            json={"question1": " What is a payment?  "},
        )

        sent_request = mock_urlopen.call_args.args[0]
        sent_payload = json.loads(sent_request.data.decode("utf-8"))

    assert response.status_code == 200
    assert sent_payload["prompt"] == "What is a payment?"



def test_question_at_maximum_length():
    ollama_response = {"response": "Answer received."}

    with patch("api.urlopen") as mock_urlopen:
        mock_urlopen.return_value.__enter__.return_value.read.return_value = (
            json.dumps(ollama_response).encode("utf-8")
        )

        response = client.post(
            "/api/ask-one",
            json={"question1": "A" * 1000},
        )

    assert response.status_code == 200
    assert response.json() == {"answer": "Answer received."}


def test_ollama_returns_empty_answer():
    ollama_response = {"response": ""}

    with patch("api.urlopen") as mock_urlopen:
        mock_urlopen.return_value.__enter__.return_value.read.return_value = (
            json.dumps(ollama_response).encode("utf-8")
        )

        response = client.post(
            "/api/ask-one",
            json={"question1": "What is a payment?"},
        )

    assert response.status_code == 502
    assert response.json() == {
        "detail": "Ollama did not generate an answer."
    }
