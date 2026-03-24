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
import os, sys
# Cross-platform PATH setup
if sys.platform == "darwin":
    os.environ["PATH"] = "/opt/homebrew/bin:" + os.environ.get("HOME", "") + "/.bun/bin:" + os.environ.get("PATH", "")

import argparse, json, subprocess
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
CONVEX_QUERY_URL = "https://notable-dragon-607.convex.cloud/api/query"

CONTRADICTION_PROMPT = """New fact: "{new_fact}"

Existing facts in the same category:
{existing_facts}

Does the new fact DIRECTLY CONTRADICT an existing fact?

CONTRADICT = same subject, INCOMPATIBLE information (cannot both be true).
NOT a contradiction:
- Adding details or precision to an existing fact
- A newer version/update of a tool or process (evolution, not conflict)
- Complementary information about the same topic
- Different aspects of the same subject

If two facts say OPPOSITE things about the same subject's current state, that IS a contradiction.
When in doubt about whether it's an update vs a complement, answer null.

Reply ONLY with valid JSON:
{{"contradicts": <number 1-{count} or null>, "reason": "<short explanation>"}}"""


def _check_contradiction_local(fact: dict, cfg: dict, debug: bool = False) -> dict | None:
    """Check if a fact contradicts existing agentMemory facts using local LLM (0€).
    Returns {"contradicts_id": id, "contradicts_fact": text, "reason": str} or None."""
    try:
        # Search similar facts in Convex
        payload = json.dumps({
            "path": "agentMemory:search",
            "args": {"query": fact["fact"], "category": fact.get("category", "savoir"), "limit": 5}
        })
        result = subprocess.run(
            ["curl", "-s", "-X", "POST", CONVEX_QUERY_URL,
             "-H", "Content-Type: application/json", "-d", payload],
            capture_output=True, text=True, timeout=15
        )
        data = json.loads(result.stdout)
        candidates = data.get("value", [])
        if not candidates:
            return None

        # Build prompt
        existing = "\n".join(f'{i+1}. "{c["fact"]}"' for i, c in enumerate(candidates))
        prompt = CONTRADICTION_PROMPT.format(
            new_fact=fact["fact"], existing_facts=existing, count=len(candidates)
        )

        # Call local LLM
        check = call_llm_json(prompt, cfg, debug)
        if check and check.get("contradicts") is not None:
            idx = check["contradicts"]
            if isinstance(idx, int) and 1 <= idx <= len(candidates):
                contradicted = candidates[idx - 1]
                if debug:
                    print(f"  ⚠ Contradiction: {fact['fact'][:50]}", file=sys.stderr)
                    print(f"    vs: {contradicted['fact'][:50]}", file=sys.stderr)
                    print(f"    Reason: {check.get('reason', '?')}", file=sys.stderr)
                return {
                    "contradicts_id": contradicted.get("_id"),
                    "contradicts_fact": contradicted["fact"],
                    "reason": check.get("reason", "")
                }
    except Exception as e:
        if debug:
            print(f"  → Contradiction check error: {e}", file=sys.stderr)
    return None


def store_to_convex(facts: list[dict], agent: str = "koda", debug: bool = False,
                    check_contradictions: bool = True, cfg: dict = None) -> int:
    """Store facts to agentMemory (Convex). Runs local contradiction check (gemma3, 0€).
    Returns count stored."""
    stored = 0
    contradictions = 0
    skipped_facts = []

    if check_contradictions and cfg is None:
        cfg = load_config(script="extract")

    for f in facts:
        # Local contradiction check before storing
        if check_contradictions and cfg:
            conflict = _check_contradiction_local(f, cfg, debug)
            if conflict:
                contradictions += 1
                skipped_facts.append({"fact": f["fact"], "conflict": conflict})
                continue  # Don't store contradicting facts

        # Store via simple agentMemory:store (Convex dedup handles the rest)
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

    if contradictions > 0:
        if debug:
            print(f"  ⚠ {contradictions} contradictions blocked, {stored} stored", file=sys.stderr)
            for sf in skipped_facts:
                print(f"    Skipped: {sf['fact'][:50]} (vs {sf['conflict']['contradicts_fact'][:50]})", file=sys.stderr)
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
