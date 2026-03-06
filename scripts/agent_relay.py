"""
Agent-to-Agent Relay via Redis Pub/Sub

Использование:
  Отправить сообщение:         python3 agent_relay.py send <to_agent> <message>
  Получить новые:              python3 agent_relay.py recv <my_agent>
  Слушать в реальном времени:  python3 agent_relay.py listen <my_agent>

Агенты: arkasha, friend (или любое имя)
"""
import sys
import json
import redis
import time

REDIS_URL = "redis://default:q2bYD3MS4sH4mw0G0yis@80.87.197.0:6379"
r = redis.from_url(REDIS_URL, decode_responses=True)

def send(to_agent: str, message: str, from_agent: str = "arkasha"):
    channel = f"agent-relay:{to_agent}"
    payload = json.dumps({
        "from": from_agent,
        "to": to_agent,
        "message": message,
        "ts": time.time()
    })
    r.publish(channel, payload)
    # Также сохраняем в list для получения offline-сообщений
    r.rpush(f"agent-inbox:{to_agent}", payload)
    print(f"✓ Sent to {to_agent}: {message}")

def recv(my_agent: str):
    """Получить все накопившиеся сообщения из inbox"""
    key = f"agent-inbox:{my_agent}"
    messages = []
    while True:
        msg = r.lpop(key)
        if not msg:
            break
        messages.append(json.loads(msg))
    if not messages:
        print("No new messages")
    for m in messages:
        print(f"[{m['from']}]: {m['message']}")
    return messages

def listen(my_agent: str):
    """Слушать новые сообщения в реальном времени"""
    channel = f"agent-relay:{my_agent}"
    pubsub = r.pubsub()
    pubsub.subscribe(channel)
    print(f"Listening on channel: {channel}")
    for msg in pubsub.listen():
        if msg["type"] == "message":
            data = json.loads(msg["data"])
            print(f"[{data['from']}]: {data['message']}")

if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "help"
    if cmd == "send" and len(sys.argv) >= 4:
        send(sys.argv[2], sys.argv[3])
    elif cmd == "recv" and len(sys.argv) >= 3:
        recv(sys.argv[2])
    elif cmd == "listen" and len(sys.argv) >= 3:
        listen(sys.argv[2])
    else:
        print(__doc__)
