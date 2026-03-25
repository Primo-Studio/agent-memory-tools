#!/usr/bin/env python3
"""
LongMemEval-S benchmark for agent-memory-tools.

Validates retrieval + answer accuracy on the industry-standard LongMemEval-S dataset
(500 questions, 6 categories: knowledge updates, multi-session reasoning, temporal reasoning, etc.)

Usage:
  python3 longmemeval_benchmark.py [sample_size]
  
  sample_size: number of questions to test (default: 12)
  
Example:
  python3 longmemeval_benchmark.py 50

Requirements:
  - LongMemEval-S dataset at /tmp/longmemeval_s.json
    Download: wget https://raw.githubusercontent.com/xiaowu0162/LongMemEval/main/data/longmemeval_s.json
  
  - LM Studio running with:
    - GPT-OSS 20B (or compatible model)
    - text-embedding-nomic-embed-text-v1.5
  
  - Config: edit LM_STUDIO, ANSWER_MODEL, EMBED_MODEL below

Results:
  - Saves to /tmp/longmemeval_benchmark_results.json
  - Prints retrieval accuracy, RAG score, Oracle score
"""
import json, sys, os, subprocess, random, re, time
from pathlib import Path

# === Config ===
BENCHMARK_FILE = "/tmp/longmemeval_s.json"
SAMPLE_SIZE = int(sys.argv[1]) if len(sys.argv) > 1 else 12
ANSWER_MODEL = "openai/gpt-oss-20b"
EMBED_MODEL = "text-embedding-nomic-embed-text-v1.5"
LM_STUDIO = "http://localhost:1234/v1"
TOP_K = 5  # retrieve top-K sessions
CACHE_DIR = "/tmp/longmemeval_cache"
EMBED_CACHE_FILE = f"{CACHE_DIR}/embed_cache.json"

os.makedirs(CACHE_DIR, exist_ok=True)

# === Load benchmark ===
with open(BENCHMARK_FILE) as f:
    data = json.load(f)

categories = {}
for q in data:
    t = q['question_type']
    if t not in categories:
        categories[t] = []
    categories[t].append(q)

