
import json
import pytest

from unittest.mock import patch
from sqlalchemy import create_engine, inspect, event
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import sessionmaker


# ─── Block AWS call before models.py is imported ─────────────────
with patch("boto3.client") as mock_boto:
    mock_boto.return_value.get_secret_value.return_value = {
        "SecretString": json.dumps({
            "username": "test",
            "password": "test",
            "host": "localhost",
            "port": "5432",
            "dbname": "testdb",
        })
    }

    from models import Base, Conversation, Message


# ─── In-memory SQLite engine for tests ───────────────────────────
@pytest.fixture(scope="module")
def engine():
    """Create an in-memory SQLite database for the test module."""
    test_engine = create_engine("sqlite:///:memory:")

    # Enable SQLite foreign-key enforcement on every connection.
    @event.listens_for(test_engine, "connect")
    def enable_foreign_keys(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    Base.metadata.create_all(test_engine)

    yield test_engine

    Base.metadata.drop_all(test_engine)
    test_engine.dispose()


@pytest.fixture
def session(engine):
    """Provide a session that rolls back and closes after each test."""
    Session = sessionmaker(bind=engine)
    db = Session()

    yield db

    db.rollback()
    db.close()


# ─── Table structure ──────────────────────────────────────────────

def test_conversations_table_exists(engine):
    inspector = inspect(engine)

    assert "conversations" in inspector.get_table_names()


def test_messages_table_exists(engine):
    inspector = inspect(engine)

    assert "messages" in inspector.get_table_names()


def test_conversations_has_expected_columns(engine):
    inspector = inspect(engine)

    columns = {
        column["name"]
        for column in inspector.get_columns("conversations")
    }

    assert columns == {
        "id",
        "title",
        "created_at",
        "updated_at",
    }


def test_messages_has_expected_columns(engine):
    inspector = inspect(engine)

    columns = {
        column["name"]
        for column in inspector.get_columns("messages")
    }

    assert columns == {
        "id",
        "conversation_id",
        "role",
        "content",
        "created_at",
    }


# ─── Conversation model ──────────────────────────────────────────

def test_create_conversation(session):
    convo = Conversation(title="What is a payment?")

    session.add(convo)
    session.flush()

    assert convo.id is not None
    assert convo.title == "What is a payment?"


def test_conversation_title_is_required(session):
    convo = Conversation()

    session.add(convo)

    with pytest.raises(IntegrityError):
        session.flush()


def test_conversation_title_is_stored_correctly(session):
    convo = Conversation(title="Tell me about AWS Lambda")

    session.add(convo)
    session.flush()

    fetched = session.get(Conversation, convo.id)

    assert fetched is not None
    assert fetched.title == "Tell me about AWS Lambda"


# ─── Message model ────────────────────────────────────────────────

def test_create_message(session):
    convo = Conversation(title="Test conversation")

    session.add(convo)
    session.flush()

    msg = Message(
        conversation_id=convo.id,
        role="user",
        content="What is a payment?",
    )

    session.add(msg)
    session.flush()

    assert msg.id is not None
    assert msg.role == "user"
    assert msg.content == "What is a payment?"
    assert msg.conversation_id == convo.id


def test_message_role_and_content_stored_correctly(session):
    convo = Conversation(title="Role test")

    session.add(convo)
    session.flush()

    msg = Message(
        conversation_id=convo.id,
        role="assistant",
        content="A payment is a transfer of value.",
    )

    session.add(msg)
    session.flush()

    fetched = session.get(Message, msg.id)

    assert fetched is not None
    assert fetched.role == "assistant"
    assert fetched.content == "A payment is a transfer of value."


def test_message_requires_conversation_id(session):
    msg = Message(
        role="user",
        content="Orphan message",
    )

    session.add(msg)

    with pytest.raises(IntegrityError):
        session.flush()


def test_message_requires_existing_conversation(session):
    msg = Message(
        conversation_id=999999,
        role="user",
        content="This conversation does not exist",
    )

    session.add(msg)

    with pytest.raises(IntegrityError):
        session.flush()


def test_multiple_messages_per_conversation(session):
    convo = Conversation(title="Multi-message conversation")

    session.add(convo)
    session.flush()

    messages = [
        Message(
            conversation_id=convo.id,
            role="user",
            content="Question 1",
        ),
        Message(
            conversation_id=convo.id,
            role="assistant",
            content="Answer 1",
        ),
        Message(
            conversation_id=convo.id,
            role="user",
            content="Question 2",
        ),
    ]

    session.add_all(messages)
    session.flush()

    results = (
        session.query(Message)
        .filter_by(conversation_id=convo.id)
        .all()
    )

    assert len(results) == 3


# ─── Cascade delete ───────────────────────────────────────────────

def test_deleting_conversation_cascades_to_messages(session):
    convo = Conversation(title="To be deleted")

    session.add(convo)
    session.flush()

    convo_id = convo.id

    msg = Message(
        conversation_id=convo_id,
        role="user",
        content="This message should be deleted too.",
    )

    session.add(msg)
    session.flush()

    # Delete the parent row directly so this tests the database's
    # ON DELETE CASCADE constraint rather than ORM relationship logic.
    session.execute(
        Conversation.__table__.delete().where(
            Conversation.id == convo_id
        )
    )
    session.flush()

    remaining = (
        session.query(Message)
        .filter_by(conversation_id=convo_id)
        .all()
    )

    assert remaining == []
