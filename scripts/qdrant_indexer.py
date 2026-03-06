#!/usr/bin/env python3
"""
Qdrant Indexer для Аркаши
Индексирует почту, память, документы в векторную БД
"""
import os
import sys
import json
import hashlib
import subprocess
from datetime import datetime
from pathlib import Path

# Загружаем secrets.env если он доступен
secrets_path = Path.home() / ".openclaw" / "secrets.env"
if secrets_path.exists():
    with open(secrets_path) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                key, value = line.split('=', 1)
                os.environ[key] = value

# Конфиг из переменных окружения
LITELLM_BASE = os.getenv('LITELLM_BASE_URL', 'https://litellm.jakeberrimor.com')
LITELLM_KEY = os.getenv('LITELLM_API_KEY')
QDRANT_URL = os.getenv('QDRANT_URL', 'https://qdrant.jakeberrimor.com')
QDRANT_KEY = os.getenv('QDRANT_API_KEY', 'sk-1234')
COLLECTION = os.getenv('QDRANT_COLLECTION', 'arkasha')
EMBEDDING_MODEL = os.getenv('EMBEDDING_MODEL', 'vl-Qwen/Qwen3-Embedding-0.6B')
NEO4J_URL = os.getenv('NEO4J_URL', 'http://neo4j-arkasha-pojvu0-34b918-80-87-197-0.traefik.me')
NEO4J_USER = os.getenv('NEO4J_USER', 'neo4j')
NEO4J_PASS = os.getenv('NEO4J_PASS', 'arkasha-neo4j-2026')

def http_request(url, method="GET", headers=None, data=None):
    """HTTP запрос через urllib"""
    import urllib.request
    import urllib.error
    
    headers = headers or {}
    req = urllib.request.Request(url, headers=headers, method=method)
    
    if data:
        req.add_header('Content-Type', 'application/json')
        req.data = json.dumps(data).encode('utf-8')
    
    try:
        with urllib.request.urlopen(req) as response:
            return json.loads(response.read().decode('utf-8'))
    except urllib.error.HTTPError as e:
        print(f"HTTP Error {e.code}: {e.read().decode('utf-8')}", file=sys.stderr)
        raise

def get_embedding(text):
    """Получить embedding через LiteLLM"""
    return http_request(
        f"{LITELLM_BASE}/v1/embeddings",
        method="POST",
        headers={"Authorization": f"Bearer {LITELLM_KEY}"},
        data={"model": EMBEDDING_MODEL, "input": text}
    )['data'][0]['embedding']

def points_exist(point_ids):
    """Проверить какие point_id уже есть в Qdrant. Возвращает set существующих id."""
    if not point_ids:
        return set()
    try:
        result = http_request(
            f"{QDRANT_URL}/collections/{COLLECTION}/points",
            method="POST",
            headers={"api-key": QDRANT_KEY},
            data={"ids": list(point_ids), "with_payload": False, "with_vector": False}
        )
        return {p['id'] for p in result.get('result', [])}
    except Exception:
        return set()

def index_point(point_id, text, metadata):
    """Добавить точку в Qdrant"""
    # Получаем embedding
    vector = get_embedding(text)
    
    # Индексируем в Qdrant
    return http_request(
        f"{QDRANT_URL}/collections/{COLLECTION}/points",
        method="PUT",
        headers={"api-key": QDRANT_KEY},
        data={
            "points": [{
                "id": point_id,
                "vector": vector,
                "payload": {
                    **metadata,
                    "text": text[:1000],  # Ограничиваем payload
                    "indexed_at": datetime.now().isoformat()
                }
            }]
        }
    )

def search(query, limit=5, filter_type=None, account=None):
    """
    Семантический поиск с фильтрами
    
    Args:
        query: поисковый запрос
        limit: макс. кол-во результатов
        filter_type: фильтр по типу ("email", "memory", "session")
        account: фильтр по email account ("dparmeev", "spam", etc.)
    """
    # Получаем embedding запроса
    vector = get_embedding(query)
    
    # Строим фильтры
    filters = {}
    must_conditions = []
    
    if filter_type:
        must_conditions.append({
            "key": "type",
            "match": {"value": filter_type}
        })
    
    if account:
        must_conditions.append({
            "key": "account",
            "match": {"value": account}
        })
    
    if must_conditions:
        filters = {"must": must_conditions}
    
    # Ищем в Qdrant
    search_params = {
        "vector": vector,
        "limit": limit,
        "with_payload": True
    }
    
    if filters:
        search_params["filter"] = filters
    
    return http_request(
        f"{QDRANT_URL}/collections/{COLLECTION}/points/search",
        method="POST",
        headers={"api-key": QDRANT_KEY},
        data=search_params
    )['result']