sample = []
per_cat = max(2, SAMPLE_SIZE // len(categories))
random.seed(42)
for cat, questions in sorted(categories.items()):
    chosen = random.sample(questions, min(per_cat, len(questions)))
    sample.extend(chosen)
sample = sample[:SAMPLE_SIZE]

# === Embedding functions ===
def get_embedding(text):
    """Get embedding via LM Studio nomic."""
    text = text[:2000]
    payload = json.dumps({"model": EMBED_MODEL, "input": text})
    try:
        result = subprocess.run(
            ['curl', '-s', f'{LM_STUDIO}/embeddings', '-H', 'Content-Type: application/json', '-d', payload],
            capture_output=True, text=True, timeout=30
        )
        resp = json.loads(result.stdout)
        return resp['data'][0]['embedding']
    except:
        return None

def cosine_sim(a, b):
    dot = sum(x*y for x,y in zip(a,b))
    na = sum(x*x for x in a)**0.5
    nb = sum(x*x for x in b)**0.5
    return dot/(na*nb) if na and nb else 0.0

def session_to_text(session):
    return "\n".join(f"{t['role']}: {t['content']}" for t in session)

# === Step 1: Ingest sessions ===
print("=" * 60)
print("STEP 1: Ingesting sessions into embed cache")
print("=" * 60, flush=True)

embed_cache = {}
if os.path.exists(EMBED_CACHE_FILE):
    with open(EMBED_CACHE_FILE) as f:
        embed_cache = json.load(f)
    print(f"Loaded {len(embed_cache)} cached embeddings", flush=True)

ingest_count = 0
for q in sample:
    qid = q['question_id']
    for sid, session in enumerate(q['haystack_sessions']):
        key = f"{qid}_{sid}"
        if key in embed_cache:
            continue
        
        text = session_to_text(session)
        if len(text.strip()) < 20:
            continue
        
        summary = text[:300]
        if len(text) > 500:
            summary += " ... " + text[-200:]
        
        emb = get_embedding(summary)
        if emb:
            embed_cache[key] = {
                "embedding": emb,
                "text_preview": text[:200],
                "char_len": len(text)
            }
            ingest_count += 1
            if ingest_count % 20 == 0:
                print(f"  Ingested {ingest_count} sessions...", flush=True)
                with open(EMBED_CACHE_FILE, 'w') as f:
                    json.dump(embed_cache, f)

with open(EMBED_CACHE_FILE, 'w') as f:
    json.dump(embed_cache, f)
print(f"Ingested {ingest_count} new sessions (total cache: {len(embed_cache)})", flush=True)

# === LLM functions ===
def ask_lm(prompt, max_tokens=500):
    try:
        payload = json.dumps({
            "model": ANSWER_MODEL,
            "messages": [
                {"role": "system", "content": "Answer directly and concisely. Give specific numbers, names, dates. If the information is in the conversation history, extract it precisely."},
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.1,
            "max_tokens": max_tokens
        })
        result = subprocess.run(
            ['curl', '-s', f'{LM_STUDIO}/chat/completions', '-H', 'Content-Type: application/json', '-d', payload],
            capture_output=True, text=True, timeout=180
        )
        resp = json.loads(result.stdout)
        msg = resp['choices'][0]['message']
        raw = msg.get('content', '').strip()
        if not raw:
            raw = msg.get('reasoning_content', '').strip()
        raw = re.sub(r'<think>.*?</think>', '', raw, flags=re.DOTALL).strip()
        if 'answer:' in raw.lower():
            parts = re.split(r'(?i)answer\s*:', raw)
            raw = parts[-1].strip()
        if len(raw) > 500:
            lines = [l.strip() for l in raw.split('\n') if l.strip()]
            raw = lines[-1] if lines else raw[-200:]
        return raw
    except Exception as e:
        return f"ERROR: {e}"

def strict_judge(question, expected, hypothesis):
    expected_str = str(expected).lower().strip()
    hyp_str = str(hypothesis).lower().strip()
    
    if expected_str in hyp_str:
        return True, "exact"
    
    exp_nums = set(re.findall(r'\d+\.?\d*', expected_str))
    hyp_nums = set(re.findall(r'\d+\.?\d*', hyp_str))
    if exp_nums and exp_nums.issubset(hyp_nums):
        return True, "number"
    
    exp_words = set(w for w in re.findall(r'[a-z]+', expected_str) if len(w) > 3)
    hyp_words = set(w for w in re.findall(r'[a-z]+', hyp_str) if len(w) > 3)
    if exp_words and len(exp_words & hyp_words) >= len(exp_words) * 0.7:
        return True, "keyword"
    
    prompt = f"""Judge strictly. Numbers must match exactly. Names must match. "I don't know" = WRONG.
Question: {question}
Expected: {expected}
Hypothesis: {hypothesis}
Reply ONLY "correct" or "incorrect"."""
    verdict = ask_lm(prompt, max_tokens=10)
    return "correct" in verdict.lower(), "llm"

# === Step 2 & 3: Retrieve + Answer ===
print("\n" + "=" * 60)
print("STEP 2 & 3: Retrieve + Answer")
print("=" * 60, flush=True)

scores = {'rag': [], 'oracle': []}
details = []
start_time = time.time()

for i, q in enumerate(sample):
    qid = q['question_id']
    qtype = q['question_type']
    question = q['question']
    expected = str(q['answer'])
    sessions = q['haystack_sessions']
    evidence_ids = q.get('answer_session_ids', [])
    all_ids = q.get('haystack_session_ids', list(range(len(sessions))))
    
    evidence_indices = set()
    for eid in evidence_ids:
        if eid in all_ids:
            evidence_indices.add(all_ids.index(eid))
    
    print(f"\n[{i+1}/{len(sample)}] {qtype}", flush=True)
    print(f"  Q: {question[:80]}", flush=True)
    print(f"  A: {expected[:80]}", flush=True)
    
    q_embed = get_embedding(question)
    if not q_embed:
        scores['rag'].append(False)
        scores['oracle'].append(False)
        continue
    
    session_scores = []
    for sid in range(len(sessions)):
        key = f"{qid}_{sid}"
        if key in embed_cache and embed_cache[key].get('embedding'):
            sim = cosine_sim(q_embed, embed_cache[key]['embedding'])
            session_scores.append((sid, sim))
    
    session_scores.sort(key=lambda x: x[1], reverse=True)
    top_k = session_scores[:TOP_K]
    retrieved_ids = set(s[0] for s in top_k)
    hit = bool(evidence_indices & retrieved_ids)
    
    print(f"  Evidence: {sorted(evidence_indices)} | Retrieved top-{TOP_K}: {[s[0] for s in top_k]}", flush=True)
    print(f"  Sims: {[f'{s[1]:.3f}' for s in top_k]} | Hit: {'YES' if hit else 'NO'}", flush=True)
    
    rag_parts = []
    for sid, sim in top_k:
        text = session_to_text(sessions[sid])
        if len(text) > 3000:
            text = text[:1500] + "\n[...]\n" + text[-1500:]
        rag_parts.append(f"=== Session {sid+1} (relevance: {sim:.2f}) ===\n{text}")
    rag_ctx = "\n\n".join(rag_parts)
    
    rag_prompt = f"""You are answering a question based on conversation history.
Search carefully through ALL the sessions below. The answer IS in there — extract it precisely.
Give specific numbers, names, dates. Be exact.

Question: {question}

{rag_ctx}

Answer (be specific and concise):"""
    
    rag_ans = ask_lm(rag_prompt, max_tokens=300)
    rag_ok, rag_m = strict_judge(question, expected, rag_ans)
    scores['rag'].append(rag_ok)
    print(f"  RAG:    {rag_ans[:70]} -> {'OK' if rag_ok else 'FAIL'} ({rag_m})", flush=True)
    
    oracle_parts = []
    for sid in sorted(evidence_indices):
        if sid < len(sessions):
            text = session_to_text(sessions[sid])
            if len(text) > 4000:
                text = text[:2000] + "\n[...]\n" + text[-2000:]
            oracle_parts.append(f"=== Session {sid+1} ===\n{text}")
    oracle_ctx = "\n\n".join(oracle_parts) if oracle_parts else rag_ctx
    
    oracle_prompt = f"""You are answering a question based on conversation history.
The answer IS in the sessions below. Extract it precisely.
Give specific numbers, names, dates.

Question: {question}

{oracle_ctx}

Answer (be specific and concise):"""
    
    oracle_ans = ask_lm(oracle_prompt, max_tokens=300)
    oracle_ok, oracle_m = strict_judge(question, expected, oracle_ans)
    scores['oracle'].append(oracle_ok)
    print(f"  Oracle: {oracle_ans[:70]} -> {'OK' if oracle_ok else 'FAIL'} ({oracle_m})", flush=True)
    
    details.append({
        'qid': qid, 'type': qtype, 'question': question, 'expected': expected,
        'retrieved_ids': [s[0] for s in top_k], 'evidence_ids': sorted(evidence_indices),
        'evidence_hit': hit,
        'rag_answer': rag_ans, 'rag_correct': rag_ok,
        'oracle_answer': oracle_ans, 'oracle_correct': oracle_ok,
    })

elapsed = time.time() - start_time

# === Results ===
print("\n" + "=" * 60)
print(f"RESULTS — {elapsed:.0f}s")
print("=" * 60)

hits = sum(1 for d in details if d['evidence_hit'])
print(f"\nRetrieval accuracy (top-{TOP_K}): {hits}/{len(details)} ({hits/len(details)*100:.0f}%)")

for mode in ['rag', 'oracle']:
    by_type = {}
    for s, q in zip(scores[mode], sample):
        t = q['question_type']
        if t not in by_type:
            by_type[t] = []
        by_type[t].append(s)
    
    print(f"\n--- {mode.upper()} ---")
    for cat in sorted(categories.keys()):
        sc = by_type.get(cat, [])
        if sc:
            pct = sum(sc)/len(sc)*100
            print(f"  {cat:<30} {pct:>5.0f}% ({sum(sc)}/{len(sc)})")
    total = sum(scores[mode]) / len(scores[mode]) * 100
    print(f"  {'TOTAL':<30} {total:>5.1f}%")

print(f"\nRef: ByteRover ~92-96% | Honcho ~88%")

with open('/tmp/longmemeval_benchmark_results.json', 'w') as f:
    json.dump({
        'details': details,
        'rag_score': sum(scores['rag'])/len(scores['rag'])*100,
        'oracle_score': sum(scores['oracle'])/len(scores['oracle'])*100,
        'retrieval_accuracy': hits/len(details)*100,
        'elapsed': elapsed,
        'config': {'model': ANSWER_MODEL, 'embed': EMBED_MODEL, 'top_k': TOP_K, 'sample': SAMPLE_SIZE}
    }, f, indent=2)
print(f"\nSaved: /tmp/longmemeval_benchmark_results.json")
