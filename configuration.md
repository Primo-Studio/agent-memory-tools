# Configuration Guide

## config.json

All scripts read from `scripts/config.json`. Edit this file to match your setup.

## Presets

Use `--preset` on any script to override LLM/embed settings:

```bash
python3 scripts/multihop_search.py "query" --preset ollama
python3 scripts/decay_search.py "query" --preset openai
```

Available presets: `ollama`, `openai`. Default uses top-level config (LM Studio).

## Provider Setup

### LM Studio (recommended for local)
1. Start LM Studio, load a model
2. Enable local server (default port 1234)
3. Config: `"baseUrl": "http://localhost:1234/v1"`
4. For embeddings: load `text-embedding-nomic-embed-text-v1.5`

### Ollama
1. `ollama serve`
2. `ollama pull nomic-embed-text-v2-moe` (embeddings)
3. `ollama pull qwen3.5:27b` (LLM)
4. Use `--preset ollama` or edit config

### OpenAI / Cloud
1. Set `OPENAI_API_KEY` env var
2. Use `--preset openai` or edit config
3. Costs ~$0.001/query (embedding) + ~$0.01/query (LLM)

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `MEMORY_WORKSPACE` | skill parent dir | Override workspace path |
| `OPENAI_API_KEY` | none | Required for openai preset |

## QMD Setup

```bash
# Install
bun install -g qmd

# Create collection
qmd collections add workspace /path/to/workspace "**/*.md"

# Index
qmd embed
```

## Tuning

| Parameter | Default | Effect |
|-----------|---------|--------|
| `search.maxHops` | 4 | More hops = deeper but slower |
| `search.confidenceThreshold` | 0.6 | Lower = more answers, less precise |
| `search.decayHalfLifeDays` | 14 | Higher = older facts stay relevant longer |
| `embeddings.chunkTokens` | 400 | Lower if embed model has small context |
| `llm.temperature` | 0.1 | Keep low for factual extraction |
