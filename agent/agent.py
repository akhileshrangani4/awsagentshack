"""
Main agent loop for the Conspiracy Board Agent.

Orchestrates all modules: search -> extract -> graph -> store in Senso -> narrate.
Runs for a configurable number of rounds autonomously.
"""
from dotenv import load_dotenv

load_dotenv()

from agent.search import search_topic, search_connections
from agent.extractor import extract_entities_and_connections, get_deeper_search_queries
from agent.graph import ConspiracyGraph
from agent.senso import store_finding, query_findings
from agent.narrator import generate_narration
from agent.vision import analyze_image


def _emit(on_event, event_type: str, data: dict):
    """Send event to callback if provided, always print to terminal too."""
    if on_event:
        on_event({"type": event_type, **data})


def run_agent(topic_a: str, topic_b: str, rounds: int = 3, on_event=None) -> None:
    graph = ConspiracyGraph()
    graph.clear()

    last_insight: str = ""

    for round_num in range(1, rounds + 1):
        print(f"\n{'='*50}")
        print(f"  ROUND {round_num}/{rounds}")
        print(f"{'='*50}")

        _emit(on_event, "round_start", {"round": round_num, "total_rounds": rounds})

        # 1. Query Senso for previous findings
        print(f"\n[Senso] Querying previous findings...")
        previous_context = query_findings(topic_a, topic_b)
        if previous_context:
            print(f"  Found prior context ({len(previous_context)} chars)")
        else:
            print(f"  No prior findings")

        _emit(on_event, "senso_query", {
            "has_context": bool(previous_context),
            "context_length": len(previous_context) if previous_context else 0,
        })

        # 2. Search
        print(f"\n[Search] Searching Tavily for '{topic_a}' and '{topic_b}'...")
        round_images: list[str] = []
        if round_num == 1:
            connection_results, conn_images = search_connections(topic_a, topic_b)
            round_images.extend(conn_images)
        else:
            deeper_queries = get_deeper_search_queries(topic_a, topic_b, last_insight)
            print(f"  Deeper queries: {deeper_queries}")
            connection_results, conn_images = search_connections(topic_a, topic_b)
            round_images.extend(conn_images)
            for query in deeper_queries:
                extra_results, extra_images = search_topic(query, max_results=3)
                connection_results += extra_results
                round_images.extend(extra_images)

        topic_a_results, topic_a_images = search_topic(topic_a)
        topic_b_results, topic_b_images = search_topic(topic_b)
        round_images.extend(topic_a_images)
        round_images.extend(topic_b_images)

        all_results = topic_a_results + topic_b_results
        if previous_context:
            all_results.append({
                "title": "Previous Findings",
                "url": "",
                "content": previous_context,
            })
        all_results += connection_results
        print(f"  Collected {len(all_results)} search results")
        print(f"  Collected {len(round_images)} image URLs")

        _emit(on_event, "search_complete", {"result_count": len(all_results), "round": round_num})

        # 3. Extract entities and connections
        print(f"\n[Extract] Analyzing with LLM...")
        extracted = extract_entities_and_connections(topic_a, topic_b, all_results)
        print(f"  Entities: {len(extracted['entities_a'])} ({topic_a}) + {len(extracted['entities_b'])} ({topic_b})")
        print(f"  Connections: {len(extracted['connections'])}")
        print(f"  Insight: {extracted['insight']}")

        _emit(on_event, "extraction_complete", {
            "entities_a": extracted["entities_a"],
            "entities_b": extracted["entities_b"],
            "connections": extracted["connections"],
            "insight": extracted["insight"],
        })

        # 4. Store in Neo4j
        print(f"\n[Neo4j] Storing in graph...")
        for entity in extracted["entities_a"]:
            graph.add_entity(entity, topic_a, round_num)
        for entity in extracted["entities_b"]:
            graph.add_entity(entity, topic_b, round_num)
        for conn in extracted["connections"]:
            graph.add_connection(
                conn["from"],
                conn["to"],
                conn["relationship"],
                conn.get("suspicion_level", 5),
            )
        entity_count = graph.get_entity_count()
        print(f"  Total entities in graph: {entity_count}")

        _emit(on_event, "graph_update", {
            "entities": (
                [{"name": e, "topic": topic_a} for e in extracted["entities_a"]]
                + [{"name": e, "topic": topic_b} for e in extracted["entities_b"]]
            ),
            "connections": extracted["connections"],
            "entity_count": entity_count,
        })

        # 5. Store in Senso
        store_finding(topic_a, topic_b, round_num, extracted["insight"], extracted["connections"])

        # 5b. Analyze images with Reka Vision
        unique_images = list(dict.fromkeys(round_images))[:2]  # dedupe, max 2
        for image_url in unique_images:
            print(f"[Vision] Analyzing image: {image_url[:80]}...")
            clue = analyze_image(image_url, topic_a, topic_b)
            if clue:
                print(f"  Clue: {clue}")
                _emit(on_event, "image_clue", {
                    "image_url": image_url,
                    "clue_text": clue,
                    "round": round_num,
                })

        # 6. Narrate (streams to terminal)
        print(f"\n[Narrator] ", end="", flush=True)
        narration = generate_narration(
            round_num, topic_a, topic_b, extracted["insight"], entity_count
        )

        _emit(on_event, "narration", {"text": narration, "round": round_num})

        last_insight = extracted["insight"]

    total = graph.get_entity_count()
    conns = graph.get_connections()
    print(f"\n{'='*50}")
    print(f"  CONSPIRACY COMPLETE")
    print(f"{'='*50}")
    print(f"  Total entities: {total}")
    print(f"  Total connections: {len(conns)}")
    if conns:
        print(f"\n  Top connections:")
        for c in sorted(conns, key=lambda x: x.get("suspicion", 0), reverse=True)[:5]:
            print(f"    {c['from']} -> {c['to']}: {c['relationship'][:80]}")
    graph.close()

    _emit(on_event, "complete", {
        "total_entities": total,
        "total_connections": len(conns),
        "top_connections": [
            {
                "from": c["from"],
                "to": c["to"],
                "relationship": c["relationship"][:80],
            }
            for c in sorted(conns, key=lambda x: x.get("suspicion", 0), reverse=True)[:5]
        ],
    })
