"""Optional vector retrieval for wardrobe item recall (Pinecone/Azure AI Search)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import httpx

from app.config import settings


@dataclass(frozen=True)
class VectorHit:
    item_id: int
    score: float


class VectorRetriever:
    """Best-effort vector search wrapper; failures degrade to empty retrieval."""

    def retrieve_item_ids(self, query_text: str, top_k: int | None = None) -> list[int]:
        backend = (settings.vector_store_backend or "none").lower().strip()
        if backend == "none" or not query_text.strip():
            return []

        vector = self._embed_query(query_text)
        if not vector:
            return []

        limit = max(1, top_k or settings.vector_search_top_k)
        try:
            if backend == "pinecone":
                hits = self._query_pinecone(vector, limit)
            elif backend == "azure_ai_search":
                hits = self._query_azure_search(vector, limit)
            else:
                return []
        except Exception:
            return []

        seen: set[int] = set()
        ordered_ids: list[int] = []
        for hit in sorted(hits, key=lambda h: h.score, reverse=True):
            if hit.item_id in seen:
                continue
            seen.add(hit.item_id)
            ordered_ids.append(hit.item_id)
        return ordered_ids

    def _embed_query(self, query_text: str) -> list[float]:
        provider = (settings.vector_embedding_provider or "endpoint").lower().strip()
        if provider == "huggingface":
            return self._embed_query_huggingface(query_text)
        return self._embed_query_endpoint(query_text)

    def _embed_query_endpoint(self, query_text: str) -> list[float]:
        endpoint = settings.vector_embedding_endpoint
        if not endpoint:
            return []

        headers = {"Content-Type": "application/json"}
        if settings.vector_embedding_api_key:
            headers["Authorization"] = f"Bearer {settings.vector_embedding_api_key}"

        payload: dict[str, Any] = {"input": query_text}
        if settings.vector_embedding_model:
            payload["model"] = settings.vector_embedding_model

        try:
            response = httpx.post(endpoint, headers=headers, json=payload, timeout=8.0)
            response.raise_for_status()
            data = response.json()
        except Exception:
            return []

        # OpenAI-compatible shape.
        openai_data = data.get("data")
        if isinstance(openai_data, list) and openai_data:
            emb = openai_data[0].get("embedding")
            if isinstance(emb, list):
                return [float(v) for v in emb]

        # Generic shape.
        emb = data.get("embedding")
        if isinstance(emb, list):
            return [float(v) for v in emb]
        return []

    def _embed_query_huggingface(self, query_text: str) -> list[float]:
        model = settings.huggingface_embedding_model
        endpoint = settings.huggingface_embedding_endpoint
        if not endpoint:
            endpoint = f"https://api-inference.huggingface.co/models/{model}"

        headers = {"Content-Type": "application/json"}
        api_key = settings.huggingface_embedding_api_key
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"

        payload: dict[str, Any] = {"inputs": query_text}
        try:
            response = httpx.post(endpoint, headers=headers, json=payload, timeout=12.0)
            response.raise_for_status()
            data = response.json()
        except Exception:
            return []

        # Common HF response formats:
        # 1) [float, ...]
        # 2) [[float, ...], ...] (token-level embeddings)
        if isinstance(data, list) and data:
            if isinstance(data[0], (int, float)):
                return [float(v) for v in data]
            if isinstance(data[0], list):
                rows = [row for row in data if isinstance(row, list) and row]
                if not rows:
                    return []
                dim = len(rows[0])
                sums = [0.0] * dim
                count = 0
                for row in rows:
                    if len(row) != dim:
                        continue
                    try:
                        nums = [float(v) for v in row]
                    except (TypeError, ValueError):
                        continue
                    for idx, val in enumerate(nums):
                        sums[idx] += val
                    count += 1
                if count == 0:
                    return []
                return [v / count for v in sums]
        return []

    def _query_pinecone(self, vector: list[float], top_k: int) -> list[VectorHit]:
        host = settings.pinecone_index_host
        api_key = settings.pinecone_api_key
        if not host or not api_key:
            return []

        payload: dict[str, Any] = {
            "vector": vector,
            "topK": top_k,
            "includeMetadata": True,
        }
        if settings.pinecone_namespace:
            payload["namespace"] = settings.pinecone_namespace

        response = httpx.post(
            f"{host.rstrip('/')}/query",
            headers={"Api-Key": api_key, "Content-Type": "application/json"},
            json=payload,
            timeout=10.0,
        )
        response.raise_for_status()
        body = response.json()

        hits: list[VectorHit] = []
        for match in body.get("matches", []):
            metadata = match.get("metadata") or {}
            raw_item_id = metadata.get("item_id")
            if raw_item_id is None:
                continue
            try:
                item_id = int(raw_item_id)
            except (TypeError, ValueError):
                continue
            score = float(match.get("score", 0.0))
            hits.append(VectorHit(item_id=item_id, score=score))
        return hits

    def _query_azure_search(self, vector: list[float], top_k: int) -> list[VectorHit]:
        endpoint = settings.azure_search_endpoint
        api_key = settings.azure_search_api_key
        index_name = settings.azure_search_index_name
        if not endpoint or not api_key or not index_name:
            return []

        url = (
            f"{endpoint.rstrip('/')}/indexes/{index_name}/docs/search"
            "?api-version=2024-07-01"
        )
        payload = {
            "vectorQueries": [
                {
                    "kind": "vector",
                    "vector": vector,
                    "fields": settings.azure_search_vector_field,
                    "k": top_k,
                }
            ],
            "select": settings.azure_search_item_id_field,
            "top": top_k,
        }
        response = httpx.post(
            url,
            headers={"api-key": api_key, "Content-Type": "application/json"},
            json=payload,
            timeout=10.0,
        )
        response.raise_for_status()
        body = response.json()

        hits: list[VectorHit] = []
        field_name = settings.azure_search_item_id_field
        for doc in body.get("value", []):
            raw_item_id = doc.get(field_name)
            if raw_item_id is None:
                continue
            try:
                item_id = int(raw_item_id)
            except (TypeError, ValueError):
                continue
            score = float(doc.get("@search.score", 0.0))
            hits.append(VectorHit(item_id=item_id, score=score))
        return hits
