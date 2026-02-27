"""
LLM-based entity and connection extractor for the Conspiracy Board Agent.

Uses the OpenAI API (gpt-5.2) to extract entities and suspicious
connections from raw search result text.
"""
import json
import re
import os
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

_client = OpenAI()


def extract_entities_and_connections(
    topic_a: str, topic_b: str, search_results: list[dict]
) -> dict:
    """
    Extract entities and connections from search results using an LLM.

    Args:
        topic_a: First topic being researched.
        topic_b: Second topic being researched.
        search_results: list of dicts with keys title, url, content.

    Returns:
        dict with keys:
            entities_a  - list of entity names related to topic_a
            entities_b  - list of entity names related to topic_b
            connections - list of {from, to, relationship, suspicion_level} dicts
            insight     - one-sentence summary of the most suspicious connection
    """
    fallback = {
        "entities_a": [],
        "entities_b": [],
        "connections": [],
        "insight": "No connections found yet...",
    }

    # Build text blob, capped at 3000 chars
    raw_text = "\n".join(r.get("content", "") for r in search_results)
    if len(raw_text) > 3000:
        raw_text = raw_text[:3000]

    if not raw_text.strip():
        return fallback

    user_prompt = (
        f"Topics: '{topic_a}' and '{topic_b}'.\n\n"
        f"Text:\n{raw_text}\n\n"
        "Extract entities and suspicious connections. "
        "Return ONLY valid JSON in this exact structure:\n"
        "{\n"
        '  "entities_a": ["entity1", "entity2"],\n'
        '  "entities_b": ["entity1", "entity2"],\n'
        '  "connections": [\n'
        '    {"from": "entity_name", "to": "entity_name", "relationship": "one sentence", "suspicion_level": 7}\n'
        "  ],\n"
        '  "insight": "one sentence summary of the most suspicious connection found"\n'
        "}"
    )

    try:
        response = _client.chat.completions.create(
            model="gpt-5.2",
            max_completion_tokens=4096,
            messages=[
                {"role": "system", "content": "You are a conspiracy theorist AI. Extract entities and find suspicious connections."},
                {"role": "user", "content": user_prompt},
            ],
        )
        raw_response = response.choices[0].message.content.strip()

        # Strip markdown code fences if present
        raw_response = re.sub(r"^```(?:json)?\s*", "", raw_response)
        raw_response = re.sub(r"\s*```$", "", raw_response)

        parsed = json.loads(raw_response)

        # Validate required keys are present, fill missing ones with defaults
        return {
            "entities_a": parsed.get("entities_a", []),
            "entities_b": parsed.get("entities_b", []),
            "connections": parsed.get("connections", []),
            "insight": parsed.get("insight", fallback["insight"]),
        }
    except Exception as e:
        print(f"[extractor] Warning: extraction failed: {e}")
        return fallback


def get_deeper_search_queries(
    topic_a: str, topic_b: str, previous_insight: str
) -> list[str]:
    """
    Generate follow-up search queries based on a previous insight.

    Args:
        topic_a: First topic.
        topic_b: Second topic.
        previous_insight: One-sentence insight from a previous extraction round.

    Returns:
        list of 3 specific search query strings.
    """
    fallback_queries = [
        f"{topic_a} secret connections",
        f"{topic_b} hidden links",
        f"{topic_a} {topic_b} conspiracy",
    ]

    try:
        user_prompt = (
            f"Topics: '{topic_a}' and '{topic_b}'.\n"
            f"Previous insight: {previous_insight}\n\n"
            "Give me exactly 3 specific web search queries to dig deeper into the "
            "suspicious connections between these topics. "
            "Return ONLY a JSON array of 3 strings, nothing else."
        )
        response = _client.chat.completions.create(
            model="gpt-5.2",
            max_completion_tokens=1024,
            messages=[
                {"role": "system", "content": "You are a conspiracy theorist AI. Find suspicious connections."},
                {"role": "user", "content": user_prompt},
            ],
        )
        raw_response = response.choices[0].message.content.strip()

        # Strip markdown code fences if present
        raw_response = re.sub(r"^```(?:json)?\s*", "", raw_response)
        raw_response = re.sub(r"\s*```$", "", raw_response)

        queries = json.loads(raw_response)
        if isinstance(queries, list) and len(queries) >= 1:
            return [str(q) for q in queries[:3]]
        return fallback_queries
    except Exception as e:
        print(f"[extractor] Warning: query generation failed: {e}")
        return fallback_queries
