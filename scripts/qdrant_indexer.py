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

# Конфиг из переменных окружения
LITELLM_BASE = os.getenv('LITELLM_BASE_URL', 'https://litellm.jakeberrimor.com')
LITELLM_KEY = os.getenv('LITELLM_API_KEY')
QDRANT_URL = os.getenv('QDRANT_URL', 'https://qdrant.jakeberrimor.com')
QDRANT_KEY = os.getenv('QDRANT_API_KEY', 'sk-1234')
COLLECTION = os.getenv('QDRANT_COLLECTION', 'arkasha')
EMBEDDING_MODEL = os.getenv('EMBEDDING_MODEL', 'vl-Qwen/Qwen3-Embedding-0.6B')

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
        
        print(json.dumps(results, indent=2, ensure_ascii=False))
    
    elif command == "index-memory":
        # Индексируем файлы памяти
        workspace = Path.home() / ".openclaw" / "workspace"
        memory_files = (
            list(workspace.glob("memory/*.md")) + 
            list(workspace.glob("memory/projects/*.md")) +
            [workspace / "MEMORY.md"]
        )
        
        total = 0
        for file_path in memory_files:
            if file_path.exists():
                try:
                    content = file_path.read_text()
                    index_memory(str(file_path.relative_to(workspace)), content)
                    print(f"✓ {file_path.name}", file=sys.stderr)
                    total += 1
                except Exception as e:
                    print(f"✗ {file_path.name}: {e}", file=sys.stderr)
        
        print(f"\nIndexed {total} memory files", file=sys.stderr)
    
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
