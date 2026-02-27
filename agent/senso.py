"""
Senso knowledge base integration for the Conspiracy Board Agent.

Uses the Senso Context OS API (apiv2) to search for relevant context.
Store operations are best-effort — the v2 API primarily exposes search.
Degrades gracefully when SENSO_API_KEY is not set.
"""
import os
import requests
from dotenv import load_dotenv

load_dotenv()

_BASE_URL = "https://apiv2.senso.ai/api/v1/org"


def _get_api_key() -> str | None:
    """Return API key from env, or None."""
    return os.environ.get("SENSO_API_KEY") or None


def _headers(api_key: str) -> dict:
    return {"X-API-Key": api_key, "Content-Type": "application/json"}


def store_finding(
    topic_a: str,
    topic_b: str,
    round_num: int,
    insight: str,
    connections: list[dict],
) -> None:
    """
    Store a round's findings. Currently a no-op on apiv2 (no ingest endpoint).
    Findings are persisted in Neo4j instead.
    """
    # apiv2 doesn't expose a content ingest endpoint.
    # Findings are stored in Neo4j graph; Senso is used for search/retrieval only.
    pass


def query_findings(topic_a: str, topic_b: str) -> str:
    """
    Query the Senso knowledge base for context about the two topics via POST /org/search.

    Returns the answer string (up to 500 chars), or empty string.
    """
    api_key = _get_api_key()
    if not api_key:
        return ""

    payload = {
        "query": f"connections between {topic_a} and {topic_b}",
        "max_results": 3,
    }

    try:
        response = requests.post(
            f"{_BASE_URL}/search",
            headers=_headers(api_key),
            json=payload,
            timeout=10,
        )
        response.raise_for_status()
        data = response.json()
        answer = data.get("answer", "")
        if answer and answer != "No results found for your query.":
            return answer[:500]
        # Fallback to concatenating result chunks
        results = data.get("results", [])
        combined = " ".join(r.get("chunk_text", "") for r in results if r.get("chunk_text"))
        return combined[:500]
    except Exception as e:
        print(f"[senso] Warning: query failed: {e}")
        return ""
