# Changelog

## v1.1.0 (2026-03-23)

### Corrections
- **Compatibilité LM Studio** : tous les scripts fonctionnent maintenant avec l'API OpenAI-compatible (LM Studio, vLLM, etc.)
  - `call_llm_ollama` : format `messages/choices` au lieu de `prompt/response`
  - `embed_ollama` : parsing format OpenAI (`data[].embedding`) + fallback Ollama
- **PATH system** : injection automatique `/opt/homebrew/bin` pour résoudre `node`/`qmd` introuvables
- **SyntaxError** : `from __future__ import annotations` toujours en première position
- **Fallback LLM** : les fallbacks vers `claude` CLI remplacés par LM Studio local
- **Timeout** : `curl --max-time 120` sur les appels LLM (évite les blocages silencieux)
- **Thinking tags** : strip automatique des balises `<think>` dans les réponses Qwen

### Tests validés
- `qmd-multihop` : 85% confiance, 5 résultats, 54s (Qwen 3.5 35B via LM Studio)
- `qmd-decay-query` : 5 résultats avec scoring temporel correct
- `build-knowledge-graph` : fonctionne, long mais stable

## v1.0.0 (2026-03-23)

### Initial
- Scripts adaptés depuis Koda (cloud) vers local (Ollama/LM Studio)
- Modèles : `qwen/qwen3.5-35b-a3b` (LLM), `text-embedding-nomic-embed-text-v1.5` (embed)
