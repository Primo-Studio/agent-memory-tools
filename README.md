# OpenClaw Memory Scripts

Advanced memory tools for OpenClaw agents. Works with any local LLM (Ollama, LM Studio) or cloud API.

## Scripts

### `qmd-multihop`
Multi-hop reasoning search over QMD-indexed markdown files. Chains multiple search queries to find complex answers.
- Uses nomic-embed + LLM reranker + LLM orchestrator
- Configurable: any OpenAI-compatible API (local or cloud)

### `qmd-decay-query`
Temporal decay search — recent facts score higher, permanent knowledge is protected.
- 14-day half-life for episodic memory
- Protected categories: savoir, erreur (no decay)

### `build-knowledge-graph`
Extracts entities and relationships from markdown files into a JSON knowledge graph.
- LLM-powered entity extraction
- Output: `.cache/knowledge-graph.json`

### `extract-facts.md`
Prompt template for extracting durable facts from LCM summaries.

## Configuration

Scripts use OpenAI-compatible API. Configure by editing the URL/model constants at the top of each script:
- **LM Studio**: `http://localhost:1234/v1/chat/completions`
- **Ollama**: `http://localhost:11434/v1/chat/completions`
- **OpenAI**: `https://api.openai.com/v1/chat/completions`

## Requirements
- Python 3.9+
- QMD (`bun install -g @tobilu/qmd`)
- A local or remote LLM

## License
MIT — Primo Studio