def index_email(email_id, account, subject, from_addr, date, body):
    """Индексировать письмо"""
    # Уникальный ID из аккаунта + email_id
    point_id = int(hashlib.md5(f"{account}:{email_id}".encode()).hexdigest()[:8], 16)
    
    # Текст для индексации
    text = f"Subject: {subject}\nFrom: {from_addr}\nDate: {date}\n\n{body}"
    
    # Метаданные
    metadata = {
        "type": "email",
        "account": account,
        "email_id": email_id,
        "subject": subject,
        "from": from_addr,
        "date": date
    }
    
    return index_point(point_id, text, metadata)

def index_memory(file_path, content):
    """Индексировать файл памяти"""
    # ID из пути файла
    point_id = int(hashlib.md5(file_path.encode()).hexdigest()[:8], 16)
    
    metadata = {
        "type": "memory",
        "file": file_path,
        "date": datetime.now().isoformat()
    }
    
    return index_point(point_id, content, metadata)

def chunk_markdown(content, file_path, max_chunk_size=800, overlap=100):
    """
    Разбить markdown-файл на чанки по заголовкам (##, ###).
    Большие секции дополнительно нарезаются с overlap.
    Возвращает список dict: {text, section, parent_section, chunk_id}
    """
    import re
    chunks = []
    lines = content.split('\n')

    current_h1 = ''
    current_h2 = ''
    current_h3 = ''
    current_lines = []
    current_level = 0

    def split_large(text, section, parent, level):
        """Нарезать большой текст на части с overlap"""
        words = text.split()
        if not words:
            return []
        result = []
        step = max_chunk_size - overlap
        # Работаем посимвольно: ищем куски по ~max_chunk_size символов
        start = 0
        part = 0
        while start < len(text):
            end = start + max_chunk_size
            chunk_text = text[start:end]
            # Обрезаем по слову чтобы не рвать на середине
            if end < len(text):
                last_space = chunk_text.rfind(' ')
                if last_space > max_chunk_size // 2:
                    chunk_text = chunk_text[:last_space]
            label = f'{section} (часть {part+1})' if part > 0 else section
            result.append((chunk_text.strip(), label, parent, level))
            start += len(chunk_text) - overlap
            if start < 0:
                break
            part += 1
        return result

    def flush(section, parent, level):
        text = '\n'.join(current_lines).strip()
        if len(text) < 30:
            return  # слишком мало — скип

        # Добавляем контекст родителя в начало чанка
        prefix = f'[{parent}] ' if parent and parent != section else ''

        if len(text) <= max_chunk_size:
            full_text = f'{prefix}{section}\n\n{text}' if section else text
            chunk_id = hashlib.md5(f'{file_path}:{section}:{text[:50]}'.encode()).hexdigest()[:12]
            chunks.append({
                'chunk_id': chunk_id,
                'section': section,
                'parent_section': parent,
                'level': level,
                'text': full_text,
                'raw_text': text,
            })
        else:
            # Большой раздел — нарезаем
            parts = split_large(text, section, parent, level)
            for raw_text, label, par, lv in parts:
                full_text = f'{prefix}{label}\n\n{raw_text}' if label else raw_text
                chunk_id = hashlib.md5(f'{file_path}:{label}:{raw_text[:50]}'.encode()).hexdigest()[:12]
                chunks.append({
                    'chunk_id': chunk_id,
                    'section': label,
                    'parent_section': par,
                    'level': lv,
                    'text': full_text,
                    'raw_text': raw_text,
                })

    for line in lines:
        h1 = re.match(r'^# (.+)', line)
        h2 = re.match(r'^## (.+)', line)
        h3 = re.match(r'^### (.+)', line)

        if h1:
            flush(current_h2 or current_h1, current_h1, current_level)
            current_lines = []
            current_h1 = h1.group(1).strip()
            current_h2 = ''
            current_h3 = ''
            current_level = 1
        elif h2:
            flush(current_h2, current_h1, current_level)
            current_lines = []
            current_h2 = h2.group(1).strip()
            current_h3 = ''
            current_level = 2
        elif h3:
            flush(current_h3 or current_h2, current_h2, current_level)
            current_lines = []
            current_h3 = h3.group(1).strip()
            current_level = 3
        else:
            current_lines.append(line)

    # Последний чанк
    section = current_h3 or current_h2 or current_h1 or file_path
    parent = current_h2 or current_h1 or ''
    flush(section, parent, current_level)

    return chunks


