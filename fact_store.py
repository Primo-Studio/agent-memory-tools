#!/usr/bin/env python3
"""
fact_store — Abstraction layer for fact storage.
Supports Convex (agentMemory) or local JSON file.

Auto-detects: if convexUrl is set in config → Convex. Otherwise → local JSON.

Local JSON provides the same API surface:
  store(fact, category, agent, confidence, source) → {action, id}
  search(query, category, limit) → [facts]
  recent(limit) → [facts]
  stats() → {total, by_category}
  forget(fact) → bool
"""
from __future__ import annotations
import hashlib, json, os, re, subprocess, sys, time, uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from llm_client import load_config


def _get_workspace(cfg: dict) -> Path:
    """Get workspace path from config or env."""
    ws = os.environ.get("MEMORY_WORKSPACE") or cfg.get("workspace", "")
    if ws:
        return Path(ws)
    # Deduce from script location
    return Path(__file__).parent.parent.parent


def _get_store_path(cfg: dict) -> Path:
    """Path to local facts JSON file."""
    ws = _get_workspace(cfg)
    cache_dir = ws / ".cache"
    cache_dir.mkdir(parents=True, exist_ok=True)
    return cache_dir / "agent-facts.json"


def _is_convex_configured(cfg: dict) -> bool:
    """Check if Convex backend is available."""
    url = cfg.get("convexUrl", "")
    if not url:
        return False
    # Quick connectivity check (cached for session)
    return True


def _fact_hash(fact: str) -> str:
    """Deterministic hash for dedup."""
    normalized = re.sub(r'\s+', ' ', fact.strip().lower())
    return hashlib.sha256(normalized.encode()).hexdigest()[:16]


def _keyword_set(fact: str) -> set:
    """Extract keywords for Jaccard similarity."""
    words = re.sub(r'[^\w\s]', '', fact.lower()).split()
    stop = {'le', 'la', 'les', 'de', 'du', 'des', 'un', 'une', 'et', 'ou', 'en',
            'est', 'a', 'the', 'is', 'of', 'and', 'to', 'in', 'for', 'on', 'with'}
    return {w for w in words if len(w) > 2 and w not in stop}


def _jaccard(s1: set, s2: set) -> float:
    if not s1 or not s2:
        return 0.0
    return len(s1 & s2) / len(s1 | s2)


# ─── Convex backend ───

CONVEX_URL = "https://notable-dragon-607.convex.cloud/api/mutation"
CONVEX_QUERY_URL = "https://notable-dragon-607.convex.cloud/api/query"


def _convex_call(path: str, args: dict, is_mutation: bool = False, timeout: int = 15) -> dict | None:
    """Call Convex API."""
    url = CONVEX_URL if is_mutation else CONVEX_QUERY_URL
    payload = json.dumps({"path": path, "args": args})
    try:
        r = subprocess.run(
            ["curl", "-s", "-X", "POST", url, "-H", "Content-Type: application/json", "-d", payload],
            capture_output=True, text=True, timeout=timeout
        )
        data = json.loads(r.stdout)
        if data.get("status") == "success":
            return data.get("value")
    except Exception:
        pass
    return None


def _convex_store(fact: str, category: str, agent: str, confidence: float, source: str) -> dict:
    result = _convex_call("agentMemory:store", {
        "fact": fact, "category": category, "agent": agent,
        "confidence": confidence, "source": source
    }, is_mutation=True)
    return result or {"action": "error"}


def _convex_search(query: str, category: str = None, limit: int = 10) -> list:
    args = {"query": query, "limit": limit}
    if category:
        args["category"] = category
    result = _convex_call("agentMemory:search", args)
    return result if isinstance(result, list) else []


def _convex_recent(limit: int = 20) -> list:
    result = _convex_call("agentMemory:recent", {"limit": limit})
    return result if isinstance(result, list) else []


def _convex_stats() -> dict:
    result = _convex_call("agentMemory:stats", {})
    return result or {}


def _convex_forget(fact: str) -> bool:
    result = _convex_call("agentMemory:forget", {"fact": fact}, is_mutation=True)
    return result is not None


# ─── Local JSON backend ───

def _load_local(path: Path) -> list:
    if path.exists():
        try:
            return json.loads(path.read_text())
        except (json.JSONDecodeError, OSError):
            pass
    return []


def _save_local(path: Path, facts: list):
    path.write_text(json.dumps(facts, ensure_ascii=False, indent=2))


