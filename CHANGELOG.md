## v2.4.0 — Auto-Ingestion (2026-03-23)

### Added
- `auto_ingest.py` — Watch/scan workspace, extract facts → agentMemory + update embed cache
  - `--scan`: one-shot scan of recently modified files
  - `--watch`: continuous fswatch daemon
  - `--file path.md`: ingest single file
  - `--post-compaction "text"`: extract from LCM compaction output
- Content-hash dedup: skip files unchanged since last ingestion
- Cooldown: don't reprocess same file within 5 min
- State tracking in `.cache/ingest-state.json`
- Incremental embed cache updates for changed files

### Fixed
- extract_facts.py: missing `subprocess` import
- Config: extract override switched to gemma3:4b (non-thinking), maxTokens 2048
- Large files truncated to ~4000 chars to stay within model context

## v2.2.0 — Synthesis Fix + Qwen Thinking Support (2026-03-23)

### Fixed
- Synthesis now uses gemma3:4b (non-thinking model) — 2-8s vs 190s timeout with Qwen
- LLM client: extract content from `thinking` field (Ollama) and `reasoning_content` (LM Studio)
- Fallback plain-text synthesis when JSON still fails after retries
- Graph results capped at 20 with relevance threshold (was flooding 229+)

### Changed
- Default recall LLM override: gemma3:4b via Ollama (fast, reliable JSON)
- Config: scriptOverrides.recall for per-pipeline model selection

## v2.1.0 — Unified Recall Pipeline (2026-03-23)

### Added
- `unified_recall.py` — Fan-out 4 sources (Convex, embeddings, QMD, graph) → merge → 6-signal scoring → LLM rerank → synthesis
- Multi-signal scoring: semantic similarity, BM25, recency decay, access frequency, source trust, graph centrality
- Multi-source bonus: results found by 2+ sources get trust boost
- Graph result filtering and capping (max 20, min relevance 0.15)
- Fallback plain-text synthesis when JSON parsing fails
- 8 new unit tests for unified recall (merge, dedup, recency, scoring)

### Fixed
- LLM client: support `reasoning_content` field (Qwen 3.x via LM Studio)
- LLM client: support `thinking` field (Qwen 3.x via Ollama)
- Strip "Thinking Process:" preamble from Qwen responses

# Changelog

## v2.0.0 (2026-03-23)
### Major refactor — ClawHub skill format
- **New unified Python modules** replacing shell scripts:
  - `llm_client.py` — Unified LLM/embed client (LM Studio, Ollama, OpenAI)
  - `multihop_search.py` — Multi-hop reasoning search with `--embed` mode
  - `decay_search.py` — Temporal decay search
  - `extract_facts.py` — Fact extraction with `--store` (→ agentMemory/Convex)
  - `knowledge_graph.py` — Knowledge graph builder
  - `selftest.py` — Setup validation (servers, QMD, graph)
  - `tests.py` — 20 unit tests
- **Centralized config** (`config.json`) with presets and per-script model overrides
- **JSON retry** — `call_llm_json` retries once on parse failure
- **GPT-OSS tag stripping** — handles `<|channel|>` tags in responses
- **Graph scoring** — relevance-based file selection (not arbitrary limit)
- **SKILL.md** — ClawHub-compatible skill manifest
- **references/configuration.md** — Full setup guide

### Legacy scripts preserved
- `qmd-multihop`, `qmd-decay-query`, `build-knowledge-graph` — original shell/Python scripts
- `extract-facts.md` — prompt template

## v1.1.0 (2026-03-23)
- LM Studio compatibility (endpoints, PATH injection, thinking tags strip)

## v1.0.0 (2026-03-23)
- Initial release: multihop, decay, knowledge graph scripts