def neo4j_query(cypher, params=None):
    """Выполнить Cypher запрос через HTTP API"""
    import base64
    token = base64.b64encode(f'{NEO4J_USER}:{NEO4J_PASS}'.encode()).decode()
    return http_request(
        f'{NEO4J_URL}/db/neo4j/tx/commit',
        method='POST',
        headers={'Authorization': f'Basic {token}'},
        data={'statements': [{'statement': cypher, 'parameters': params or {}}]}
    )


def extract_and_index_entities(chunk, file_path):
    """
    Извлечь сущности из чанка через LLM и записать в Neo4j.
    Сущности: Person, Project, Organization, Tool, Decision
    """
    prompt = f"""Извлеки именованные сущности из текста. Верни ТОЛЬКО JSON, без пояснений.

Формат:
{{
  "persons": ["имя1", "имя2"],
  "projects": ["проект1"],
  "organizations": ["орг1"],
  "tools": ["инструмент1"],
  "decisions": ["ключевое решение (кратко, до 60 символов)"]
}}

Текст:
{chunk['raw_text'][:800]}"""

    try:
        resp = http_request(
            f'{LITELLM_BASE}/v1/chat/completions',
            method='POST',
            headers={'Authorization': f'Bearer {LITELLM_KEY}'},
            data={
                'model': 'anthropic/claude-sonnet-4-5',
                'messages': [{'role': 'user', 'content': prompt}],
                'max_tokens': 300,
                'temperature': 0,
            }
        )
        raw = resp['choices'][0]['message']['content'].strip()
        # Убираем markdown блок если есть
        if '```' in raw:
            raw = raw.split('```')[1]
            if raw.startswith('json'):
                raw = raw[4:]
        entities = json.loads(raw)
    except Exception as e:
        print(f'    ⚠ entity extraction failed: {e}', file=sys.stderr)
        return

    # Записываем в Neo4j
    chunk_node_id = f'{file_path}:{chunk["chunk_id"]}'
    try:
        # Создаём Chunk узел
        neo4j_query(
            'MERGE (c:Chunk {id: $id}) SET c.file=$file, c.section=$section, c.parent=$parent, c.text=$text',
            {'id': chunk_node_id, 'file': file_path, 'section': chunk['section'],
             'parent': chunk['parent_section'], 'text': chunk['raw_text'][:500]}
        )
        # Связываем сущности
        for person in entities.get('persons', []):
            if person and len(person) > 1:
                neo4j_query(
                    'MERGE (p:Person {name: $name}) MERGE (c:Chunk {id: $cid}) MERGE (c)-[:MENTIONS]->(p)',
                    {'name': person, 'cid': chunk_node_id}
                )
        for project in entities.get('projects', []):
            if project and len(project) > 1:
                neo4j_query(
                    'MERGE (p:Project {name: $name}) MERGE (c:Chunk {id: $cid}) MERGE (c)-[:MENTIONS]->(p)',
                    {'name': project, 'cid': chunk_node_id}
                )
        for org in entities.get('organizations', []):
            if org and len(org) > 1:
                neo4j_query(
                    'MERGE (o:Organization {name: $name}) MERGE (c:Chunk {id: $cid}) MERGE (c)-[:MENTIONS]->(o)',
                    {'name': org, 'cid': chunk_node_id}
                )
        for tool in entities.get('tools', []):
            if tool and len(tool) > 1:
                neo4j_query(
                    'MERGE (t:Tool {name: $name}) MERGE (c:Chunk {id: $cid}) MERGE (c)-[:MENTIONS]->(t)',
                    {'name': tool, 'cid': chunk_node_id}
                )
        for decision in entities.get('decisions', []):
            if decision and len(decision) > 5:
                neo4j_query(
                    'MERGE (d:Decision {text: $text}) MERGE (c:Chunk {id: $cid}) MERGE (c)-[:CONTAINS]->(d)',
                    {'text': decision, 'cid': chunk_node_id}
                )
    except Exception as e:
        print(f'    ⚠ neo4j write failed: {e}', file=sys.stderr)


