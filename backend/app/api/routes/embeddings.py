from __future__ import annotations

import hashlib

from fastapi import APIRouter

from app.api.schemas import EmbeddingData, EmbeddingRequest, EmbeddingResponse

router = APIRouter(prefix="/embeddings", tags=["embeddings"])

_DEFAULT_DIM = 256


def _hash_embedding(text: str, dim: int = _DEFAULT_DIM) -> list[float]:
    """Deterministic local embedding for development without external providers."""
    values = [0.0] * dim
    tokens = [tok for tok in text.lower().split() if tok]
    if not tokens:
        return values

    for token in tokens:
        digest = hashlib.sha256(token.encode("utf-8")).digest()
        for idx in range(dim):
            byte = digest[idx % len(digest)]
            values[idx] += (byte / 255.0) * 2.0 - 1.0

    scale = float(len(tokens))
    return [v / scale for v in values]


@router.post("", response_model=EmbeddingResponse)
def create_embedding(body: EmbeddingRequest) -> EmbeddingResponse:
    model = body.model or "local-hash-embedding-v1"
    vector = _hash_embedding(body.input)
    return EmbeddingResponse(
        data=[EmbeddingData(embedding=vector, index=0)],
        model=model,
    )
