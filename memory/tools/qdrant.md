# Qdrant Semantic Search 🔍

**Script:** `scripts/qdrant_indexer.py`
**Credentials:** `secrets.env` → QDRANT_URL, QDRANT_API_KEY, LITELLM_API_KEY
**Embedding model:** Qwen3-Embedding-0.6B (via LiteLLM)
**Collection:** `arkasha`

## Команды

```bash
# Поиск
python3 scripts/qdrant_indexer.py search "запрос на русском"

# Индексировать почту (dparmeev, spam, contact, contact-lumines)
python3 scripts/qdrant_indexer.py index-emails

# Индексировать memory файлы
python3 scripts/qdrant_indexer.py index-memory
```

## Когда использовать

- Поиск старых писем по смыслу (не по ключевым словам)
- Найти контекст из прошлых разговоров
- Связать информацию из разных источников (email + memory)