def index_session_message(session_id, timestamp, role, text):
    """Индексировать сообщение из session history"""
    # Уникальный ID из session + timestamp + role
    unique_key = f"{session_id}:{timestamp}:{role}"
    point_id = int(hashlib.md5(unique_key.encode()).hexdigest()[:8], 16)
    
    metadata = {
        "type": "session",
        "session_id": session_id,
        "timestamp": timestamp,
        "role": role,
        "date": datetime.fromtimestamp(timestamp / 1000).isoformat()
    }
    
    return index_point(point_id, text, metadata)

def get_himalaya_emails(account):
    """Получить письма из himalaya"""
    result = subprocess.run(
        ['himalaya', 'envelope', 'list', '-a', account, '--output', 'json'],
        capture_output=True,
        text=True,
        env={**os.environ, 'PATH': f"{os.environ['HOME']}/.local/bin:{os.environ['PATH']}"}
    )
    
    if result.returncode != 0:
        print(f"Error getting emails from {account}: {result.stderr}", file=sys.stderr)
        return []
    
    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError:
        return []

def get_collection_info():
    """Get collection statistics"""
    try:
        result = http_request(
            f"{QDRANT_URL}/collections/{COLLECTION}",
            headers={"api-key": QDRANT_KEY}
        )
        return result.get('result', {})
    except Exception as e:
        return {"error": str(e)}

