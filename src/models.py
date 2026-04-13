from pydantic import BaseModel, Field
from typing import List, Optional
import uuid

class Article(BaseModel):
    id: str
    title: str
    content: str

class ExtractionResult(BaseModel):
    summary: str = Field(description="A 1-sentence summary of the article")
    keywords: List[str] = Field(description="Key entities or concepts extracted from the article")

class Entity(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    description: Optional[str] = None
    source_article_id: Optional[str] = None
    # We do not explicitly store embedding here as ChromaDB handles it

class ResolutionResult(BaseModel):
    conservative_entity: str = Field(description="The most stable, correct, and broad entity")
    granular_entity: Optional[str] = Field(
        default=None, 
        description="The specific entity. Omit if identical or extremely similar to the conservative one"
    )
