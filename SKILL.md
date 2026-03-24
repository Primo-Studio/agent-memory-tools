---
name: agent-memory-tools
version: 2.6.0
description: Advanced memory search and knowledge management for AI agents. Provides unified recall (4-source fan-out + multi-signal scoring), multi-hop reasoning, temporal decay, knowledge graph with auto-rebuild, fact extraction with contradiction check + agentMemory storage, auto-ingestion, and feedback analytics. Cross-platform (macOS/Linux/Windows). Use when an agent needs to search workspace knowledge, find recent context, build entity graphs, extract facts, or auto-ingest file changes into memory.
---

# Agent Memory Tools v2.6.0

Workspace-level memory augmentation for AI agents. All tools run 100% local (Ollama, LM Studio) or via cloud API. Cross-platform (macOS/Linux/Windows).

## Architecture

```
File changed → auto_ingest (scan/watch/polling)
    ├─→ extract_facts → storeWithContradictionCheck → agentMemory (Convex)
    │                    ↓ fallback: store (simple)
    ├─→ update embed cache (nomic vectors)
    └─→ update_graph_incremental (knowledge graph)

Question → unified_recall → [agentMemory, embeddings, QMD/BM25, knowledge graph]
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

# Extract facts and store to agentMemory (with contradiction check)
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
Fan-out 4 sources in parallel, merge, 6-signal scoring, LLM rerank, synthesis with feedback loop.

```bash
python3 scripts/unified_recall.py "question" [--top 8] [--debug] [--json] [--preset ollama]
python3 scripts/unified_recall.py "question" --no-rerank   # Skip LLM reranking
python3 scripts/unified_recall.py "question" --no-llm      # Scoring only, no synthesis
python3 scripts/unified_recall.py --stats                   # Feedback analytics
python3 scripts/unified_recall.py --feedback                # Log results for analysis
```

**Sources:** agentMemory (Convex), vector embeddings (nomic), QMD/BM25, knowledge graph
**Scoring signals:** semantic similarity, BM25, recency decay, access frequency, source trust, graph centrality
**Multi-source bonus:** results found by 2+ sources get trust boost

### `auto_ingest.py` — Auto-ingestion pipeline (v2.4+)
Watch or scan workspace for .md changes → extract facts (with contradiction check) → store to agentMemory + update embed cache + auto-rebuild knowledge graph.

```bash
python3 scripts/auto_ingest.py --scan [--max-files 10] [--debug]     # One-shot scan
python3 scripts/auto_ingest.py --watch [--debug]                      # Daemon (fswatch macOS / polling elsewhere)
python3 scripts/auto_ingest.py --file path/to/doc.md [--debug]       # Single file
python3 scripts/auto_ingest.py --post-compaction "LCM summary" [--debug]  # From compaction
```

- Content-hash dedup: skip unchanged files
- Cooldown: don't reprocess same file within 5 min
- State tracking in `.cache/ingest-state.json`
- Incremental embed cache + knowledge graph updates
- Cross-platform: fswatch (macOS) / polling 30s fallback (Linux/Windows)

### `extract_facts.py` — Fact extraction + storage (v2.6: contradiction check)
Extract durable facts from text, store to agentMemory with automatic contradiction detection.

```bash
python3 scripts/extract_facts.py "text" [--file path.md] [--store] [--agent koda] [--json]
echo "text" | python3 scripts/extract_facts.py --store
```

- `--store` — Write to agentMemory via `storeWithContradictionCheck` (auto-fallback to simple `store` if endpoint unavailable)
- Contradictions are detected and logged, conflicting facts are not stored
- Categories: savoir, erreur, chronologie, preference, outil, client, rh

### `multihop_search.py` — Multi-hop reasoning search
Chains QMD + optional vector embedding searches with LLM synthesis.

```bash
python3 scripts/multihop_search.py "question" [--max-hops 4] [--embed] [--debug] [--json]
```

### `decay_search.py` — Temporal decay search
Recent facts score higher. Permanent knowledge (errors, rules) is protected from decay.

```bash
python3 scripts/decay_search.py "query" [--limit 10] [--half-life 14] [--json]
```

### `knowledge_graph.py` — Knowledge graph builder (v2.6: incremental)
Extract entities/relationships from workspace markdown into a JSON graph.

```bash
python3 scripts/knowledge_graph.py [--rebuild] [--dry-run] [--debug]
```

- `update_graph_incremental(changed_files)` — Partial update without full rebuild (called by auto_ingest)
- Full rebuild extracts from all workspace .md files
- Graph stored at `.cache/knowledge-graph.json`

### `selftest.py` — Setup validation

```bash
python3 scripts/selftest.py [--preset ollama]
```

### `tests.py` — Unit tests (28 tests)

```bash
python3 scripts/tests.py
```

## Configuration

All scripts share `scripts/config.json`. See `references/configuration.md` for full guide.

### Workspace auto-detect
1. `MEMORY_WORKSPACE` env var (if set)
2. Deduced from skill directory parent

### Per-script model override
```json
"scriptOverrides": {
  "recall": { "llm": { "baseUrl": "http://localhost:11434", "model": "gemma3:4b", "apiFormat": "ollama" } },
  "extract": { "llm": { "baseUrl": "http://localhost:11434", "model": "gemma3:4b", "apiFormat": "ollama" } },
  "multihop": { "llm": { "model": "qwen/qwen3.5-35b-a3b" } },
  "graph": { "llm": { "model": "gemma3:4b", "apiFormat": "ollama" } }
}
```

### Presets
```bash
python3 scripts/unified_recall.py "query" --preset ollama
```
Available: `ollama`, `ollama-big`, `lmstudio`, `openai`, `openrouter`

### Model recommendations

| RAM | LLM | Embed | Cost |
|-----|-----|-------|------|
| 4 GB | gemma3:1b | nomic-embed-text | $0 |
| **8 GB** | **gemma3:4b** ← recommended | nomic-embed-text-v2-moe | $0 |
| 16 GB | qwen3.5:27b | nomic-embed-text-v2-moe | $0 |
| 32+ GB | qwen3.5:35b (MLX) | nomic-embed-text-v2-moe | $0 |

**⚠ Avoid Qwen 3.5 for JSON tasks** — puts output in "thinking" field, wastes tokens.
**✅ gemma3:4b** — Best ratio quality/speed for structured output (~2s/call).

## Platform Setup

| Platform | Scan/Extract | Watch | Auto-trigger |
|----------|-------------|-------|--------------|
| macOS | ✅ | fswatch or polling | LaunchAgent WatchPaths |
| Linux | ✅ | polling 30s | systemd timer or cron |
| Windows | ✅ | polling 30s | Task Scheduler |

See `references/configuration.md` for platform-specific examples.

## Requirements

- Python 3.9+
- QMD CLI (`bun install -g qmd`) — for BM25 search
- Ollama or LM Studio — for local LLM + embeddings
- `curl` — for agentMemory (Convex) API calls
- Optional: `fswatch` (macOS, for --watch; polling fallback everywhere)

## Changelog

### v2.6.0 (2026-03-23)
- **Contradiction check** by default: `storeWithContradictionCheck` + auto-fallback
- **Knowledge graph auto-rebuild** on file changes in auto_ingest
- `update_graph_incremental()` for partial graph updates
- Contradictions logged with conflict source

### v2.5.0 (2026-03-23)
- Cross-platform: macOS/Linux/Windows (no hardcoded paths)
- Workspace auto-detect (`MEMORY_WORKSPACE` env or parent dir)
- 5 presets: ollama, ollama-big, lmstudio, openai, openrouter
- LLM recommendations by RAM and budget
- `references/configuration.md`: full setup guide

### v2.4.0 (2026-03-23)
- `auto_ingest.py`: scan/watch/file/post-compaction pipeline
- Content-hash dedup + cooldown + state tracking
- Incremental embed cache updates

### v2.2.0 (2026-03-23)
- Synthesis fixed: gemma3:4b (2-8s) vs Qwen 35B timeout
- LLM reranker + feedback loop (`--stats`, `--feedback`)

### v2.1.0 (2026-03-23)
- `unified_recall.py`: fan-out 4 sources, merge, 6-signal scoring

### v2.0.0 (2026-03-23)
- JSON retry + GPT-OSS tag stripping
- Config per-script (scriptOverrides)
- Graph scoring by relevance
- `extract_facts --store` → agentMemory
- Multihop `--embed` mode
- 20→28 unit tests