def main():
    if len(sys.argv) < 2:
        print("Usage: qdrant_indexer.py [status|index-emails|search|index-memory|index-sessions|index-events]")
        sys.exit(1)
    
    command = sys.argv[1]
    
    if command == "status":
        # Show collection statistics
        info = get_collection_info()
        if 'error' in info:
            print(f"Error: {info['error']}", file=sys.stderr)
            sys.exit(1)
        
        print(f"Collection: {COLLECTION}")
        print(f"Points count: {info.get('points_count', 0)}")
        print(f"Indexed segments: {info.get('segments_count', 0)}")
        print(f"Vector size: {info.get('config', {}).get('params', {}).get('vectors', {}).get('size', 'unknown')}")
        print(f"Distance: {info.get('config', {}).get('params', {}).get('vectors', {}).get('distance', 'unknown')}")
        
        # Try to estimate breakdown by type
        print("\nEstimated breakdown (based on ID patterns):")
        # This is approximate - would need to actually query
        print("  Run search queries to explore indexed content")
    
    elif command == "index-emails":
        # Индексируем все почтовые ящики
        accounts = ['dparmeev', 'spam', 'contact', 'contact-lumines']
        total = 0
        
        for account in accounts:
            print(f"Indexing {account}...", file=sys.stderr)
            emails = get_himalaya_emails(account)
            
            for email in emails[:50]:  # Первые 50 писем каждого аккаунта
                try:
                    # Получаем полное письмо
                    result = subprocess.run(
                        ['himalaya', 'message', 'read', '-a', account, str(email.get('id', ''))],
                        capture_output=True,
                        text=True,
                        env={**os.environ, 'PATH': f"{os.environ['HOME']}/.local/bin:{os.environ['PATH']}"}
                    )
                    
                    if result.returncode == 0:
                        body = result.stdout[:2000]  # Первые 2000 символов
                        
                        index_email(
                            email_id=str(email.get('id')),
                            account=account,
                            subject=email.get('subject', ''),
                            from_addr=email.get('from', ''),
                            date=email.get('date', ''),
                            body=body
                        )
                        total += 1
                        print(f"  ✓ {email.get('subject', 'No subject')}", file=sys.stderr)
                except Exception as e:
                    print(f"  ✗ Failed: {e}", file=sys.stderr)
        
        print(f"\nIndexed {total} emails", file=sys.stderr)
    
    elif command == "search":
        # Parse args: search [--type TYPE] [--account ACCOUNT] [--limit N] query
        import argparse
        parser = argparse.ArgumentParser()
        parser.add_argument('--type', help='Filter by type (email/memory/session)')
        parser.add_argument('--account', help='Filter by email account')
        parser.add_argument('--limit', type=int, default=5, help='Max results')
        parser.add_argument('query', nargs='+', help='Search query')
        
        args = parser.parse_args(sys.argv[2:])
        query = " ".join(args.query)
        
        results = search(query, limit=args.limit, filter_type=args.type, account=args.account)

        for r in results:
            score = r.get('score', 0)
            payload = r.get('payload', {})
            file = payload.get('file', '')
            section = payload.get('section', '')
            text_snippet = payload.get('text', '')[:200].replace('\n', ' ')
            print(f"[{score:.3f}] {file} › {section}")
            print(f"  {text_snippet}")
            print()
    
    elif command == "index-memory":
        # Индексируем файлы памяти — чанками по секциям
        neo4j_flag = '--neo4j' in sys.argv
        workspace = Path.home() / ".openclaw" / "workspace"
        memory_files = (
            list(workspace.glob("memory/*.md")) +
            list(workspace.glob("memory/projects/*.md")) +
            list(workspace.glob("memory/people/*.md")) +
            list(workspace.glob("memory/tools/*.md")) +
            list(workspace.glob("memory/rules/*.md")) +
            [workspace / "MEMORY.md"]
        )

        total_files = 0
        total_chunks = 0
        for file_path in memory_files:
            if not file_path.exists():
                continue
            try:
                content = file_path.read_text()
                rel_path = str(file_path.relative_to(workspace))
                chunks = chunk_markdown(content, rel_path)

                # Вычисляем все point_id для файла
                chunk_map = {
                    int(hashlib.md5(f'{rel_path}:{c["chunk_id"]}'.encode()).hexdigest()[:8], 16): c
                    for c in chunks
                }
                # Батч-проверка — какие уже есть в Qdrant
                existing = points_exist(list(chunk_map.keys()))
                new_count = len(chunk_map) - len(existing)
                print(f'📄 {file_path.name} → {len(chunks)} chunks ({len(existing)} skip, {new_count} new)', file=sys.stderr)

                for point_id, chunk in chunk_map.items():
                    if point_id in existing:
                        continue  # уже проиндексирован — пропускаем
                    try:
                        metadata = {
                            'type': 'memory',
                            'file': rel_path,
                            'section': chunk['section'],
                            'parent_section': chunk['parent_section'],
                            'chunk_id': chunk['chunk_id'],
                        }
                        index_point(point_id, chunk['text'], metadata)

                        if neo4j_flag:
                            extract_and_index_entities(chunk, rel_path)

                        total_chunks += 1
                        print(f'  ✓ {chunk["section"][:60]}', file=sys.stderr)
                    except Exception as e:
                        print(f'  ✗ {chunk["section"][:40]}: {e}', file=sys.stderr)

                total_files += 1
            except Exception as e:
                print(f'✗ {file_path.name}: {e}', file=sys.stderr)

        print(f'\n✅ Indexed {total_chunks} chunks from {total_files} files', file=sys.stderr)
        if not neo4j_flag:
            print('💡 Add --neo4j to also extract entities into Neo4j graph', file=sys.stderr)
    
    elif command == "index-memory-chunked":
        # Индексируем файлы памяти с чанкингом по секциям + Neo4j entities
        neo4j_flag = '--neo4j' in sys.argv
        workspace = Path.home() / ".openclaw" / "workspace"
        memory_files = (
            list(workspace.glob("memory/*.md")) +
            list(workspace.glob("memory/projects/*.md")) +
            [workspace / "MEMORY.md"]
        )

        total_files = 0
        total_chunks = 0
        for file_path in memory_files:
            if not file_path.exists():
                continue
            try:
                content = file_path.read_text()
                rel_path = str(file_path.relative_to(workspace))
                chunks = chunk_markdown(content, rel_path)

                print(f'📄 {file_path.name} → {len(chunks)} chunks', file=sys.stderr)

                for i, chunk in enumerate(chunks):
                    try:
                        # Уникальный ID для Qdrant
                        point_id = int(hashlib.md5(
                            f'{rel_path}:{chunk["chunk_id"]}'.encode()
                        ).hexdigest()[:8], 16)

                        metadata = {
                            'type': 'memory',
                            'file': rel_path,
                            'section': chunk['section'],
                            'parent_section': chunk['parent_section'],
                            'chunk_id': chunk['chunk_id'],
                        }
                        index_point(point_id, chunk['text'], metadata)

                        # Neo4j (опционально, дороже — LLM вызов на каждый чанк)
                        if neo4j_flag:
                            extract_and_index_entities(chunk, rel_path)

                        total_chunks += 1
                        print(f'  ✓ [{i+1}/{len(chunks)}] {chunk["section"][:50]}', file=sys.stderr)
                    except Exception as e:
                        print(f'  ✗ chunk {i}: {e}', file=sys.stderr)

                total_files += 1
            except Exception as e:
                print(f'✗ {file_path.name}: {e}', file=sys.stderr)

        print(f'\n✅ Indexed {total_chunks} chunks from {total_files} files', file=sys.stderr)
        if not neo4j_flag:
            print('💡 Add --neo4j to also extract entities into Neo4j graph', file=sys.stderr)

    elif command == "index-sessions":
        # Индексируем историю сессий
        sessions_dir = Path.home() / ".openclaw" / "agents" / "main" / "sessions"
        
        total = 0
        for jsonl_file in sessions_dir.glob("*.jsonl"):
            # Пропускаем lock файлы
            if jsonl_file.suffix == ".lock":
                continue
            
            session_id = jsonl_file.stem
            print(f"Indexing session {session_id[:8]}...", file=sys.stderr)
            
            try:
                with open(jsonl_file, 'r') as f:
                    for line_num, line in enumerate(f, 1):
                        try:
                            record = json.loads(line)
                            
                            # Фильтруем только messages
                            if record.get('type') != 'message':
                                continue
                            
                            message = record.get('message', {})
                            
                            # Извлекаем текст из content
                            role = message.get('role', 'unknown')
                            timestamp = message.get('timestamp', 0)
                            content_items = message.get('content', [])
                            
                            # Собираем весь текст из content
                            texts = []
                            for item in content_items:
                                if isinstance(item, dict):
                                    if item.get('type') == 'text':
                                        texts.append(item.get('text', ''))
                                    elif item.get('type') == 'thinking':
                                        # Thinking тоже индексируем (reasoning!)
                                        texts.append(f"[thinking] {item.get('thinking', '')}")
                            
                            text = "\n".join(texts).strip()
                            
                            # Индексируем если есть текст
                            if text and len(text) > 20:  # Минимум 20 символов
                                index_session_message(session_id, timestamp, role, text)
                                total += 1
                        
                        except json.JSONDecodeError:
                            print(f"  ✗ Line {line_num}: Invalid JSON", file=sys.stderr)
                        except Exception as e:
                            print(f"  ✗ Line {line_num}: {e}", file=sys.stderr)
                
                print(f"  ✓ {jsonl_file.name}", file=sys.stderr)
            
            except Exception as e:
                print(f"  ✗ {jsonl_file.name}: {e}", file=sys.stderr)
        
        print(f"\nIndexed {total} session messages", file=sys.stderr)


    elif command == "index-events":
        # Index event logs
        session_id = sys.argv[2] if len(sys.argv) > 2 else None
        index_events(session_id)

