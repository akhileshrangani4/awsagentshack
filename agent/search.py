"""
Tavily search wrapper for the Conspiracy Board Agent.
"""
import os
from dotenv import load_dotenv

load_dotenv()

try:
    from tavily import TavilyClient
    _client = TavilyClient(api_key=os.environ.get("TAVILY_API_KEY", ""))
except Exception as e:
    print(f"[search] Warning: Could not initialize Tavily client: {e}")
    _client = None


def _truncate(text: str, max_len: int = 500) -> str:
    if not text:
        return ""
    return text[:max_len] if len(text) > max_len else text


def search_topic(topic: str, max_results: int = 5) -> tuple[list[dict], list[str]]:
    """Search for a topic and return structured results plus image URLs."""
    if _client is None:
        print(f"[search] Warning: Tavily client not available, returning empty results for '{topic}'")
        return [], []
    try:
        response = _client.search(
            query=topic,
            search_depth="advanced",
            max_results=max_results,
            include_images=True,
        )
        results = response.get("results", []) if isinstance(response, dict) else []
        images = response.get("images", []) if isinstance(response, dict) else []
        return [
            {
                "title": r.get("title", ""),
                "url": r.get("url", ""),
                "content": _truncate(r.get("content", "")),
            }
            for r in results
        ], images[:3]  # cap at 3 image URLs per search
    except Exception as e:
        print(f"[search] Warning: Search failed for '{topic}': {e}")
        return [], []


def search_connections(topic_a: str, topic_b: str) -> tuple[list[dict], list[str]]:
    """Search for connections between two topics."""
    query = f"{topic_a} {topic_b} connection relationship"
    return search_topic(query, max_results=3)
