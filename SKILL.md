---
name: agent-memory-tools
description: Advanced memory search and knowledge management for AI agents. Provides multi-hop reasoning search, temporal decay search, knowledge graph building, and fact extraction with direct agentMemory storage. Use when an agent needs to search workspace knowledge before coding, find recent context with temporal relevance, build entity relationship graphs from markdown, or extract and store durable facts from conversations.
---

# Agent Memory Tools

Workspace-level memory augmentation for AI agents. All tools run 100% local (LM Studio, Ollama) or via cloud API.

## Quick Start

```bash
# Verify setup
python3 scripts/selftest.py

# Search with multi-hop reasoning
python3 scripts/multihop_search.py "What workflow does Sol follow for tasks?"

# Search with recency bias
python3 scripts/decay_search.py "recent bugs"

# Extract facts and store to agentMemory
python3 scripts/extract_facts.py "Neto prefers step-by-step deploys." --store

# Build/update knowledge graph
python3 scripts/knowledge_graph.py

# Run tests
python3 scripts/tests.py
```

## Scripts

### `multihop_search.py` — Multi-hop reasoning search
Chains QMD + optional vector embedding searches with LLM synthesis. Finds complex answers across multiple files.

```bash
python3 scripts/multihop_search.py "question" [--max-hops 4] [--embed] [--debug] [--json] [--preset ollama]
```

- `--embed` — Also use vector embeddings for recall (recommended for French content)
- Best for: complex questions requiring cross-file reasoning

### `decay_search.py` — Temporal decay search
Recent facts score higher. Permanent knowledge (errors, rules) is protected from decay.

```bash
python3 scripts/decay_search.py "query" [--limit 10] [--half-life 14] [--json] [--preset ollama]
```

Best for: finding recent context ("latest bugs", "what changed today")

### `extract_facts.py` — Fact extraction + storage
Extract durable facts from text, optionally store directly to agentMemory (Convex).

```bash
python3 scripts/extract_facts.py "text" [--file path.md] [--store] [--agent koda] [--min-confidence 0.7] [--json]
echo "text" | python3 scripts/extract_facts.py --store
```

- `--store` — Write extracted facts to agentMemory (Convex) automatically
- `--agent` — Agent name for storage (default: koda)
- Best for: post-conversation fact capture, LCM summary processing

### `knowledge_graph.py` — Knowledge graph builder
Extract entities/relationships from workspace markdown into a JSON graph.

```bash
python3 scripts/knowledge_graph.py [--rebuild] [--dry-run] [--debug]
```

Best for: periodic workspace indexing (after major doc changes)

### `selftest.py` — Setup validation
Check config, servers, QMD, and graph in one command.

```bash
python3 scripts/selftest.py [--preset ollama]
```

### `tests.py` — Unit tests
20 tests covering JSON parsing, config loading, cosine similarity, graph enrichment.

```bash
python3 scripts/tests.py
```

## Configuration

All scripts share `scripts/config.json`. Edit once, applies everywhere.

### Per-script model override
Use `scriptOverrides` in config.json to assign different models per script:
```json
"scriptOverrides": {
  "multihop": { "llm": { "model": "qwen/qwen3.5-35b-a3b" } },
  "extract": { "llm": { "model": "openai/gpt-oss-20b" } }
}
```

### Presets
Use `--preset` on any script to switch providers:
```bash
python3 scripts/multihop_search.py "query" --preset ollama
```

Available presets: `ollama`, `openai`. See [references/configuration.md](references/configuration.md) for full setup.

## Requirements

- Python 3.9+
- QMD CLI with indexed collection (`bun install -g qmd`)
- Local LLM server (LM Studio or Ollama) OR OpenAI API key
- `curl` in PATH

## Agent Integration

Add to agent workflow (AGENTS.md):

```
Before coding → run multihop_search with task keywords
Before planning → run decay_search for recent context  
After significant work → run extract_facts --store to capture learnings
After major doc changes → run knowledge_graph to update graph
```
