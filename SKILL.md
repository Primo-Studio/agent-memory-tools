---
name: agent-memory-tools
version: 2.4.0
description: Advanced memory search and knowledge management for AI agents. Provides unified recall (4-source fan-out + multi-signal scoring), multi-hop reasoning, temporal decay, knowledge graph, fact extraction with agentMemory storage, auto-ingestion, and feedback analytics. Use when an agent needs to search workspace knowledge, find recent context, build entity graphs, extract facts, or auto-ingest file changes into memory.
---

# Agent Memory Tools v2.4.0

Workspace-level memory augmentation for AI agents. All tools run 100% local (Ollama, LM Studio) or via cloud API.

## Architecture

```
Question → [agentMemory, embeddings, QMD/BM25, knowledge graph]
         → merge/dedup → 6-signal scoring → LLM rerank → synthesis → answer
                                                    ↓
                                              feedback log
```

## Quick Start

```bash
# Verify setup
python3 scripts/selftest.py

# Unified recall (recommended — uses all 4 sources)
python3 scripts/unified_recall.py "What bugs did Sol have?" --debug

# Multi-hop reasoning search
python3 scripts/multihop_search.py "What workflow does Sol follow?"

# Temporal decay search
python3 scripts/decay_search.py "recent bugs"

# Extract facts and store to agentMemory
python3 scripts/extract_facts.py "Some text" --store

# Auto-ingest: scan workspace for new/modified files
python3 scripts/auto_ingest.py --scan --debug

# Auto-ingest: watch for changes (daemon)
python3 scripts/auto_ingest.py --watch --debug

# Feedback analytics
python3 scripts/unified_recall.py --stats

# Build/update knowledge graph
python3 scripts/knowledge_graph.py

# Run tests
python3 scripts/tests.py
```

## Scripts

### `unified_recall.py` — Unified recall pipeline (v2.1+)
Fan-out 4 sources in parallel, merge, 6-signal scoring, LLM rerank, synthesis.

```bash
python3 scripts/unified_recall.py "question" [--top 8] [--debug] [--json] [--preset ollama]
python3 scripts/unified_recall.py "question" --no-rerank   # Skip LLM reranking
python3 scripts/unified_recall.py "question" --no-llm      # Scoring only, no synthesis
python3 scripts/unified_recall.py --stats                   # Feedback analytics
```

**Sources:** agentMemory (Convex), vector embeddings (nomic), QMD/BM25, knowledge graph
**Scoring signals:** semantic similarity, BM25, recency decay, access frequency, source trust, graph centrality
**Multi-source bonus:** results found by 2+ sources get trust boost

Best for: any recall question — this is the primary entry point.

### `auto_ingest.py` — Auto-ingestion pipeline (v2.4)
Watch or scan workspace for .md changes → extract facts → store to agentMemory + update embed cache.

```bash
python3 scripts/auto_ingest.py --scan [--max-files 10] [--debug]     # One-shot scan
python3 scripts/auto_ingest.py --watch [--debug]                      # fswatch daemon
python3 scripts/auto_ingest.py --file path/to/doc.md [--debug]       # Single file
python3 scripts/auto_ingest.py --post-compaction "LCM summary" [--debug]  # From compaction
```

- Content-hash dedup: skip unchanged files
- Cooldown: don't reprocess same file within 5 min
- State tracking in `.cache/ingest-state.json`
- Incremental embed cache updates

Best for: continuous memory building, post-compaction fact capture.

### `multihop_search.py` — Multi-hop reasoning search
Chains QMD + optional vector embedding searches with LLM synthesis.

```bash
python3 scripts/multihop_search.py "question" [--max-hops 4] [--embed] [--debug] [--json]
```

- `--embed` — Also use vector embeddings (recommended for French content)
- Best for: complex questions requiring cross-file reasoning

### `decay_search.py` — Temporal decay search
Recent facts score higher. Permanent knowledge (errors, rules) is protected from decay.

```bash
python3 scripts/decay_search.py "query" [--limit 10] [--half-life 14] [--json]
```

Best for: "what changed today", "latest bugs", recent context.

### `extract_facts.py` — Fact extraction + storage
Extract durable facts from text, optionally store to agentMemory (Convex).

```bash
python3 scripts/extract_facts.py "text" [--file path.md] [--store] [--agent koda] [--json]
echo "text" | python3 scripts/extract_facts.py --store
```

- `--store` — Write extracted facts to agentMemory (Convex) automatically
- Best for: post-conversation fact capture, LCM summary processing

### `knowledge_graph.py` — Knowledge graph builder
Extract entities/relationships from workspace markdown into a JSON graph.

```bash
python3 scripts/knowledge_graph.py [--rebuild] [--dry-run] [--debug]
```

### `selftest.py` — Setup validation

```bash
python3 scripts/selftest.py [--preset ollama]
```

### `tests.py` — Unit tests (28 tests)

```bash
python3 scripts/tests.py
```

## Configuration

All scripts share `scripts/config.json`.

### Per-script model override
```json
"scriptOverrides": {
  "recall": { "llm": { "baseUrl": "http://localhost:11434", "model": "gemma3:4b", "apiFormat": "ollama" } },
  "extract": { "llm": { "baseUrl": "http://localhost:11434", "model": "gemma3:4b", "apiFormat": "ollama" } },
  "multihop": { "llm": { "model": "qwen/qwen3.5-35b-a3b" } }
}
```

### Presets
```bash
python3 scripts/unified_recall.py "query" --preset ollama
```
Available presets: `ollama`, `openai`.

### Model recommendations
| Task | Recommended | Why |
|------|-------------|-----|
| Synthesis/rerank | gemma3:4b | Fast JSON, no thinking overhead |
| Extraction | gemma3:4b | Reliable structured output |
| Multihop reasoning | qwen3.5:27b+ | Better at complex reasoning |
| Embeddings | nomic-embed-text-v2-moe | Best local embed for FR (90.3% accuracy) |

**Avoid Qwen 3.5 for JSON tasks** — puts output in "thinking" field, wastes tokens, no JSON produced.

## Requirements

- Python 3.9+
- QMD CLI (`bun install -g qmd`)
- Ollama or LM Studio (local LLM)
- `curl`, `fswatch` (for --watch mode)

## Changelog

### v2.4.0 (2026-03-23)
- `auto_ingest.py`: scan/watch/file/post-compaction pipeline
- Content-hash dedup + cooldown + state tracking
- Incremental embed cache updates

### v2.2.0 (2026-03-23)
- Synthesis fixed: gemma3:4b (2-8s) vs Qwen 35B (190s timeout)
- LLM reranker with gemma3 for result ordering
- Feedback loop: query logging + `--stats` analytics

### v2.1.0 (2026-03-23)
- `unified_recall.py`: fan-out 4 sources, merge, 6-signal scoring

### v2.0.0 (2026-03-23)
- JSON retry + GPT-OSS tag stripping
- Config per-script (scriptOverrides)
- Graph scoring by relevance
- `extract_facts --store` → agentMemory
- Multihop `--embed` mode
- 20→28 unit tests
