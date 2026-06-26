"""Proveedor de búsqueda Tavily (httpx) con caché simple. Inyectable (falso en tests)."""

from __future__ import annotations

import httpx

from app.core.config import settings
from app.search.base import SearchResult


class TavilyProvider:
    def __init__(self, *, api_key: str | None = None, client: httpx.AsyncClient | None = None):
        self.api_key = api_key or settings.search_api_key or ""
        self._owns = client is None
        self._client = client or httpx.AsyncClient(timeout=30.0)
        self._cache: dict[str, list[SearchResult]] = {}

    async def aclose(self) -> None:
        if self._owns:
            await self._client.aclose()

    async def search(self, query: str, *, max_results: int = 5) -> list[SearchResult]:
        if query in self._cache:
            return self._cache[query]
        resp = await self._client.post(
            f"{settings.search_base_url.rstrip('/')}/search",
            json={"api_key": self.api_key, "query": query, "max_results": max_results},
        )
        data = resp.json()
        results = [
            SearchResult(
                title=r.get("title", ""),
                content=r.get("content", ""),
                url=r.get("url"),
                score=r.get("score"),
            )
            for r in data.get("results", [])
        ]
        self._cache[query] = results
        return results
