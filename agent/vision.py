"""
Reka Vision image analyzer for the Conspiracy Board Agent.

Analyzes images found during research for conspiratorial "clues"
using the Reka multimodal API.
"""
import os
from dotenv import load_dotenv

load_dotenv()

_client = None
try:
    from reka.client import Reka
    from reka import ChatMessage
    _api_key = os.environ.get("REKA_API_KEY", "")
    if _api_key:
        _client = Reka(api_key=_api_key)
    else:
        print("[vision] Warning: REKA_API_KEY not set, vision analysis disabled")
except ImportError:
    print("[vision] Warning: reka package not installed, vision analysis disabled")
except Exception as e:
    print(f"[vision] Warning: Could not initialize Reka client: {e}")


def analyze_image(image_url: str, topic_a: str, topic_b: str) -> str:
    """
    Analyze an image URL using Reka Vision for conspiratorial clues.

    Args:
        image_url: Public URL of the image to analyze.
        topic_a: First investigation topic.
        topic_b: Second investigation topic.

    Returns:
        A short "clue" string describing what the agent found suspicious.
        Returns empty string if analysis fails or client unavailable.
    """
    if _client is None:
        return ""

    prompt = (
        f"You are a conspiracy theorist investigating connections between '{topic_a}' and '{topic_b}'. "
        f"Analyze this image for any suspicious details, hidden symbols, or connections to either topic. "
        f"Respond in EXACTLY 1-2 sentences as a paranoid conspiracy theorist. Be specific about what you see."
    )

    try:
        response = _client.chat.create(
            messages=[
                ChatMessage(
                    content=[
                        {"type": "image_url", "image_url": image_url},
                        {"type": "text", "text": prompt},
                    ],
                    role="user",
                )
            ],
            model="reka-core-20240501",
        )
        clue = response.responses[0].message.content.strip()
        return clue
    except Exception as e:
        print(f"[vision] Warning: Image analysis failed for {image_url}: {e}")
        return ""
