"""
Conspiracy Board Agent — CLI entry point.
Usage:
  python -m agent.main "Topic A" "Topic B" [--rounds N]   # CLI mode
  python -m agent.main --web [--port PORT]                 # Web UI mode
"""
import argparse
import os
from dotenv import load_dotenv

load_dotenv()

from agent.agent import run_agent


def main():
    parser = argparse.ArgumentParser(
        description="Conspiracy Board Agent — connect any two topics"
    )
    parser.add_argument("topic_a", type=str, nargs="?", default=None, help="First topic to investigate")
    parser.add_argument("topic_b", type=str, nargs="?", default=None, help="Second topic to investigate")
    parser.add_argument(
        "--rounds",
        type=int,
        default=3,
        help="Number of investigation rounds (default: 3)",
    )
    parser.add_argument(
        "--web",
        action="store_true",
        help="Launch web UI server instead of CLI mode",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=int(os.environ.get("PORT", "8000")),
        help="Port for web server (default: 8000, or PORT env var)",
    )
    args = parser.parse_args()

    if args.web:
        import uvicorn
        from agent.server import app
        print(f"Starting Conspiracy Board web UI at http://localhost:{args.port}")
        uvicorn.run(app, host="0.0.0.0", port=args.port)
        return

    if not args.topic_a or not args.topic_b:
        parser.error("topic_a and topic_b are required in CLI mode (or use --web for web UI)")

    print("=== CONSPIRACY BOARD AGENT ===")
    print(f"Investigating: {args.topic_a} <-> {args.topic_b}")
    print(f"Rounds: {args.rounds}")

    run_agent(args.topic_a, args.topic_b, rounds=args.rounds)


if __name__ == "__main__":
    main()