if __name__ == "__main__":
    main()

def index_events(session_id=None):
    """Index event logs in Qdrant for semantic search"""
    from pathlib import Path
    events_dir = Path.home() / ".openclaw" / "workspace" / "memory" / "events"
    
    if not events_dir.exists():
        print("No events directory", file=sys.stderr)
        return
    
    total = 0
    session_files = [events_dir / f"{session_id}.jsonl"] if session_id else events_dir.glob("*.jsonl")
    
    for jsonl_file in session_files:
        if not jsonl_file.exists():
            continue
            
        session = jsonl_file.stem
        print(f"Indexing events: {session}...", file=sys.stderr)
        
        with open(jsonl_file, 'r') as f:
            for line in f:
                try:
                    event = json.loads(line.strip())
                    
                    # Build searchable text
                    etype = event.get('type', '')
                    data = event.get('data', {})
                    timestamp = event.get('timestamp', '')
                    
                    text_parts = [f"Event: {etype}"]
                    for key, value in data.items():
                        text_parts.append(f"{key}: {value}")
                    
                    text = "\n".join(text_parts)
                    
                    # Generate unique ID
                    event_id = hashlib.md5(f"{session}:{timestamp}".encode()).hexdigest()[:8]
                    point_id = int(event_id, 16)
                    
                    # Index
                    index_point(point_id, text, {
                        "type": "event",
                        "session_id": session,
                        "event_type": etype,
                        "timestamp": timestamp,
                        "data": data
                    })
                    
                    total += 1
                    
                except Exception as e:
                    print(f"Error indexing event: {e}", file=sys.stderr)
    
    print(f"\nIndexed {total} events", file=sys.stderr)
