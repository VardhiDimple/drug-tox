"""API request/response schemas."""

from pydantic import BaseModel, Field


class SmilesRequest(BaseModel):
    smiles: str = Field(..., min_length=1, description="SMILES string")


class DiseaseRequest(BaseModel):
    query: str = Field(..., min_length=3, description="Disease name, symptoms, or keywords")


class GoEnrichmentRequest(BaseModel):
    genes: str | None = Field(None, description="Gene symbols (comma or newline separated)")


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=2000)
    context: dict | None = Field(default=None, description="Page context (panel, columns, etc.)")
    history: list[dict] | None = Field(default=None, description="Recent chat messages")
