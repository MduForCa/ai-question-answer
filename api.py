import json
import boto3
from groq import Groq, APIConnectionError, APIStatusError

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from mangum import Mangum


def get_groq_api_key() -> str:
    """Fetch Groq API key from Secrets Manager at Lambda cold start."""
    client = boto3.client("secretsmanager", region_name="eu-north-1")
    secret = client.get_secret_value(SecretId="qa-app/groq-api-key")
    return json.loads(secret["SecretString"])["GROQ_API_KEY"]


# Initialised once at cold start — reused across warm invocations
groq_client = Groq(api_key=get_groq_api_key())


app = FastAPI(
    title="AI Question and Answer",
    version="0.2.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "https://your-frontend-domain.com",  # update after frontend is deployed
    ],
    allow_credentials=False,
    allow_methods=["POST"],
    allow_headers=["Content-Type"],
)


class QuestionRequest(BaseModel):
    question1: str = Field(max_length=1000)


@app.post("/api/ask-one")
def ask_one(request: QuestionRequest):
    question = request.question1.strip()

    if not question:
        raise HTTPException(
            status_code=422,
            detail="Question must contain text.",
        )

    try:
        completion = groq_client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[{"role": "user", "content": question}],
            max_tokens=1024,
            temperature=0.7,
        )

    except APIConnectionError as exc:
        raise HTTPException(
            status_code=503,
            detail="Cannot connect to Groq. Check your API key and network.",
        ) from exc

    except APIStatusError as exc:
        raise HTTPException(
            status_code=502,
            detail=f"Groq returned HTTP {exc.status_code}.",
        ) from exc

    answer = completion.choices[0].message.content.strip()

    if not answer:
        raise HTTPException(
            status_code=502,
            detail="Groq did not generate an answer.",
        )

    return {
        "answer": answer,
    }


# Wraps FastAPI for AWS Lambda — entry point is app.main.handler
handler = Mangum(app, lifespan="off")
