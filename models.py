import json
import boto3
from sqlalchemy import BigInteger, Integer, ForeignKey, String, Text, DateTime, func, create_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker

PrimaryKeyType = BigInteger().with_variant(Integer, "sqlite")


def get_database_url() -> str:
    """Fetch database credentials from Secrets Manager at Lambda cold start."""
    client = boto3.client("secretsmanager", region_name="eu-north-1")
    secret = client.get_secret_value(SecretId="qa-app/db-credentials")
    data = json.loads(secret["SecretString"])
    return (
        f"postgresql+psycopg2://{data['username']}:{data['password']}"
        f"@{data['host']}:{data['port']}/{data['dbname']}"
    )


# Initialised once at cold start
engine = create_engine(
    get_database_url(),
    pool_pre_ping=True,
)

SessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,
    expire_on_commit=False,
)


class Base(DeclarativeBase):
    pass


class Conversation(Base):
    __tablename__ = "conversations"

    id: Mapped[int] = mapped_column(PrimaryKeyType, primary_key=True, autoincrement=True,)
    title: Mapped[str] = mapped_column(String, nullable=False)
    created_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )


class Message(Base):
    __tablename__ = "messages"

    id: Mapped[int] = mapped_column(PrimaryKeyType, primary_key=True,autoincrement=True)
    conversation_id: Mapped[int] = mapped_column(
        PrimaryKeyType,
        ForeignKey("conversations.id", ondelete="CASCADE"),
        nullable=False,
    )
    role: Mapped[str] = mapped_column(String, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
