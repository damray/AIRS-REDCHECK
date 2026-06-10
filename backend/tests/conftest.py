from collections.abc import Generator

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.db.session import get_db
from app.main import app
from app.models import (  # noqa: F401
    Attempt,
    Dataset,
    EvaluationError,
    EvaluationJob,
    EvaluationJobAttempt,
    HumanReview,
    ImportErrorRecord,
    JudgePromptProfile,
    JudgeResultRecord,
    MappingProfile,
    PortkeyGatewayProfile,
    Project,
    Stream,
)


@pytest.fixture()
def db_session() -> Generator[Session]:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        future=True,
    )
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)
    with session_factory() as session:
        yield session


@pytest.fixture()
def client(db_session: Session) -> Generator[object]:
    def override_get_db() -> Generator[Session]:
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    try:
        from fastapi.testclient import TestClient

        yield TestClient(app)
    finally:
        app.dependency_overrides.clear()
