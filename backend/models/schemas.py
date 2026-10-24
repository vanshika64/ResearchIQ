from typing import Literal
from pydantic import BaseModel, Field

ResearchKind = Literal["search", "question", "summary", "comparison", "gaps", "report"]

class ResearchRequest(BaseModel):
    query: str = Field(min_length=1, max_length=4000)
    paper_ids: list[int] = Field(default_factory=list, max_length=20)
    kind: ResearchKind = "question"
