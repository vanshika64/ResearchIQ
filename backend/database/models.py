from sqlalchemy import Column, Integer, String, Text, DateTime, JSON, ForeignKey, create_engine
from sqlalchemy.orm import declarative_base
from datetime import datetime, timezone
from core.settings import settings

Base = declarative_base()
engine = create_engine(settings.DATABASE_URL, connect_args={"check_same_thread": False} if settings.DATABASE_URL.startswith("sqlite") else {})

class Paper(Base):
    __tablename__ = "papers"
    id = Column(Integer, primary_key=True)
    owner_id = Column(String, index=True, nullable=False)
    title = Column(String, nullable=False)
    filename = Column(String, nullable=False)
    text = Column(Text, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

class Interaction(Base):
    __tablename__ = "interactions"
    id = Column(Integer, primary_key=True)
    owner_id = Column(String, index=True, nullable=False)
    kind = Column(String, nullable=False)
    query = Column(Text, nullable=False)
    answer = Column(Text, nullable=False)
    sources = Column(JSON, default=list)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

class PaperChunk(Base):
    __tablename__ = "paper_chunks"
    id = Column(Integer, primary_key=True)
    owner_id = Column(String, index=True, nullable=False)
    paper_id = Column(Integer, ForeignKey("papers.id", ondelete="CASCADE"), index=True, nullable=False)
    position = Column(Integer, nullable=False)
    page_number = Column(Integer, nullable=False)
    text = Column(Text, nullable=False)
    embedding = Column(JSON, nullable=False)
