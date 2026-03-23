# Prompt d'extraction de faits — Phase 2 mémoire

## Utilisation
Envoyé à **Sonnet** (`claude --print`, $0 via Max) pendant le boot de Koda.
Ancien modèle : `qwen3.5:9b` (Ollama) — remplacé le 22/03 pour fiabilité JSON + vitesse (5s vs 60s).
L'input = résumés LCM des dernières 24h.
Fonctionne aussi pour Luna (même prompt, même modèle Sonnet via API).

## Prompt

```
Tu es un extracteur de faits. Tu reçois des résumés de conversations entre Neto (dirigeant) et Koda (dev IA).

RÈGLES :
- Extrais UNIQUEMENT les faits durables (vrais demain, pas juste aujourd'hui)
- Ignore les actions ponctuelles ("j'ai lancé le build", "j'ai envoyé le message")
- Ignore ce qui est déjà du contexte de conversation (salutations, confirmations)
- Chaque fait doit être autonome (compréhensible sans le contexte)
- Confiance : 0.0 à 1.0 (ne retourne que ≥ 0.5)

CLASSIFICATION :
- "sémantique" → fait durable, règle, préférence, info technique
- "épisodique" → événement daté important (déploiement, décision, incident)
- "erreur" → leçon apprise, erreur à ne pas répéter

FICHIER CIBLE :
- USER.md → préférence, habitude, frustration de Neto
- COMPANY.md → client, chiffre, décision business, RH
- TOOLS.md → outil, token, config technique découverte
- MEMORY.md → tout le reste (règles techniques, patterns, événements)

ZONE (si fichier = MEMORY.md) :
- "savoir" → fait technique, règle, pattern (zone 🧠)
- "chronologie" → événement daté (zone 📅)
- "erreurs" → leçon critique (zone ❌)
- "navigation" → nouveau fichier/dossier important (zone 📌)

Réponds UNIQUEMENT en JSON valide, pas de texte autour :
[
  {
    "fait": "description courte et autonome",
    "type": "sémantique|épisodique|erreur",
    "fichier": "USER.md|COMPANY.md|TOOLS.md|MEMORY.md",
    "zone": "savoir|chronologie|erreurs|navigation",
    "date": "JJ/MM/AAAA ou null",
    "confiance": 0.85
  }
]

Si aucun fait durable trouvé, retourne : []

RÉSUMÉS À ANALYSER :
{RÉSUMÉS_LCM}
```

## Double écriture : .md + Convex agentMemory

Chaque fait extrait est écrit **à deux endroits** :
1. Fichier .md → documentation pour Neto (humain-lisible)
2. Convex `agentMemory:store` → source de vérité temps réel (queryable par tous les agents)

### Mapping type → category Convex
| Type extraction | Category Convex |
|-----------------|----------------|
| sémantique      | savoir         |
| épisodique      | chronologie    |
| erreur          | erreur         |

### Script d'écriture Convex (après extraction)
```bash
for each fact in extracted_facts:
  curl -s -X POST "https://notable-dragon-607.convex.cloud/api/mutation" \
    -H "Content-Type: application/json" \
    -d "{\"path\":\"agentMemory:store\",\"args\":{
      \"fact\":\"${fact.fait}\",
      \"category\":\"${mapped_category}\",
      \"agent\":\"koda\",
      \"confidence\":${fact.confiance},
      \"source\":\"boot-extract\",
      \"tags\":[\"auto-extract\"]
    }}"
```

## Notes
- `zone` n'est pertinent que si `fichier` = MEMORY.md
- `date` n'est pertinent que si `type` = épisodique
- Le prompt doit rester sous 2000 tokens pour laisser de la place à l'output
- Temperature 0.1 pour maximiser la cohérence JSON
- Si le JSON est invalide → ignorer et logger l'erreur, ne pas retry
- **Priorité** : Convex write > .md write (si un seul marche, c'est Convex qui compte)

## Invocation
```bash
# Sonnet (défaut, recommandé)
claude --print --model claude-sonnet-4-5 "$(cat prompt-with-summaries.txt)"

# Fallback Ollama (si Max indispo)
curl -s http://localhost:11434/api/generate -d '{"model":"qwen3.5:9b","prompt":"...","stream":false}'
```
