from sqlalchemy import Column, Integer, String, Text, DateTime
from sqlalchemy.sql import func
from backend.commons.database import Base


class Paragraph(Base):
    __tablename__ = "paragraphs"

    id = Column(Integer, primary_key=True, index=True)
    content = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    def __repr__(self):
        return f"<Paragraph(id={self.id})>"

class WordFrequency(Base):
    __tablename__ = "word_frequencies"

    id = Column(Integer, primary_key=True, index=True)
    word = Column(String(100), unique=True, nullable=False)
    frequency = Column(Integer, nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
