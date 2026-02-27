# Conspiracy Board Agent

An autonomous AI agent that takes any two unrelated topics and builds an increasingly unhinged conspiracy board connecting them. It searches the internet, finds tenuous connections, analyzes "evidence" images, and constructs a live graph that deepens with each round — getting progressively more conspiratorial.

Built at the Autonomous Agents Hackathon (Feb 27, 2026) at AWS Builder Loft, San Francisco.

## How It Works

1. **Search** — Tavily searches the web for both topics and connections between them
2. **Extract** — GPT extracts entities and relationships from the search results
3. **Graph** — Neo4j stores the conspiracy graph of entities and connections
4. **Vision** — Reka Vision analyzes found images for "hidden clues"
5. **Remember** — Senso.ai stores findings so each round builds on the last
6. **Narrate** — The agent provides unhinged commentary as it connects the dots

Each round feeds into the next, making the conspiracy deeper and wilder.

## Sponsor Tools

| Tool | Purpose |
|------|---------|
| [Tavily](https://tavily.com) | Real-time web search |
| [Neo4j](https://neo4j.com) | Graph database for entities and relationships |
| [Reka](https://reka.ai) | Vision API for analyzing image "evidence" |
| [Senso.ai](https://senso.ai) | Knowledge base for accumulating findings |
| [Render](https://render.com) | Cloud deployment |

## Setup

```
pip install -r requirements.txt
cp .env.example .env  # fill in your API keys
```

Required API keys (see `.env.example`):
- `TAVILY_API_KEY`
- `NEO4J_URI`, `NEO4J_USERNAME`, `NEO4J_PASSWORD`
- `OPENAI_API_KEY`
- `REKA_API_KEY`
- `SENSO_API_KEY`

## Usage

**Web UI** (conspiracy board + graph visualization):

```
python -m agent.main --web
```

Open `http://localhost:8000`, enter two topics, and watch the board build itself.

**CLI mode:**

```
python -m agent.main "dolphins" "the pyramids" --rounds 3
```

## Architecture

```
agent/
  main.py       — CLI entry point (--web or --cli)
  agent.py      — Main agent loop (search → extract → graph → narrate)
  search.py     — Tavily web search
  extractor.py  — LLM entity/relationship extraction
  graph.py      — Neo4j graph operations
  vision.py     — Reka Vision image analysis
  senso.py      — Senso.ai knowledge base
  narrator.py   — Conspiratorial narration generator
  server.py     — FastAPI + WebSocket server
  static/       — Web UI (vis.js graph + cork board view)
```

## Deploy to Render

[![Deploy to Render](https://render.com/images/deploy-to-render-button.svg)](https://render.com/deploy)

A `render.yaml` blueprint is included. Set the env vars and deploy.
