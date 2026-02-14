from sqlalchemy import JSON, Column, Float, ForeignKey, Integer, String, Text, create_engine
from sqlalchemy.orm import declarative_base, relationship, sessionmaker

from core.config import DB_PATH

engine = create_engine(f"sqlite:///{DB_PATH}", future=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)
Base = declarative_base()


class Document(Base):
    __tablename__ = "documents"

    id = Column(Integer, primary_key=True)
    filename = Column(String, nullable=False)
    filepath = Column(String, nullable=False)
    page_count = Column(Integer, nullable=False)

    pages = relationship("Page", back_populates="document", cascade="all, delete-orphan")
    queries = relationship("QueryHistory", back_populates="document", cascade="all, delete-orphan")


class Page(Base):
    __tablename__ = "pages"

    id = Column(Integer, primary_key=True)
    document_id = Column(Integer, ForeignKey("documents.id"), nullable=False)
    page_number = Column(Integer, nullable=False)
    text = Column(Text, nullable=False)
    chunks = Column(JSON, nullable=False)
    vectors = Column(JSON, nullable=False)

    document = relationship("Document", back_populates="pages")


class QueryHistory(Base):
    __tablename__ = "query_history"

    id = Column(Integer, primary_key=True)
    document_id = Column(Integer, ForeignKey("documents.id"), nullable=False)
    query = Column(String, nullable=False)
    smoothing = Column(Float, nullable=False)
    threshold = Column(Float, nullable=False)
    top_k = Column(Integer, nullable=False)

    document = relationship("Document", back_populates="queries")


def init_db() -> None:
    Base.metadata.create_all(bind=engine)
