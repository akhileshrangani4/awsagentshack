"""
Neo4j graph operations for the Conspiracy Board Agent.

Stores entities and CONNECTED_TO relationships representing the conspiracy graph.
Degrades gracefully when Neo4j is unavailable so the agent can run without it.
"""
import os
from dotenv import load_dotenv

load_dotenv()

try:
    from neo4j import GraphDatabase
    from neo4j.exceptions import ServiceUnavailable
except ImportError:
    GraphDatabase = None  # type: ignore
    ServiceUnavailable = Exception  # type: ignore


class ConspiracyGraph:
    """Neo4j-backed graph of conspiracy entities and connections."""

    def __init__(self) -> None:
        self.available = False
        self._driver = None

        if GraphDatabase is None:
            print("[graph] Warning: neo4j package not installed — graph unavailable")
            return

        uri = os.environ.get("NEO4J_URI", "bolt://localhost:7687")
        user = os.environ.get("NEO4J_USERNAME", "neo4j")
        password = os.environ.get("NEO4J_PASSWORD", "")

        try:
            self._driver = GraphDatabase.driver(uri, auth=(user, password))
            # Verify connectivity
            self._driver.verify_connectivity()
            self.available = True
        except ServiceUnavailable as e:
            print(f"[graph] Warning: Neo4j not reachable at {uri}: {e}")
            self._driver = None
        except Exception as e:
            print(f"[graph] Warning: Could not connect to Neo4j: {e}")
            self._driver = None

    def close(self) -> None:
        """Close the Neo4j driver connection."""
        if self._driver is not None:
            self._driver.close()
            self._driver = None

    def clear(self) -> None:
        """Delete all nodes and relationships (fresh run)."""
        if not self.available or self._driver is None:
            return
        with self._driver.session() as session:
            session.run("MATCH (n) DETACH DELETE n")

    def add_entity(self, name: str, topic: str, round_num: int = 1) -> None:
        """
        Upsert an Entity node.

        Args:
            name: Entity name (used as unique key).
            topic: Which input topic this entity belongs to.
            round_num: Agent loop round when entity was discovered.
        """
        if not self.available or self._driver is None:
            return
        with self._driver.session() as session:
            session.run(
                "MERGE (e:Entity {name: $name}) "
                "SET e.topic = $topic, e.round = $round",
                name=name,
                topic=topic,
                round=round_num,
            )

    def add_connection(
        self,
        from_entity: str,
        to_entity: str,
        relationship: str,
        suspicion: int = 5,
    ) -> None:
        """
        Upsert a CONNECTED_TO relationship between two entity nodes.

        Args:
            from_entity: Source entity name.
            to_entity: Target entity name.
            relationship: One-sentence description of the connection.
            suspicion: Suspicion level 1-10.
        """
        if not self.available or self._driver is None:
            return
        with self._driver.session() as session:
            session.run(
                "MERGE (a:Entity {name: $from_name}) "
                "MERGE (b:Entity {name: $to_name}) "
                "MERGE (a)-[r:CONNECTED_TO]->(b) "
                "SET r.relationship = $rel, r.suspicion = $suspicion",
                from_name=from_entity,
                to_name=to_entity,
                rel=relationship,
                suspicion=suspicion,
            )

    def get_all_entities(self) -> list[dict]:
        """Return all Entity nodes as a list of dicts."""
        if not self.available or self._driver is None:
            return []
        with self._driver.session() as session:
            result = session.run("MATCH (e:Entity) RETURN properties(e) AS props")
            return [record["props"] for record in result]

    def get_connections(self) -> list[dict]:
        """Return all CONNECTED_TO relationships with from/to names."""
        if not self.available or self._driver is None:
            return []
        with self._driver.session() as session:
            result = session.run(
                "MATCH (a:Entity)-[r:CONNECTED_TO]->(b:Entity) "
                "RETURN a.name AS from_name, b.name AS to_name, "
                "r.relationship AS relationship, r.suspicion AS suspicion"
            )
            return [
                {
                    "from": record["from_name"],
                    "to": record["to_name"],
                    "relationship": record["relationship"],
                    "suspicion": record["suspicion"],
                }
                for record in result
            ]

    def get_entity_count(self) -> int:
        """Return the total number of Entity nodes."""
        if not self.available or self._driver is None:
            return 0
        with self._driver.session() as session:
            result = session.run("MATCH (e:Entity) RETURN count(e) AS cnt")
            record = result.single()
            return record["cnt"] if record else 0
