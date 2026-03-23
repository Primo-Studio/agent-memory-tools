#!/usr/bin/env python3
"""
extract_facts — Extract durable facts from text (LCM summaries, conversations, docs).
Outputs structured JSON for ingestion into agentMemory or similar stores.

Usage:
    extract_facts "text to extract from"
    echo "some text" | extract_facts
    extract_facts --file path/to/summary.md
"""
from __future__ import annotations
import os
os.environ["PATH"] = "/opt/homebrew/bin:" + os.environ.get("HOME", "") + "/.bun/bin:" + os.environ.get("PATH", "")

import argparse, json, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from llm_client import load_config, call_llm_json


EXTRACTION_PROMPT = """You are a fact extractor. You receive text from conversations or documents.

RULES:
- Extract ONLY durable facts (true tomorrow, not just today)
- Ignore one-time actions ("I ran the build", "I sent the message")
- Ignore conversation filler (greetings, confirmations)
- Each fact must be self-contained (understandable without context)
- Confidence: 0.0 to 1.0 (only return >= 0.5)
- Categories: savoir, erreur, chronologie, preference, outil, client, rh

TEXT:
{text}

Return JSON:
{{"facts": [
  {{"fact": "concise fact statement", "category": "category", "confidence": 0.8}},
  ...
]}}

Return empty facts array if nothing durable found: {{"facts": []}}"""


def extract(text: str, cfg: dict | None = None, debug: bool = False) -> list[dict]:
    """Extract facts from text."""
    if cfg is None:
        cfg = load_config()
    
    # Truncate to avoid overwhelming the LLM
    text = text[:4000]
    
    prompt = EXTRACTION_PROMPT.format(text=text)
    result = call_llm_json(prompt, cfg, debug)
    
    if result and "facts" in result:
        # Filter by confidence
        return [f for f in result["facts"] if f.get("confidence", 0) >= 0.5]
    
    return []


CONVEX_URL = "https://notable-dragon-607.convex.cloud/api/mutation"


def store_to_convex(facts: list[dict], agent: str = "koda", debug: bool = False) -> int:
    """Store facts to agentMemory (Convex). Returns count stored."""
    stored = 0
    for f in facts:
        payload = json.dumps({
            "path": "agentMemory:store",
            "args": {
                "fact": f["fact"],
                "category": f.get("category", "savoir"),
                "agent": agent,
                "confidence": f.get("confidence", 0.8),
                "source": "extract_facts"
            }
        })
        try:
            result = subprocess.run(
                ["curl", "-s", "-X", "POST", CONVEX_URL,
                 "-H", "Content-Type: application/json", "-d", payload],
                capture_output=True, text=True, timeout=15
            )
            data = json.loads(result.stdout)
            if data.get("status") == "success":
                stored += 1
                if debug:
                    action = data.get("value", {}).get("action", "?")
                    print(f"  → Stored ({action}): {f['fact'][:60]}", file=sys.stderr)
            elif debug:
                print(f"  → Failed: {result.stdout[:100]}", file=sys.stderr)
        except Exception as e:
            if debug:
                print(f"  → Error: {e}", file=sys.stderr)
    return stored


def main():
    parser = argparse.ArgumentParser(description="Extract durable facts from text")
    parser.add_argument("text", nargs="?", help="Text to extract from")
    parser.add_argument("--file", help="Read from file")
    parser.add_argument("--min-confidence", type=float, default=0.5)
    parser.add_argument("--debug", action="store_true")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--preset", help="Config preset")
    parser.add_argument("--store", action="store_true", help="Store facts to agentMemory (Convex)")
    parser.add_argument("--agent", default="koda", help="Agent name for agentMemory")
    args = parser.parse_args()
    
    cfg = load_config(preset=args.preset, script="extract")
    
    # Get input text
    if args.file:
        with open(args.file) as f:
            text = f.read()
    elif args.text:
        text = args.text
    elif not sys.stdin.isatty():
        text = sys.stdin.read()
    else:
        print("Error: provide text as argument, --file, or pipe stdin", file=sys.stderr)
        sys.exit(1)
    
    facts = extract(text, cfg, args.debug)
    facts = [f for f in facts if f.get("confidence", 0) >= args.min_confidence]
    
    if args.json:
        print(json.dumps({"facts": facts}, ensure_ascii=False, indent=2))
    else:
        if not facts:
            print("No durable facts found.")
        else:
            print(f"📋 {len(facts)} facts extracted:\n")
            for f in facts:
                cat = f.get("category", "?")
                conf = f.get("confidence", 0)
                print(f"  [{cat}] ({conf:.0%}) {f['fact']}")
    
    # Store to Convex if requested
    if args.store and facts:
        stored = store_to_convex(facts, agent=args.agent, debug=args.debug)
        print(f"\n💾 {stored}/{len(facts)} facts stored to agentMemory")


if __name__ == "__main__":
    main()
