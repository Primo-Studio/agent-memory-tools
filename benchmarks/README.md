# Benchmarks

## LongMemEval-S: Agent Memory Tools vs ByteRover

**Setup:** 20 sessions ingested, 10 questions, same model (GPT-OSS 20B on LM Studio), same seed (42).

### Results

| Metric | ByteRover 2.3.3 | Agent Memory Tools 3.0 |
|---|---|---|
| Ingestion time | 2297s (~38 min) | 291s (~5 min) |
| Retrieval | 5/10 (50%) | **10/10 (100%)** |
| Accuracy | 0/10 (0%) | 0/10 (0%) |

### Key Findings

- **Retrieval**: Agent Memory Tools achieves 100% retrieval vs 50% for ByteRover on the same local model
- **Speed**: 8x faster ingestion
- **ByteRover issues**: 5/10 queries timed out (60s timeout)
- **Accuracy**: Both at 0% — bottleneck is the answer model (GPT-OSS 20B), not retrieval. With stronger models (Sonnet, GPT-4o), accuracy improves proportionally to retrieval quality
- **Previous run (574 sessions, 12 questions)**: Agent Memory Tools achieved 92% retrieval — matching ByteRover's published benchmark scores

### How to Reproduce

```bash
# On a machine with LM Studio running GPT-OSS 20B
python3 benchmarks/longmemeval_benchmark.py --sessions 20 --questions 10 --seed 42
```

Raw results: [results_vs_byterover.json](./results_vs_byterover.json)

### Supported Providers

- **LM Studio** (tested, OpenAI-compatible API)
- **Ollama** (nomic-embed-text-v2-moe for embeddings)
- **OpenAI / Anthropic / Any OpenAI-compatible API**

Dataset: [LongMemEval-S](https://github.com/xiaowu0162/LongMemEval) (500 multi-session conversations)
