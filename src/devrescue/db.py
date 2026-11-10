from datetime import datetime

from sqlalchemy import DateTime, Float, Integer, String, Text, create_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker

from .config import DATABASE_URL


class Base(DeclarativeBase):
    pass


class Incident(Base):
    __tablename__ = "incidents"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    kind: Mapped[str] = mapped_column(String(32))
    input_text: Mapped[str] = mapped_column(Text)
    diagnosis: Mapped[str] = mapped_column(Text)
    root_cause_correct: Mapped[int | None] = mapped_column(Integer, nullable=True)  # 1/0 once confirmed
    fix_minutes: Mapped[float | None] = mapped_column(Float, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class Feedback(Base):
    """One rated candidate answer; pairs are mined from these for DPO."""
    __tablename__ = "feedback"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    prompt: Mapped[str] = mapped_column(Text, index=True)
    response: Mapped[str] = mapped_column(Text)
    rating: Mapped[int] = mapped_column(Integer)  # 1 (bad) .. 5 (good)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


def make_session_factory(url: str = DATABASE_URL):
    if url.startswith("sqlite"):  # tests: share one in-memory DB across threads
        from sqlalchemy.pool import StaticPool

        engine = create_engine(url, connect_args={"check_same_thread": False}, poolclass=StaticPool)
    else:
        engine = create_engine(url, pool_pre_ping=True)
    Base.metadata.create_all(engine)
    return sessionmaker(engine, expire_on_commit=False)