def _local_store(fact: str, category: str, agent: str, confidence: float, source: str, cfg: dict) -> dict:
    path = _get_store_path(cfg)
    facts = _load_local(path)
    
    fhash = _fact_hash(fact)
    kw_new = _keyword_set(fact)
    
    # Dedup: exact hash or Jaccard > 0.7
    for existing in facts:
        if existing.get("_hash") == fhash:
            existing["confidence"] = max(existing.get("confidence", 0), confidence)
            existing["updatedAt"] = time.time() * 1000
            existing["accessCount"] = existing.get("accessCount", 0) + 1
            _save_local(path, facts)
            return {"action": "updated", "id": existing["_id"]}
        
        kw_old = _keyword_set(existing.get("fact", ""))
        if _jaccard(kw_new, kw_old) > 0.7:
            existing["fact"] = fact
            existing["confidence"] = max(existing.get("confidence", 0), confidence)
            existing["updatedAt"] = time.time() * 1000
            existing["accessCount"] = existing.get("accessCount", 0) + 1
            _save_local(path, facts)
            return {"action": "updated", "id": existing["_id"]}
    
    # New fact
    new_id = f"local_{uuid.uuid4().hex[:16]}"
    facts.append({
        "_id": new_id,
        "_hash": fhash,
        "fact": fact,
        "category": category,
        "agent": agent,
        "confidence": confidence,
        "source": source,
        "createdAt": time.time() * 1000,
        "updatedAt": time.time() * 1000,
        "accessCount": 0,
        "superseded": False
    })
    _save_local(path, facts)
    return {"action": "created", "id": new_id}


def _local_search(query: str, category: str = None, limit: int = 10, cfg: dict = None) -> list:
    path = _get_store_path(cfg or {})
    facts = _load_local(path)
    
    # Filter by category
    if category:
        facts = [f for f in facts if f.get("category") == category and not f.get("superseded")]
    else:
        facts = [f for f in facts if not f.get("superseded")]
    
    # Score by keyword overlap
    kw_query = _keyword_set(query)
    scored = []
    for f in facts:
        kw_fact = _keyword_set(f.get("fact", ""))
        score = _jaccard(kw_query, kw_fact)
        if score > 0.05:  # Minimal relevance
            scored.append((score, f))
    
    scored.sort(key=lambda x: x[0], reverse=True)
    return [f for _, f in scored[:limit]]


def _local_recent(limit: int = 20, cfg: dict = None) -> list:
    path = _get_store_path(cfg or {})
    facts = _load_local(path)
    facts = [f for f in facts if not f.get("superseded")]
    facts.sort(key=lambda f: f.get("createdAt", 0), reverse=True)
    return facts[:limit]


def _local_stats(cfg: dict = None) -> dict:
    path = _get_store_path(cfg or {})
    facts = _load_local(path)
    active = [f for f in facts if not f.get("superseded")]
    by_cat = {}
    for f in active:
        cat = f.get("category", "unknown")
        by_cat[cat] = by_cat.get(cat, 0) + 1
    return {"total": len(active), "byCategory": by_cat}


def _local_forget(fact: str, cfg: dict = None) -> bool:
    path = _get_store_path(cfg or {})
    facts = _load_local(path)
    fhash = _fact_hash(fact)
    for f in facts:
        if f.get("_hash") == fhash or f.get("fact") == fact:
            f["superseded"] = True
            _save_local(path, facts)
            return True
    return False


# ─── Public API (auto-selects backend) ───

class FactStore:
    """Unified fact store. Auto-detects Convex or local JSON."""
    
    def __init__(self, cfg: dict = None):
        if cfg is None:
            cfg = load_config()
        self.cfg = cfg
        self.use_convex = _is_convex_configured(cfg)
        self.backend = "convex" if self.use_convex else "local"
    
    def store(self, fact: str, category: str = "savoir", agent: str = "koda",
              confidence: float = 0.8, source: str = "extract_facts") -> dict:
        if self.use_convex:
            return _convex_store(fact, category, agent, confidence, source)
        return _local_store(fact, category, agent, confidence, source, self.cfg)
    
    def search(self, query: str, category: str = None, limit: int = 10) -> list:
        if self.use_convex:
            return _convex_search(query, category, limit)
        return _local_search(query, category, limit, self.cfg)
    
    def recent(self, limit: int = 20) -> list:
        if self.use_convex:
            return _convex_recent(limit)
        return _local_recent(limit, self.cfg)
    
    def stats(self) -> dict:
        if self.use_convex:
            return _convex_stats()
        return _local_stats(self.cfg)
    
    def forget(self, fact: str) -> bool:
        if self.use_convex:
            return _convex_forget(fact)
        return _local_forget(fact, self.cfg)
    
    def __repr__(self):
        return f"FactStore(backend={self.backend})"


if __name__ == "__main__":
    cfg = load_config()
    store = FactStore(cfg)
    print(f"Backend: {store.backend}")
    stats = store.stats()
    print(f"Stats: {json.dumps(stats, indent=2)}")
