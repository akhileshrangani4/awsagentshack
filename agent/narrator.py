"""
Round-aware narration generator for the Conspiracy Board Agent.

Produces progressively more unhinged narration as rounds advance,
using OpenAI gpt-5.2 with round-specific system prompts.
"""
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

_client = OpenAI()

_SYSTEM_PROMPTS = {
    1: "You ARE the conspiracy theorist. You just stumbled onto something BIG. Talk like a paranoid late-night radio host whispering into the mic. Use phrases like 'follow the money', 'they don't want you to see this', 'open your eyes'. Respond in EXACTLY 2-3 sentences. First person. You're narrating YOUR investigation.",
    2: "You ARE a deep-state-obsessed conspiracy theorist who is SEEING THE PATTERN. You're pacing your apartment, pinning strings to your cork board, muttering to yourself. Use dramatic pauses (ellipses), rhetorical questions, and phrases like 'coincidence? I THINK NOT' and 'the rabbit hole goes deeper'. Respond in EXACTLY 2-3 sentences. First person, increasingly paranoid.",
    3: "You ARE a FULLY UNHINGED conspiracy theorist who has CRACKED THE CODE. You're recording a frantic voice memo at 3am. Use ALL CAPS for key revelations, reference shadow cabals and hidden agendas, insist NOTHING is a coincidence and EVERYTHING is connected. Be wildly entertaining. Respond in EXACTLY 2-3 sentences. First person, peak unhinged energy.",
}

_FALLBACKS = {
    1: "Interesting...",
    2: "THIS IS NOT A COINCIDENCE.",
    3: "THEY DON'T WANT YOU TO KNOW THIS.",
}


def generate_narration(
    round_num: int,
    topic_a: str,
    topic_b: str,
    insight: str,
    connection_count: int,
) -> str:
    """
    Generate round-appropriate narration about a finding.

    Args:
        round_num: Agent loop round (1, 2, or 3+).
        topic_a: First topic being investigated.
        topic_b: Second topic being investigated.
        insight: One-sentence insight from extraction.
        connection_count: Total entity count in the graph so far.

    Returns:
        Narration string. Falls back to a canned string on any error.
    """
    system_prompt = _SYSTEM_PROMPTS.get(round_num, _SYSTEM_PROMPTS[3])
    fallback = _FALLBACKS.get(round_num, _FALLBACKS[3])

    user_prompt = (
        f"React to this finding about {topic_a} and {topic_b}: "
        f"'{insight}'. {connection_count} connections found so far."
    )

    try:
        stream = _client.chat.completions.create(
            model="gpt-5.2",
            max_completion_tokens=1024,
            stream=True,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        )
        chunks = []
        for chunk in stream:
            delta = chunk.choices[0].delta if chunk.choices else None
            if delta and delta.content:
                print(delta.content, end="", flush=True)
                chunks.append(delta.content)
        print()  # newline after stream
        return "".join(chunks).strip()
    except Exception as e:
        print(f"[narrator] Warning: narration failed: {e}")
        return fallback
