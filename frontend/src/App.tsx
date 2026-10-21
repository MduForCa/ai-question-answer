import { useState, type FormEvent } from "react";
import "./index.css";

type ApiResponse = {
  answer?: string;
  detail?: string | { msg?: string }[];
};

// Update this to your API Gateway URL after deployment
const API_URL = import.meta.env.VITE_API_URL ?? "http://127.0.0.1:8000/api/ask-one";
const MAX_QUESTION_LENGTH = 1000;

function getErrorMessage(data: ApiResponse, status: number): string {
  if (typeof data.detail === "string") {
    return data.detail;
  }

  if (Array.isArray(data.detail) && data.detail.length > 0) {
    return data.detail
      .map((item) => item.msg ?? "Invalid request.")
      .join(" ");
  }

  if (status === 503) {
    return "The AI service is unavailable. Please try again later.";
  }

  if (status === 502) {
    return "The AI service could not generate an answer. Please try again.";
  }

  return "The request could not be completed. Please try again.";
}

function App() {
  const [question, setQuestion] = useState("");
  const [answer, setAnswer] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const trimmedQuestion = question.trim();
  const characterCount = trimmedQuestion.length;

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();

    setAnswer("");
    setError("");

    if (!trimmedQuestion) {
      setError("Please enter a question before submitting.");
      return;
    }

    if (characterCount > MAX_QUESTION_LENGTH) {
      setError("Your question must not exceed 1,000 characters.");
      return;
    }

    setLoading(true);

    try {
      const response = await fetch(API_URL, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          question1: trimmedQuestion,
        }),
      });

      const data = (await response.json()) as ApiResponse;

      if (!response.ok) {
        throw new Error(getErrorMessage(data, response.status));
      }

      if (typeof data.answer !== "string" || !data.answer.trim()) {
        throw new Error(
          "The server returned no answer. Please try again."
        );
      }

      setAnswer(data.answer.trim());
    } catch (err) {
      if (err instanceof TypeError) {
        setError(
          "Cannot connect to the backend. Please try again later."
        );
      } else {
        setError(
          err instanceof Error
            ? err.message
            : "An unexpected error occurred."
        );
      }
    } finally {
      setLoading(false);
    }
  }

  function handleClear() {
    setQuestion("");
    setAnswer("");
    setError("");
  }

  return (
    <main className="app-shell">
      <header className="topbar">
        <a className="brand" href="/" aria-label="AI Answer home">
          <span className="brand-icon" aria-hidden="true">
            AI
          </span>
          <span>AI Answer</span>
        </a>

        <span className="connection-status">
          <span className="status-dot" />
          Cloud AI
        </span>
      </header>

      <section className="hero">
        <span className="eyebrow">YOUR PERSONAL AI ASSISTANT</span>

        <h1>
          Ask a question.
          <br />
          <span>Discover an answer.</span>
        </h1>

        <p className="hero-description">
          Ask about technology, business, science, or anything you want
          to understand. Your question is processed by a cloud AI model.
        </p>
      </section>

      <section className="workspace" aria-label="Question and answer">
        <form className="question-card" onSubmit={handleSubmit}>
          <div className="card-heading">
            <div>
              <h2>Your question</h2>
              <p>What would you like to know?</p>
            </div>

            <span className="card-icon" aria-hidden="true">
              ?
            </span>
          </div>

          <label className="visually-hidden" htmlFor="question">
            Enter your question
          </label>

          <textarea
            id="question"
            value={question}
            onChange={(event) => {
              setQuestion(event.target.value);
              setError("");
            }}
            placeholder="For example, how does interbank clearing work?"
            rows={5}
            maxLength={MAX_QUESTION_LENGTH}
            disabled={loading}
            aria-describedby="question-help character-count"
          />

          <div className="form-footer">
            <p id="question-help">
              Be clear and specific for a more useful answer.
            </p>

            <span
              id="character-count"
              className={
                characterCount >= MAX_QUESTION_LENGTH
                  ? "character-count limit-reached"
                  : "character-count"
              }
            >
              {characterCount}/{MAX_QUESTION_LENGTH}
            </span>
          </div>

          {error && (
            <div className="error-message" role="alert">
              <span aria-hidden="true">!</span>
              <p>{error}</p>
            </div>
          )}

          <div className="form-actions">
            <button
              className="submit-button"
              type="submit"
              disabled={loading || !trimmedQuestion}
            >
              {loading ? (
                <>
                  <span className="spinner" aria-hidden="true" />
                  Generating answer...
                </>
              ) : (
                <>
                  Get answer
                  <span aria-hidden="true">→</span>
                </>
              )}
            </button>

            <button
              className="clear-button"
              type="button"
              onClick={handleClear}
              disabled={loading || (!question && !answer && !error)}
            >
              Clear
            </button>
          </div>
        </form>

        <section
          className={`answer-card${answer ? " has-answer" : ""}`}
          aria-live="polite"
          aria-busy={loading}
        >
          <div className="card-heading">
            <div>
              <h2>Answer</h2>
              <p>Generated by Groq AI</p>
            </div>

            <span className="answer-icon" aria-hidden="true">
              ✦
            </span>
          </div>

          {loading ? (
            <div className="answer-placeholder">
              <span className="large-spinner" aria-hidden="true" />
              <h3>Thinking through your question...</h3>
              <p>
                Your question is being processed. The first answer may
                take a little longer while the model loads.
              </p>
            </div>
          ) : answer ? (
            <div className="answer-content">
              <p className="answer-text">{answer}</p>
              <div className="answer-meta">
                <span className="status-dot" />
                Answer generated
              </div>
            </div>
          ) : (
            <div className="answer-placeholder">
              <div className="empty-answer-icon" aria-hidden="true">
                <span>✦</span>
              </div>
              <h3>Your answer will appear here</h3>
              <p>
                Enter a question above and select "Get answer" to
                start a conversation with your AI model.
              </p>
            </div>
          )}
        </section>
      </section>

      <footer className="page-footer">
        <p>
          Powered by <strong>FastAPI</strong>, <strong>React</strong> and{" "}
          <strong>Groq</strong>
        </p>
        <p>Cloud AI · Built for learning</p>
      </footer>
    </main>
  );
}

export default App;
