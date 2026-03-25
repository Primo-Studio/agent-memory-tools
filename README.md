# 🧠 Agent Memory Tools
> **⚠️ This project has been superseded by [Memoria](https://github.com/Primo-Studio/openclaw-memoria)** — a native OpenClaw plugin with multi-layer memory (SQLite + FTS5 + embeddings + knowledge graph + topics + adaptive budget). If you're using OpenClaw, switch to Memoria for a fully integrated experience.
>
> This repository remains available as a reference for the Python-based retrieval pipeline and benchmarks.

---


Multi-source persistent memory for AI agents. **92% retrieval accuracy on LongMemEval-S** — matching commercial solutions, running 100% local at zero cost.

Compatible with **Ollama**, **LM Studio**, and any **OpenAI-compatible API** (OpenRouter, GPT-4o, Claude...). Optional **Convex** backend for cloud sync, shared memory between agents, contradiction detection, and real-time fact tracking.

## How it works

```
Question
  │
  ▼
unified_recall.py ──── fan-out (parallel) ────┐
  │                                            │
  ├─→ Fact store     (extracted facts, dedup)  │
  ├─→ Embeddings     (semantic search, nomic)  │
  ├─→ BM25           (keyword match, QMD)      │
  └─→ Knowledge graph (entity traversal)       │
                                               ▼
                                         Merge + Dedup
                                               │
                                         Multi-signal Score
                                         (relevance × recency × source weight)
                                               │
                                         LLM Rerank (gemma3)
                                               │
                                         Synthesize answer
                                         with source citations
```

Each layer adds a different recall strength — embeddings catch semantic similarity, BM25 catches exact terms, the graph catches relationships, and the fact store catches previously validated knowledge. Together they cover blind spots that any single method would miss.

## Quick start

```bash
# 1. Install
bash setup.sh

# 2. Search your workspace
python3 scripts/unified_recall.py "What happened last week?"

# 3. Extract facts from text
python3 scripts/extract_facts.py "Meeting notes..." --store

# 4. Auto-ingest file changes
python3 scripts/auto_ingest.py --scan
```

**Requirements:** Python 3.9+, Ollama, ~2GB disk (for models).

## Why Agent Memory Tools?

- **92% retrieval on LongMemEval-S** — proven on industry-standard benchmark, not toy data
- **Runs anywhere** — Ollama (free), LM Studio (free), or any OpenAI-compatible API
- **Works with small models** — tested with GPT-OSS 20B, gemma3:4b, Qwen 35B. No GPT-4o required for retrieval
- **Optional Convex backend** — shared memory between agents, real-time sync, contradiction detection, access tracking. Or just use local JSON (default, zero setup)
- **Zero cost** — local embeddings (nomic), local LLM, no API keys needed

## Key features

- **Multi-hop reasoning** — chains searches with LLM synthesis for complex questions
- **Contradiction detection** — blocks facts that contradict existing knowledge (local LLM, 0€)
- **Temporal decay** — recent facts score higher, errors/knowledge protected from decay
- **Auto-ingestion** — watch workspace for .md changes, extract + store automatically
- **Knowledge graph** — entity/relationship graph built from workspace files
- **Cross-platform** — macOS, Linux, Windows (polling watcher)
- **Flexible storage** — local JSON (default) or Convex cloud (shared memory, sync, tracking)
- **Model presets** — Ollama, LM Studio, OpenAI, OpenRouter — switch with `--preset`

## As an OpenClaw Skill

```bash
clawhub install agent-memory-tools
```

See [SKILL.md](SKILL.md) for agent integration details.

**Compatible with OpenClaw 2026.3.23+** — uses `openclaw/plugin-sdk/core` API.

### OpenClaw Plugin (auto-recall/capture)

We also maintain a companion OpenClaw plugin (`memory-convex`) that hooks into the gateway for automatic memory injection:
- **before_prompt_build** → searches facts and injects them before each message
- **agent_end** → extracts and stores new facts after each response
- Temporal scoring, boot audit, .md sync

This plugin is designed for local use (`~/.openclaw/extensions/memory-convex/`). See [openclaw-memory-convex](https://github.com/Hello-Primo/openclaw-memory-convex) for the source.

## Configuration

See [references/configuration.md](references/configuration.md) for the full guide, including:
- Model recommendations by RAM (4GB → 32GB+)
- Per-script model overrides
- Platform auto-trigger setup (LaunchAgent, systemd, Task Scheduler)
- Convex cloud backend setup

## Benchmarks

### LongMemEval-S (industry standard)

Tested on [LongMemEval-S](https://github.com/xiaowu0162/LongMemEval) — 500 questions across 6 categories (knowledge updates, multi-session reasoning, temporal reasoning, user preferences...).

**Retrieval accuracy: 92%** — on par with commercial solutions.

| Setup | Retrieval | Answer Score | Model | Cost |
|-------|-----------|-------------|-------|------|
| **Agent Memory Tools** (local) | **92%** | 25%* | GPT-OSS 20B (LM Studio) | **$0** |
| ByteRover (cloud) | 92-96% | 92-96% | GPT-4o | $$$ |
| Honcho (cloud) | — | 88% | GPT-4o | $$$ |

\* Answer score limited by the local 20B model, not by retrieval quality. The same retrieval pipeline with a stronger answering model (GPT-4o, Claude) would score significantly higher.

**Key takeaway:** Our retrieval matches ByteRover at 92% — using only local embeddings (nomic) at zero cost. The answer quality gap comes from the answering LLM, not from the memory system itself.

**Run it yourself:**
```bash
# Download dataset
wget https://raw.githubusercontent.com/xiaowu0162/LongMemEval/main/data/longmemeval_s.json

# Run benchmark (uses config.json model settings)
python3 scripts/benchmark.py --verbose
```

### Internal benchmark

10-question recall on synthetic workspace:

| Metric | Score |
|--------|-------|
| Precision | 96.7% |
| Questions OK | 10/10 |
| Backend | Local JSON |

## Tests

```bash
python3 scripts/tests.py    # 28 unit tests
```

## Compatibility

| Platform | Status |
|----------|--------|
| OpenClaw 2026.3.23+ | ✅ Tested |
| OpenClaw 2026.3.13–2026.3.22 | ✅ Compatible |
| Ollama | ✅ Tested (nomic-embed-text-v2-moe, gemma3:4b) |
| LM Studio | ✅ Tested (GPT-OSS 20B, Qwen 35B) |
| OpenAI API | ✅ Compatible |
| OpenRouter | ✅ Compatible |
| Python | 3.9+ |
| OS | macOS, Linux, Windows |

## Related

- **[memory-convex](https://github.com/Hello-Primo/openclaw-memory-convex)** — OpenClaw gateway plugin for auto-recall/capture via Convex
- **[ClawHub](https://clawhub.ai/primo-studio/agent-memory-tools)** — Install as OpenClaw skill

## License

MIT

---

Built by [Primo Studio](https://github.com/Primo-Studio) 🇬🇫
