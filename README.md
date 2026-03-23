# OpenClaw Memory Scripts

Advanced memory tools for OpenClaw agents. Works with any local LLM (Ollama, LM Studio) or cloud API.

## Scripts

### `qmd-multihop`
Multi-hop reasoning search over QMD-indexed markdown files. Chains multiple search queries to find complex answers.

```bash
qmd-multihop "Quel bug Sol a eu sur Primask ?"
qmd-multihop "workflow tâche" --qmd          # Force QMD au lieu de nomic
qmd-multihop "erreur deploy" --debug         # Mode debug
```

- Uses embed model + LLM reranker + LLM orchestrator
- Configurable: any OpenAI-compatible API (local or cloud)

### `qmd-decay-query`
Temporal decay search — recent facts score higher, permanent knowledge is protected.

```bash
qmd-decay-query "bug récent Sol"
```

- 14-day half-life for episodic memory
- Protected categories: savoir, erreur (no decay)

### `build-knowledge-graph`
Extracts entities and relationships from markdown files into a JSON knowledge graph.

```bash
build-knowledge-graph              # Full rebuild
build-knowledge-graph --dry-run    # Preview only
```

- LLM-powered entity extraction
- Output: `.cache/knowledge-graph.json`

### `extract-facts.md`
Prompt template for extracting durable facts from LCM summaries.

## Configuration

Each script has constants at the top. Adapt to your setup:

| Variable | LM Studio | Ollama | OpenAI |
|----------|-----------|--------|--------|
| LLM URL | `localhost:1234/v1/chat/completions` | `localhost:11434/api/generate` | `api.openai.com/v1/chat/completions` |
| Embed URL | `localhost:1234/v1/embeddings` | `localhost:11434/api/embed` | `api.openai.com/v1/embeddings` |
| LLM Model | `qwen/qwen3.5-35b-a3b` | `qwen3.5:27b` | `gpt-4o` |
| Embed Model | `text-embedding-nomic-embed-text-v1.5` | `nomic-embed-text-v2-moe` | `text-embedding-3-small` |

> ⚠️ If switching between Ollama and OpenAI-compatible APIs, the response format differs.
> Scripts handle both formats (OpenAI `data[].embedding` + Ollama `embeddings[]`).

## Requirements

- Python 3.9+
- QMD CLI (`bun install -g qmd`) with an indexed collection
- A local LLM server (LM Studio or Ollama) OR OpenAI API key
- `curl` in PATH

## Troubleshooting

| Symptom | Cause | Fix |
|---------|-------|-----|
| Script hangs silently | LLM server not running or wrong port | Check `curl localhost:1234/v1/models` |
| `node: not found` | PATH missing homebrew | Script auto-injects, or `export PATH=/opt/homebrew/bin:$PATH` |
| `SyntaxError: from __future__` | Import order broken | `from __future__` must be first import |
| 0 results | QMD not indexed or wrong collection | `qmd collections list` + `qmd embed` |
| `<think>` tags in output | Qwen reasoning mode | Scripts auto-strip, update if needed |

## License

MIT
