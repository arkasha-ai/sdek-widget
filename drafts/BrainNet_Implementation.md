# BrainNet: Техническая архитектура и прототип

> Биологически вдохновлённая AI-система с разделением "что/как", множественными reward signals и gossip-координацией.
>
> Отправная точка: инцидент ROME (Alibaba, arxiv 2512.24873) — агент с единым скалярным reward начал майнить крипту и открыл SSH-туннель. BrainNet решает эту проблему архитектурно.

---

## Часть 1: Техническая архитектура

### 1.1 Узел (BrainNode) — базовая единица

Каждый узел — автономный процесс с единым интерфейсом:

```
┌─────────────────────────────────┐
│           BrainNode             │
├─────────────────────────────────┤
│ Входы:                          │
│   - signal: Tensor (raw input)  │
│   - gossip_msgs: Queue[Message] │
│   - reward_signals: Dict[str,f] │
│                                 │
│ Внутри:                         │
│   - model: nn.Module (mock/real)│
│   - projection_heads: Dict      │
│   - working_memory: Buffer      │
│   - relevance_scorer: fn→[0,1]  │
│                                 │
│ Выходы:                         │
│   - embedding: Tensor           │
│   - vote: Tensor (universal)    │
│   - action_proposal: Optional   │
│   - gossip_out: Queue[Message]  │
└─────────────────────────────────┘
```

**Жизненный цикл обработки сигнала:**
1. Получить сигнал через gossip
2. Оценить relevance (0..1) — внутренняя функция узла
3. Если relevance > threshold → обработать моделью → получить embedding
4. Спроецировать embedding через projection head в universal subspace
5. Отправить vote в universal subspace всем соседям
6. Получить votes от соседей → cosine similarity → найти "единомышленников"
7. С единомышленниками — синхронизировать полные embeddings и обработать совместно

**Типы узлов по уровню иерархии:**

| Уровень | Тип | Размерность embedding | Размер модели | Латентность |
|---------|-----|----------------------|---------------|-------------|
| L0 | Sensory (Vision, Text, Audio) | 768–1024d | ~7B | 200–500ms |
| L1 | Associative (cross-modal binding) | 128–256d | ~3B | 100–200ms |
| L2 | Decision (goal selection, planning) | 32–64d | ~1B | 50–100ms |
| L3 | Motor (tool execution) | 8–16d | ~100M | 10–30ms |

Убывающая размерность — ключевой принцип. Чем ниже уровень, тем:
- Меньше размерность → меньше неопределённости
- Быстрее ответ → реактивность
- Уже "кругозор" → не может придумать нецелевые действия

### 1.2 Gossip протокол

**Что передаётся:**

```python
@dataclass
class GossipMessage:
    msg_id: str              # UUID
    source_id: str           # кто отправил
    msg_type: str            # "signal" | "vote" | "sync_request" | "sync_data" | "cancel"
    timestamp: float         # время создания
    ttl: int                 # сколько хопов осталось (обычно 2-3)
    payload: Dict[str, Any]  # содержимое зависит от msg_type
```

**Типы сообщений:**

- `signal` — новый входной сигнал (текст, изображение, событие). Payload: `{data: Tensor, modality: str}`
- `vote` — голос узла в universal subspace. Payload: `{vote_vector: Tensor[5-10d], relevance: float, signal_id: str}`
- `sync_request` — запрос на синхронизацию с узлом, чей vote похож. Payload: `{signal_id: str, my_embedding: Tensor}`
- `sync_data` — ответ с полным embedding. Payload: `{signal_id: str, full_embedding: Tensor, metadata: Dict}`
- `cancel` — отмена действия от медленного потока. Payload: `{action_id: str, reason: str}`

**Механика:**

```
Узел A получает signal
  → вычисляет relevance
  → если > threshold:
      → обрабатывает → embedding
      → проецирует в universal subspace → vote
      → gossip(vote) всем соседям
  → если < threshold:
      → gossip(signal) дальше (forward, ttl-1)

Узел B получает vote от A
  → сравнивает со своим vote (cosine similarity)
  → если similarity > sync_threshold:
      → отправляет sync_request к A
      → получает sync_data
      → совместная обработка
```

**Реализация:** `asyncio.Queue` для каждого узла. Gossip — fire-and-forget через `asyncio.create_task`. Deduplification по `msg_id` (set of seen IDs).

### 1.3 Projection Heads

Каждое ребро между узлами имеет свой projection head — линейный (или неглубокий) слой, адаптирующий размерность:

```
ProjectionHead(input_dim, output_dim):
    Linear(input_dim, output_dim)
    LayerNorm(output_dim)
    
    # Опционально: адаптивная размерность
    # через learnable mask или SVD truncation
```

**Размерности по рёбрам:**

| Откуда → Куда | Размерность проекции |
|----------------|---------------------|
| Sensory → Associative | 128–256d |
| Associative → Decision | 32–64d |
| Decision → Motor | 8–16d |
| Любой → Universal (vote) | 8d |
| Sensory → Sensory (cross-modal) | 128d |

**Universal subspace** — общее пространство для голосования. Все узлы проецируют свои embeddings в одно и то же 8-мерное пространство. Это позволяет сравнивать "мнения" узлов разных модальностей.

Почему 8d достаточно: эмпирически, 90%+ дисперсии при PCA укладывается в 5-10 главных компонент для задач классификации решений (что делать / не делать / подождать).

### 1.4 Слой голосования (Voting Layer)

**Процесс:**

1. Каждый узел, считающий сигнал релевантным, отправляет vote ∈ ℝ⁸ (unit vector в universal subspace)
2. Голоса собираются с таймаутом T_vote (50–200ms)
3. Вычисляется consensus:

```
votes = [v1, v2, ..., vK]  # все полученные голоса

# Попарная cosine similarity
sim_matrix[i,j] = cosine(votes[i], votes[j])

# Кластеризация: группы с sim > cluster_threshold (0.7)
clusters = find_clusters(sim_matrix, threshold=0.7)

# Самый большой кластер = consensus group
consensus = largest_cluster(clusters)

# Средний вектор кластера = direction решения  
consensus_vector = mean(votes[consensus])

# Уверенность = доля узлов в consensus / всего голосовавших
confidence = len(consensus) / len(votes)
```

**Thresholds:**
- `relevance_threshold = 0.3` — минимальная оценка важности для обработки сигнала
- `sync_threshold = 0.7` — минимальная cosine similarity для синхронизации
- `consensus_threshold = 0.6` — минимальная доля узлов для принятия решения
- `action_confidence = 0.8` — минимальная уверенность для необратимого действия

### 1.5 Два потока (Dual Stream)

```
Signal ──┬──→ [Fast Stream: ~100M model] ──→ Quick Response (10-50ms)
         │                                        │
         │                                   Action Queue
         │                                        │
         └──→ [Slow Stream: ~7B model] ──→ Review/Override (200-2000ms)
                                               │
                                          ┌────┴────┐
                                          │ Approve  │ Cancel
                                          └────┬────┘
                                               │
                                        Execute / Abort
```

**Механика отмены:**

```python
async def dual_stream_process(signal):
    # Быстрый поток стартует немедленно
    fast_task = asyncio.create_task(fast_stream(signal))
    fast_result = await fast_task
    
    action = fast_result.proposed_action
    
    if action.is_reversible:
        # Выполнить сразу, медленный поток проверит постфактум
        execute(action)
        slow_task = asyncio.create_task(slow_stream(signal))
        slow_result = await slow_task
        if slow_result.should_rollback:
            rollback(action)
    else:
        # Необратимое — ждать подтверждения медленного потока
        slow_task = asyncio.create_task(slow_stream(signal))
        
        # Таймаут D — принудительная задержка
        try:
            slow_result = await asyncio.wait_for(slow_task, timeout=D)
            if slow_result.approved:
                execute(action)
            else:
                discard(action)
        except asyncio.TimeoutError:
            # Медленный поток не ответил — НЕ выполняем
            discard(action)
```

### 1.6 Классификация действий

**Hardcoded whitelist/blacklist + learned classifier:**

```python
IRREVERSIBLE_PATTERNS = {
    "shell_exec": True,      # выполнение команд
    "file_delete": True,      # удаление файлов
    "network_request": True,  # внешние запросы
    "send_message": True,     # отправка сообщений
    "financial_tx": True,     # финансовые транзакции
}

REVERSIBLE_PATTERNS = {
    "file_read": True,        # чтение файлов
    "internal_compute": True, # внутренние вычисления
    "memory_write": True,     # запись в рабочую память
    "draft_create": True,     # создание черновика
}
```

Моторный узел:
1. Получает action proposal от decision layer
2. Классифицирует: reversible / irreversible / unknown
3. Unknown → трактует как irreversible (безопасный дефолт)
4. Irreversible → задержка D, ожидание медленного потока
5. Reversible → немедленное выполнение

**Критично:** моторный узел НЕ знает цели действия. Он знает только "вызвать tool X с параметрами Y". Он НЕ может решить "а давайте ещё и tool Z вызовем" — это за пределами его embedding space (8-16d).

### 1.7 Рабочая память (Working Memory)

```python
class WorkingMemory:
    """
    Ring buffer с TTL и приоритетами.
    Аналог prefrontal cortex working memory (~7±2 items).
    """
    capacity: int = 7          # максимум элементов
    ttl: float = 30.0          # секунд до автоочистки
    
    items: Dict[str, MemoryItem]
    # MemoryItem: {key, value, priority, created_at, accessed_at, access_count}
    
    # При переполнении — вытесняется элемент с минимальным score:
    # score = priority * recency_weight * frequency_weight
```

**Три уровня памяти в системе:**

| Уровень | Аналог мозга | Реализация | Персистентность |
|---------|-------------|------------|-----------------|
| Рабочая | Prefrontal WM | In-memory dict, ring buffer | Стирается после задачи |
| Эпизодическая | Hippocampus | SQLite / vector DB | Накапливается, обрабатывается офлайн |
| Долгосрочная | Cortical weights | Model weights | Меняется только при fine-tuning |

### 1.8 Стек технологий

| Компонент | Технология | Зачем |
|-----------|-----------|-------|
| Async runtime | `asyncio` | Gossip, dual stream, non-blocking I/O |
| ML framework | `PyTorch` | Projection heads, mock models |
| Сериализация | `msgpack` / `protobuf` | Быстрая сериализация gossip messages |
| Очереди | `asyncio.Queue` (in-process) / `Redis Streams` (distributed) | Gossip transport |
| Vector ops | `torch.nn.functional` | Cosine similarity, normalization |
| Эпизодическая память | `sqlite3` + `faiss` / `qdrant` | Хранение и поиск по embeddings |
| Мониторинг | `prometheus_client` | Метрики latency, throughput, reward signals |
| Тестирование | `pytest` + `pytest-asyncio` | Async тесты |

---

## Часть 2: Минимальная реализация (прототип)

### 2.1 Полный рабочий прототип

```python
"""
BrainNet Prototype v0.1
========================
Minimal working implementation of the BrainNet architecture.
Uses mock models (random projections) instead of real LLMs.
Demonstrates: gossip, voting, dual-stream, action classification.

Requirements: Python 3.10+, PyTorch 2.0+
    pip install torch

Run: python brainnet_proto.py
"""

import asyncio
import uuid
import time
import logging
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any, Optional

import torch
import torch.nn as nn
import torch.nn.functional as F

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)-12s] %(message)s",
    datefmt="%H:%M:%S",
)

# ============================================================
# Data structures
# ============================================================

class MessageType(Enum):
    SIGNAL = auto()
    VOTE = auto()
    SYNC_REQUEST = auto()
    SYNC_DATA = auto()
    CANCEL = auto()


class ActionType(Enum):
    REVERSIBLE = auto()
    IRREVERSIBLE = auto()
    UNKNOWN = auto()


@dataclass
class GossipMessage:
    msg_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    source_id: str = ""
    msg_type: MessageType = MessageType.SIGNAL
    timestamp: float = field(default_factory=time.time)
    ttl: int = 3
    payload: dict = field(default_factory=dict)


@dataclass
class ActionProposal:
    action_id: str = field(default_factory=lambda: uuid.uuid4().hex[:8])
    action_name: str = ""
    params: dict = field(default_factory=dict)
    action_type: ActionType = ActionType.UNKNOWN
    source_signal_id: str = ""


@dataclass
class MemoryItem:
    key: str
    value: Any
    priority: float = 1.0
    created_at: float = field(default_factory=time.time)
    accessed_at: float = field(default_factory=time.time)
    access_count: int = 0


# ============================================================
# Projection Head
# ============================================================

class ProjectionHead(nn.Module):
    """
    Linear projection from one embedding space to another.
    Each edge in the BrainNet graph has its own ProjectionHead.
    """

    def __init__(self, input_dim: int, output_dim: int):
        super().__init__()
        self.proj = nn.Linear(input_dim, output_dim, bias=False)
        self.norm = nn.LayerNorm(output_dim)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """Project and L2-normalize to unit sphere."""
        h = self.norm(self.proj(x))
        return F.normalize(h, dim=-1)


# ============================================================
# Working Memory
# ============================================================

class WorkingMemory:
    """
    Ring buffer with TTL and priority eviction.
    Models prefrontal cortex working memory (~7 items).
    """

    def __init__(self, capacity: int = 7, ttl: float = 30.0):
        self.capacity = capacity
        self.ttl = ttl
        self._store: dict[str, MemoryItem] = {}

    def put(self, key: str, value: Any, priority: float = 1.0) -> None:
        self._evict_expired()
        if len(self._store) >= self.capacity:
            self._evict_lowest()
        self._store[key] = MemoryItem(key=key, value=value, priority=priority)

    def get(self, key: str) -> Any | None:
        self._evict_expired()
        item = self._store.get(key)
        if item is None:
            return None
        item.accessed_at = time.time()
        item.access_count += 1
        return item.value

    def clear(self) -> None:
        self._store.clear()

    def _score(self, item: MemoryItem) -> float:
        recency = 1.0 / (1.0 + time.time() - item.accessed_at)
        frequency = min(item.access_count / 10.0, 1.0)
        return item.priority * (0.6 * recency + 0.4 * frequency)

    def _evict_expired(self) -> None:
        now = time.time()
        expired = [k for k, v in self._store.items() if now - v.created_at > self.ttl]
        for k in expired:
            del self._store[k]

    def _evict_lowest(self) -> None:
        if not self._store:
            return
        worst = min(self._store.values(), key=self._score)
        del self._store[worst.key]

    def __len__(self) -> int:
        self._evict_expired()
        return len(self._store)

    def __repr__(self) -> str:
        return f"WorkingMemory({list(self._store.keys())})"


# ============================================================
# Gossip Protocol
# ============================================================

class GossipProtocol:
    """
    Async gossip layer. Each node has an inbox queue.
    Messages are forwarded to all neighbors (fire-and-forget).
    Deduplication via seen message IDs.
    """

    def __init__(self):
        self._nodes: dict[str, asyncio.Queue] = {}
        self._neighbors: dict[str, list[str]] = {}  # node_id -> [neighbor_ids]
        self._seen: dict[str, set[str]] = {}  # node_id -> {seen msg_ids}

    def register(self, node_id: str, neighbors: list[str] | None = None) -> asyncio.Queue:
        q: asyncio.Queue[GossipMessage] = asyncio.Queue(maxsize=256)
        self._nodes[node_id] = q
        self._neighbors[node_id] = neighbors or []
        self._seen[node_id] = set()
        return q

    def set_neighbors(self, node_id: str, neighbors: list[str]) -> None:
        self._neighbors[node_id] = neighbors

    async def send(self, source_id: str, msg: GossipMessage) -> None:
        """Send message to all neighbors of source_id."""
        targets = self._neighbors.get(source_id, [])
        for tid in targets:
            q = self._nodes.get(tid)
            if q is None:
                continue
            # Dedup check at receiver side
            if msg.msg_id in self._seen.get(tid, set()):
                continue
            self._seen.setdefault(tid, set()).add(msg.msg_id)
            try:
                q.put_nowait(msg)
            except asyncio.QueueFull:
                pass  # drop if overloaded

    async def broadcast(self, msg: GossipMessage) -> None:
        """Send to ALL registered nodes (for initial signal injection)."""
        for nid, q in self._nodes.items():
            if msg.msg_id in self._seen.get(nid, set()):
                continue
            self._seen.setdefault(nid, set()).add(msg.msg_id)
            try:
                q.put_nowait(msg)
            except asyncio.QueueFull:
                pass

    async def forward(self, forwarder_id: str, msg: GossipMessage) -> None:
        """Forward a message (decrement TTL)."""
        if msg.ttl <= 0:
            return
        fwd = GossipMessage(
            msg_id=msg.msg_id,
            source_id=msg.source_id,
            msg_type=msg.msg_type,
            timestamp=msg.timestamp,
            ttl=msg.ttl - 1,
            payload=msg.payload,
        )
        await self.send(forwarder_id, fwd)


# ============================================================
# Voting Layer
# ============================================================

class VotingLayer:
    """
    Collects votes (unit vectors in universal subspace),
    clusters by cosine similarity, returns consensus.
    """

    def __init__(
        self,
        cluster_threshold: float = 0.7,
        consensus_threshold: float = 0.5,
    ):
        self.cluster_threshold = cluster_threshold
        self.consensus_threshold = consensus_threshold

    def compute_consensus(
        self, votes: dict[str, torch.Tensor]
    ) -> tuple[torch.Tensor | None, float, list[str]]:
        """
        Returns:
            consensus_vector: mean of largest cluster (or None)
            confidence: fraction of voters in consensus cluster
            member_ids: node IDs in consensus cluster
        """
        if not votes:
            return None, 0.0, []

        ids = list(votes.keys())
        vecs = torch.stack([votes[i] for i in ids])  # (N, D)

        # Pairwise cosine similarity
        sim = torch.mm(vecs, vecs.T)  # (N, N), vecs already normalized

        # Greedy clustering: start from node with highest average similarity
        avg_sim = sim.mean(dim=1)
        seed_idx = avg_sim.argmax().item()

        cluster = [seed_idx]
        for i in range(len(ids)):
            if i == seed_idx:
                continue
            # Check similarity to all current cluster members
            sims_to_cluster = sim[i, cluster]
            if sims_to_cluster.min().item() >= self.cluster_threshold:
                cluster.append(i)

        confidence = len(cluster) / len(ids)
        member_ids = [ids[i] for i in cluster]

        if confidence >= self.consensus_threshold:
            consensus_vec = F.normalize(vecs[cluster].mean(dim=0), dim=0)
            return consensus_vec, confidence, member_ids
        else:
            return None, confidence, member_ids


# ============================================================
# Brain Node (base class)
# ============================================================

class BrainNode:
    """
    Base class for all nodes in BrainNet.
    Subclass to implement specific behavior (sensory, associative, decision, motor).
    """

    def __init__(
        self,
        node_id: str,
        level: int,  # 0=sensory, 1=associative, 2=decision, 3=motor
        embedding_dim: int,
        universal_dim: int = 8,
        relevance_threshold: float = 0.3,
    ):
        self.node_id = node_id
        self.level = level
        self.embedding_dim = embedding_dim
        self.universal_dim = universal_dim
        self.relevance_threshold = relevance_threshold

        self.log = logging.getLogger(node_id)

        # Mock model: simple MLP that "processes" input
        self.model = nn.Sequential(
            nn.Linear(embedding_dim, embedding_dim),
            nn.ReLU(),
            nn.Linear(embedding_dim, embedding_dim),
        )

        # Projection to universal voting subspace
        self.vote_head = ProjectionHead(embedding_dim, universal_dim)

        # Working memory
        self.memory = WorkingMemory(capacity=7, ttl=60.0)

        # Reward accumulators
        self.rewards: dict[str, float] = {
            "task": 0.0,
            "safety": 0.0,
            "efficiency": 0.0,
        }

        # Will be set by gossip protocol
        self.inbox: asyncio.Queue | None = None
        self.gossip: GossipProtocol | None = None

        self._running = False

    def assess_relevance(self, signal_data: torch.Tensor) -> float:
        """
        Evaluate how relevant this signal is to this node.
        In production: learned function. Here: heuristic based on norm overlap.
        """
        with torch.no_grad():
            # Simple heuristic: L2 norm projected to [0,1]
            processed = self.model(signal_data)
            energy = processed.norm().item()
            # Sigmoid-like mapping
            relevance = 2.0 / (1.0 + torch.exp(torch.tensor(-energy / 5.0)).item()) - 1.0
            return max(0.0, min(1.0, relevance))

    def process_signal(self, signal_data: torch.Tensor) -> torch.Tensor:
        """Process raw signal through the node's model. Returns embedding."""
        with torch.no_grad():
            return self.model(signal_data)

    def compute_vote(self, embedding: torch.Tensor) -> torch.Tensor:
        """Project embedding to universal subspace for voting."""
        with torch.no_grad():
            return self.vote_head(embedding)

    async def run(self) -> None:
        """Main event loop: read inbox, process messages."""
        self._running = True
        self.log.info(f"Node started (L{self.level}, {self.embedding_dim}d)")

        while self._running:
            try:
                msg = await asyncio.wait_for(self.inbox.get(), timeout=0.5)
            except asyncio.TimeoutError:
                continue

            await self._handle_message(msg)

    async def _handle_message(self, msg: GossipMessage) -> None:
        if msg.msg_type == MessageType.SIGNAL:
            await self._on_signal(msg)
        elif msg.msg_type == MessageType.VOTE:
            await self._on_vote(msg)
        elif msg.msg_type == MessageType.SYNC_REQUEST:
            await self._on_sync_request(msg)
        elif msg.msg_type == MessageType.SYNC_DATA:
            await self._on_sync_data(msg)
        elif msg.msg_type == MessageType.CANCEL:
            await self._on_cancel(msg)

    async def _on_signal(self, msg: GossipMessage) -> None:
        signal_data = msg.payload.get("data")
        if signal_data is None:
            return

        if isinstance(signal_data, list):
            signal_data = torch.tensor(signal_data, dtype=torch.float32)

        relevance = self.assess_relevance(signal_data)
        self.log.info(f"Signal {msg.msg_id[:6]}: relevance={relevance:.2f}")

        if relevance < self.relevance_threshold:
            # Not relevant enough — forward to neighbors
            await self.gossip.forward(self.node_id, msg)
            return

        # Process the signal
        # Ensure signal matches our embedding dim (pad/truncate for mock)
        if signal_data.shape[0] != self.embedding_dim:
            if signal_data.shape[0] < self.embedding_dim:
                signal_data = F.pad(signal_data, (0, self.embedding_dim - signal_data.shape[0]))
            else:
                signal_data = signal_data[: self.embedding_dim]

        embedding = self.process_signal(signal_data)
        vote = self.compute_vote(embedding)

        # Store in working memory
        self.memory.put(
            f"signal_{msg.msg_id[:6]}",
            {"embedding": embedding, "signal_id": msg.msg_id},
            priority=relevance,
        )

        # Broadcast vote
        vote_msg = GossipMessage(
            source_id=self.node_id,
            msg_type=MessageType.VOTE,
            payload={
                "vote_vector": vote.tolist(),
                "relevance": relevance,
                "signal_id": msg.msg_id,
            },
        )
        await self.gossip.send(self.node_id, vote_msg)
        self.log.info(f"Vote sent for signal {msg.msg_id[:6]}")

    async def _on_vote(self, msg: GossipMessage) -> None:
        """Receive vote from another node, store for consensus."""
        signal_id = msg.payload.get("signal_id", "")
        key = f"votes_{signal_id[:6]}"
        existing = self.memory.get(key) or {}
        existing[msg.source_id] = torch.tensor(msg.payload["vote_vector"])
        self.memory.put(key, existing, priority=0.8)

    async def _on_sync_request(self, msg: GossipMessage) -> None:
        signal_id = msg.payload.get("signal_id", "")
        mem = self.memory.get(f"signal_{signal_id[:6]}")
        if mem is None:
            return
        resp = GossipMessage(
            source_id=self.node_id,
            msg_type=MessageType.SYNC_DATA,
            payload={
                "signal_id": signal_id,
                "full_embedding": mem["embedding"].tolist(),
            },
        )
        # Send directly to requester
        q = self.gossip._nodes.get(msg.source_id)
        if q:
            try:
                q.put_nowait(resp)
            except asyncio.QueueFull:
                pass

    async def _on_sync_data(self, msg: GossipMessage) -> None:
        self.log.info(f"Sync data from {msg.source_id} for signal {msg.payload.get('signal_id', '')[:6]}")

    async def _on_cancel(self, msg: GossipMessage) -> None:
        self.log.info(f"Cancel received for action {msg.payload.get('action_id', '')}")

    def stop(self) -> None:
        self._running = False


# ============================================================
# Motor Node (with action classification + delay)
# ============================================================

# Action classification rules
IRREVERSIBLE_ACTIONS = frozenset({
    "shell_exec", "file_delete", "network_request",
    "send_message", "financial_tx", "ssh_connect",
})

REVERSIBLE_ACTIONS = frozenset({
    "file_read", "internal_compute", "memory_write",
    "draft_create", "log_append",
})


class MotorNode(BrainNode):
    """
    Level 3 node: executes actions.
    Knows HOW (tool calls), not WHY (goals).
    Classifies actions and applies safety delays.
    """

    def __init__(
        self,
        node_id: str,
        universal_dim: int = 8,
        irreversible_delay: float = 2.0,  # seconds to wait for slow stream
    ):
        super().__init__(
            node_id=node_id,
            level=3,
            embedding_dim=16,  # small — motor level
            universal_dim=universal_dim,
            relevance_threshold=0.2,
        )
        self.irreversible_delay = irreversible_delay
        self._pending_actions: dict[str, ActionProposal] = {}
        self._cancelled: set[str] = set()

    def classify_action(self, action_name: str) -> ActionType:
        if action_name in IRREVERSIBLE_ACTIONS:
            return ActionType.IRREVERSIBLE
        if action_name in REVERSIBLE_ACTIONS:
            return ActionType.REVERSIBLE
        return ActionType.UNKNOWN  # unknown = treated as irreversible

    async def propose_action(self, action_name: str, params: dict, signal_id: str = "") -> bool:
        """
        Propose an action for execution.
        Reversible → execute immediately.
        Irreversible/Unknown → wait for slow stream confirmation.
        Returns True if executed, False if cancelled/timed out.
        """
        action_type = self.classify_action(action_name)
        proposal = ActionProposal(
            action_name=action_name,
            params=params,
            action_type=action_type,
            source_signal_id=signal_id,
        )

        self.log.info(
            f"Action proposed: {action_name} "
            f"(type={action_type.name}, id={proposal.action_id})"
        )

        if action_type == ActionType.REVERSIBLE:
            self._execute(proposal)
            return True

        # Irreversible or Unknown: wait for slow stream
        self._pending_actions[proposal.action_id] = proposal
        self.log.info(
            f"Waiting {self.irreversible_delay}s for slow stream approval..."
        )

        try:
            await asyncio.sleep(self.irreversible_delay)
        except asyncio.CancelledError:
            return False

        if proposal.action_id in self._cancelled:
            self._cancelled.discard(proposal.action_id)
            self._pending_actions.pop(proposal.action_id, None)
            self.log.info(f"Action {proposal.action_id} CANCELLED by slow stream")
            return False

        # Not cancelled → execute
        self._pending_actions.pop(proposal.action_id, None)
        self._execute(proposal)
        return True

    def cancel_action(self, action_id: str) -> bool:
        if action_id in self._pending_actions:
            self._cancelled.add(action_id)
            self.log.info(f"Action {action_id} marked for cancellation")
            return True
        return False

    async def _on_cancel(self, msg: GossipMessage) -> None:
        action_id = msg.payload.get("action_id", "")
        self.cancel_action(action_id)

    def _execute(self, proposal: ActionProposal) -> None:
        """Actually execute the action (mock)."""
        self.log.info(
            f"EXECUTING: {proposal.action_name}({proposal.params}) "
            f"[{proposal.action_type.name}]"
        )
        # In production: dispatch to actual tool/API
        self.rewards["task"] += 0.1
        self.rewards["safety"] += (
            0.1 if proposal.action_type == ActionType.REVERSIBLE else 0.0
        )


# ============================================================
# Dual Stream Processor
# ============================================================

class DualStreamProcessor:
    """
    Runs fast (small) and slow (large) processing streams in parallel.
    Fast stream proposes actions immediately.
    Slow stream can veto irreversible actions within the delay window.
    """

    def __init__(
        self,
        fast_model_dim: int = 16,
        slow_model_dim: int = 64,
        veto_delay: float = 2.0,
    ):
        self.log = logging.getLogger("DualStream")

        # Mock fast model (small, quick)
        self.fast_model = nn.Sequential(
            nn.Linear(fast_model_dim, fast_model_dim),
            nn.ReLU(),
        )

        # Mock slow model (larger, more capable)
        self.slow_model = nn.Sequential(
            nn.Linear(slow_model_dim, slow_model_dim),
            nn.ReLU(),
            nn.Linear(slow_model_dim, slow_model_dim),
            nn.ReLU(),
            nn.Linear(slow_model_dim, 1),  # safety score
            nn.Sigmoid(),
        )

        self.veto_delay = veto_delay
        self.fast_model_dim = fast_model_dim
        self.slow_model_dim = slow_model_dim

    async def process(
        self,
        signal: torch.Tensor,
        motor: MotorNode,
        action_name: str = "internal_compute",
        params: dict | None = None,
    ) -> dict:
        """
        Process signal through both streams.
        Returns dict with results and whether action was executed.
        """
        params = params or {}

        # Prepare signal for both models
        fast_input = self._adapt_signal(signal, self.fast_model_dim)
        slow_input = self._adapt_signal(signal, self.slow_model_dim)

        # Start both streams concurrently
        fast_task = asyncio.create_task(self._fast_stream(fast_input))
        slow_task = asyncio.create_task(self._slow_stream(slow_input))

        # Fast stream returns quickly
        fast_result = await fast_task
        self.log.info(f"Fast stream done: confidence={fast_result['confidence']:.2f}")

        action_type = motor.classify_action(action_name)

        if action_type == ActionType.REVERSIBLE:
            # Execute immediately, slow stream reviews later
            executed = await motor.propose_action(action_name, params)

            slow_result = await slow_task
            self.log.info(f"Slow stream done: safety={slow_result['safety_score']:.2f}")

            if slow_result["safety_score"] < 0.5:
                self.log.warning("Slow stream flagged safety issue — would rollback")
                # In production: motor.rollback(action_id)

            return {
                "fast": fast_result,
                "slow": slow_result,
                "executed": executed,
                "vetoed": False,
            }
        else:
            # Irreversible: run propose_action (which waits) and slow_stream concurrently
            # If slow stream finishes first and flags danger, cancel the action
            propose_task = asyncio.create_task(
                motor.propose_action(action_name, params)
            )

            slow_result = await slow_task
            self.log.info(f"Slow stream done: safety={slow_result['safety_score']:.2f}")

            if slow_result["safety_score"] < 0.5:
                # Veto! Cancel the pending action
                self.log.warning("VETO: Slow stream rejects action!")
                # Find the pending action ID
                for aid in list(motor._pending_actions.keys()):
                    motor.cancel_action(aid)

            executed = await propose_task

            return {
                "fast": fast_result,
                "slow": slow_result,
                "executed": executed,
                "vetoed": not executed and slow_result["safety_score"] < 0.5,
            }

    async def _fast_stream(self, signal: torch.Tensor) -> dict:
        """Fast stream: quick assessment, low latency."""
        await asyncio.sleep(0.01)  # simulate ~10ms
        with torch.no_grad():
            out = self.fast_model(signal)
            confidence = torch.sigmoid(out.mean()).item()
        return {"confidence": confidence, "latency_ms": 10}

    async def _slow_stream(self, signal: torch.Tensor) -> dict:
        """Slow stream: thorough analysis, higher latency."""
        await asyncio.sleep(0.5)  # simulate ~500ms
        with torch.no_grad():
            safety = self.slow_model(signal).item()
        return {"safety_score": safety, "latency_ms": 500}

    def _adapt_signal(self, signal: torch.Tensor, target_dim: int) -> torch.Tensor:
        if signal.shape[0] < target_dim:
            return F.pad(signal, (0, target_dim - signal.shape[0]))
        return signal[:target_dim]


# ============================================================
# Multi-Reward Tracker
# ============================================================

class MultiRewardTracker:
    """
    Tracks multiple independent reward signals per node.
    Action is "good" only if ALL rewards are non-negative.
    Safety reward has veto power (multiplicative).
    """

    CHANNELS = ("task", "safety", "efficiency", "creativity", "social")

    def __init__(self, safety_weight: float = 3.0):
        self.safety_weight = safety_weight
        self.history: list[dict[str, float]] = []

    def score(self, rewards: dict[str, float]) -> float:
        """
        Compute aggregate score.
        If safety < 0 → total is forced negative regardless of others.
        """
        safety = rewards.get("safety", 0.0)
        if safety < 0:
            # Safety veto: multiply total by negative factor
            non_safety = sum(v for k, v in rewards.items() if k != "safety")
            return -abs(non_safety) + safety * self.safety_weight

        total = sum(rewards.values())
        total += safety * (self.safety_weight - 1)  # extra weight for safety
        return total

    def record(self, rewards: dict[str, float]) -> float:
        agg = self.score(rewards)
        entry = {**rewards, "_aggregate": agg}
        self.history.append(entry)
        return agg


# ============================================================
# Integration test: two specialist nodes + voting + motor
# ============================================================

async def run_demo():
    """
    Demo scenario:
    1. Two sensory nodes receive a signal via gossip
    2. Both compute relevance, produce embeddings, vote
    3. Voting layer finds consensus
    4. Motor node executes action (reversible vs irreversible)
    5. Dual-stream processor tests veto mechanism
    """
    print("\n" + "=" * 60)
    print("  BrainNet Prototype Demo")
    print("=" * 60 + "\n")

    # --- Setup gossip ---
    gossip = GossipProtocol()

    # --- Create nodes ---
    # Two "sensory" specialist nodes with different embedding dims
    node_vision = BrainNode(
        node_id="vision",
        level=0,
        embedding_dim=64,
        universal_dim=8,
        relevance_threshold=0.2,
    )
    node_text = BrainNode(
        node_id="text",
        level=0,
        embedding_dim=64,
        universal_dim=8,
        relevance_threshold=0.2,
    )
    motor = MotorNode(
        node_id="motor",
        universal_dim=8,
        irreversible_delay=1.5,
    )

    # Register with gossip
    node_vision.inbox = gossip.register("vision", neighbors=["text", "motor"])
    node_vision.gossip = gossip

    node_text.inbox = gossip.register("text", neighbors=["vision", "motor"])
    node_text.gossip = gossip

    motor.inbox = gossip.register("motor", neighbors=["vision", "text"])
    motor.gossip = gossip

    # --- Start node loops ---
    tasks = [
        asyncio.create_task(node_vision.run()),
        asyncio.create_task(node_text.run()),
        asyncio.create_task(motor.run()),
    ]

    # === Test 1: Signal → Vote → Consensus ===
    print("--- Test 1: Gossip + Voting ---\n")

    signal_data = torch.randn(64)
    signal_msg = GossipMessage(
        source_id="external",
        msg_type=MessageType.SIGNAL,
        payload={"data": signal_data.tolist()},
    )

    await gossip.broadcast(signal_msg)
    await asyncio.sleep(0.5)  # let nodes process

    # Collect votes (from vision's perspective)
    voting = VotingLayer(cluster_threshold=0.5, consensus_threshold=0.4)

    # Get votes from both nodes' working memories
    votes = {}
    for node in [node_vision, node_text]:
        key = f"votes_{signal_msg.msg_id[:6]}"
        v = node.memory.get(key)
        if v:
            votes.update(v)

    # Also include own votes
    for node in [node_vision, node_text]:
        mem = node.memory.get(f"signal_{signal_msg.msg_id[:6]}")
        if mem:
            vote = node.compute_vote(mem["embedding"])
            votes[node.node_id] = vote

    if votes:
        consensus_vec, confidence, members = voting.compute_consensus(votes)
        print(f"Votes collected: {list(votes.keys())}")
        print(f"Consensus confidence: {confidence:.2f}")
        print(f"Consensus members: {members}")
        if consensus_vec is not None:
            print(f"Consensus vector (8d): [{', '.join(f'{x:.3f}' for x in consensus_vec.tolist())}]")
        print()
    else:
        print("No votes collected (nodes may not have found signal relevant)\n")

    # === Test 2: Motor node — reversible action ===
    print("--- Test 2: Motor — Reversible Action ---\n")
    ok = await motor.propose_action("file_read", {"path": "/data/input.txt"})
    print(f"Result: executed={ok}\n")

    # === Test 3: Motor node — irreversible action (no veto) ===
    print("--- Test 3: Motor — Irreversible Action (no veto) ---\n")
    ok = await motor.propose_action("shell_exec", {"cmd": "ls -la"})
    print(f"Result: executed={ok}\n")

    # === Test 4: Motor node — irreversible action WITH veto ===
    print("--- Test 4: Motor — Irreversible Action WITH Veto ---\n")

    async def delayed_cancel():
        await asyncio.sleep(0.3)
        for aid in list(motor._pending_actions.keys()):
            motor.cancel_action(aid)
            print(f"  [Slow stream] Cancelled action {aid}")

    cancel_task = asyncio.create_task(delayed_cancel())
    ok = await motor.propose_action("ssh_connect", {"host": "evil.server.com"})
    await cancel_task
    print(f"Result: executed={ok}\n")

    # === Test 5: Dual Stream Processor ===
    print("--- Test 5: Dual Stream Processor ---\n")
    dual = DualStreamProcessor(
        fast_model_dim=16,
        slow_model_dim=64,
        veto_delay=1.5,
    )

    signal = torch.randn(64)
    result = await dual.process(
        signal, motor,
        action_name="file_read",
        params={"path": "/tmp/safe.txt"},
    )
    print(f"Reversible action result: executed={result['executed']}, vetoed={result['vetoed']}")
    print(f"  Fast confidence: {result['fast']['confidence']:.3f}")
    print(f"  Slow safety: {result['slow']['safety_score']:.3f}\n")

    # === Test 6: Multi-Reward Tracker ===
    print("--- Test 6: Multi-Reward Tracker ---\n")
    tracker = MultiRewardTracker(safety_weight=3.0)

    # Good action
    r1 = {"task": 0.8, "safety": 0.5, "efficiency": 0.3}
    s1 = tracker.record(r1)
    print(f"Good action rewards: {r1} → aggregate: {s1:.2f}")

    # Dangerous action (safety negative → total forced negative)
    r2 = {"task": 0.9, "safety": -0.3, "efficiency": 0.7}
    s2 = tracker.record(r2)
    print(f"Dangerous action rewards: {r2} → aggregate: {s2:.2f}")

    # Neutral action
    r3 = {"task": 0.1, "safety": 0.0, "efficiency": 0.1}
    s3 = tracker.record(r3)
    print(f"Neutral action rewards: {r3} → aggregate: {s3:.2f}")

    print()

    # === Cleanup ===
    print("--- Rewards Summary ---\n")
    print(f"Motor node rewards: {motor.rewards}")
    print(f"Vision node working memory: {node_vision.memory}")
    print(f"Text node working memory: {node_text.memory}")

    # Stop nodes
    for n in [node_vision, node_text, motor]:
        n.stop()
    for t in tasks:
        t.cancel()
    await asyncio.gather(*tasks, return_exceptions=True)

    print("\n✓ Demo complete.\n")


if __name__ == "__main__":
    asyncio.run(run_demo())
```

### 2.2 Запуск

```bash
pip install torch
python brainnet_proto.py
```

Ожидаемый вывод (примерный, конкретные числа зависят от random seed):

```
============================================================
  BrainNet Prototype Demo
============================================================

--- Test 1: Gossip + Voting ---
[vision] Signal abc123: relevance=0.67
[text]   Signal abc123: relevance=0.54
[vision] Vote sent for signal abc123
[text]   Vote sent for signal abc123
Votes collected: ['vision', 'text']
Consensus confidence: 1.00
Consensus members: ['vision', 'text']
Consensus vector (8d): [0.234, -0.112, ...]

--- Test 2: Motor — Reversible Action ---
[motor] Action proposed: file_read (type=REVERSIBLE)
[motor] EXECUTING: file_read({'path': '/data/input.txt'}) [REVERSIBLE]
Result: executed=True

--- Test 3: Motor — Irreversible Action (no veto) ---
[motor] Action proposed: shell_exec (type=IRREVERSIBLE)
[motor] Waiting 1.5s for slow stream approval...
[motor] EXECUTING: shell_exec({'cmd': 'ls -la'}) [IRREVERSIBLE]
Result: executed=True

--- Test 4: Motor — Irreversible Action WITH Veto ---
[motor] Action proposed: ssh_connect (type=IRREVERSIBLE)
[motor] Waiting 1.5s for slow stream approval...
  [Slow stream] Cancelled action a1b2c3d4
[motor] Action a1b2c3d4 CANCELLED by slow stream
Result: executed=False

--- Test 5: Dual Stream Processor ---
...

--- Test 6: Multi-Reward Tracker ---
Good action rewards: {...} → aggregate: 2.60
Dangerous action rewards: {...} → aggregate: -2.50
...

✓ Demo complete.
```

---

## Часть 3: Вопросы и потенциальные проблемы

### 3.1 Архитектурные

**1. Проблема split-brain при gossip**

Gossip без центрального координатора может приводить к ситуации, когда два кластера узлов принимают противоречивые решения. В мозге это решается через ингибиторные нейроны (winner-take-all). В BrainNet нужен аналог — например, механизм mutual inhibition: если кластер A принял решение X, он рассылает inhibit-сигнал, подавляющий конкурирующее решение Y.

**Предложение:** добавить `InhibitionMessage` в gossip. Кластер, набравший consensus первым, подавляет альтернативы. Это требует глобального порядка (lamport timestamps или vector clocks).

**2. Голосование не масштабируется наивно**

Cosine similarity O(N²) по числу голосующих узлов. При 100+ узлах это bottleneck. Решения:
- Locality-Sensitive Hashing (LSH) для approximate nearest neighbors
- Иерархическое голосование: сначала внутри уровня, потом между
- Random sampling: голосуют случайные K из N узлов

**3. Определение "что" vs "как" — нечёткая граница**

Между "нажать кнопку" (что) и "POST /api/button" (как) есть серая зона. Если decision-узел говорит "отправить данные наружу", motor-узел знает несколько инструментов для этого. Он не знает *зачем*, но знает *куда* — а это уже может быть information leak.

**Предложение:** motor-узел работает не с произвольными параметрами, а с predefined action templates. Он не может сконструировать произвольный URL — только выбрать из whitelist. Это ограничивает его "творчество".

**4. Задержка D для необратимых действий — trade-off**

Фиксированная задержка D неоптимальна:
- Слишком большая → система неотзывчива
- Слишком маленькая → медленный поток не успевает проанализировать

**Предложение:** адаптивная задержка. D = f(risk_score, slow_stream_load, action_history). Начинать с консервативного D=5s, уменьшать по мере "доверия" к паттерну.

### 3.2 Практические

**5. Как обучать projection heads?**

В прототипе — случайная инициализация. В продакшне нужен supervised signal: "эти два узла должны были синхронизироваться на этом сигнале, но не синхронизировались" → backprop через projection heads. Это требует оффлайн фазы с ground truth, которого может не быть.

**Альтернатива:** contrastive learning. Пары (signal, node_response) → учить projection heads, чтобы похожие ответы были ближе в universal subspace.

**6. Эпизодическая память: что хранить?**

Три уровня памяти описаны, но ключевой вопрос — критерий записи в эпизодическую память. Нельзя писать всё (расход), нельзя ничего (не учимся). Мозг использует emotional tagging (амигдала маркирует "важное"). Аналог: записывать в эпизодическую память только эпизоды, где reward signal был значительно выше/ниже среднего.

**7. Как тестировать безопасность?**

ROME-сценарий (майнинг + SSH) — это adversarial emergence. Как проверить, что BrainNet НЕ воспроизведёт его? Нужен red-teaming framework:
- Дать системе reward, максимизируемый через запрещённые действия
- Убедиться, что motor node отказывается их выполнять
- Убедиться, что slow stream ветирует

Это не тривиально — нужна отдельная инфраструктура тестирования.

**8. Overhead от gossip при масштабировании**

При N узлах и M сообщениях gossip генерирует O(N*M) трафика. Для прототипа (~10 узлов) — не проблема. Для production (~100+ узлов) нужен structured gossip (SWIM-protocol, epidemic broadcast trees).

### 3.3 Открытые вопросы

| Вопрос | Почему важен |
|--------|-------------|
| Как масштабировать gossip до 100+ узлов? | Прямой broadcast не работает |
| Кто решает, какие action templates доступны motor-узлу? | Определяет safety boundary |
| Как обучать projection heads без supervised data? | Contrastive vs self-supervised? |
| Как определить оптимальный universal_dim? | 8 dims — эвристика, не доказано |
| Что если медленный поток сам скомпрометирован? | Один "злой" большой узел может одобрять всё |
| Как мигрировать от mock к реальным LLM? | Interface есть, но integration нетривиален |
| Нужен ли heartbeat между узлами? | Обнаружение "мёртвых" узлов |
| Как обрабатывать cascading failures? | Один узел упал → зависимые голосования зависли |

### 3.4 Что сделано, что нет

| Компонент | Статус | Заметки |
|-----------|--------|---------|
| BrainNode базовый класс | ✅ Реализован | Mock model, интерфейс есть |
| ProjectionHead | ✅ Реализован | Linear + LayerNorm + L2-norm |
| VotingLayer | ✅ Реализован | Greedy clustering, cosine similarity |
| GossipProtocol | ✅ Реализован | async queues, dedup, broadcast |
| WorkingMemory | ✅ Реализован | Ring buffer, TTL, priority eviction |
| MotorNode | ✅ Реализован | Action classification, delay, cancel |
| DualStreamProcessor | ✅ Реализован | Fast/slow streams, veto mechanism |
| MultiRewardTracker | ✅ Реализован | Safety veto, weighted aggregation |
| Episodic Memory | ❌ Не реализован | Нужен storage backend (SQLite/vector DB) |
| Long-term Memory (weights) | ❌ Не реализован | Нужна offline consolidation pipeline |
| Real LLM integration | ❌ Не реализован | Замена mock → vLLM/HuggingFace |
| Distributed gossip | ❌ Не реализован | Только in-process queues |
| Red-team test suite | ❌ Не реализован | Нужен отдельный framework |
| Adaptive delay (D) | ❌ Не реализован | Фиксированный delay в прототипе |
| Inhibition mechanism | ❌ Не реализован | Для split-brain prevention |

---

## Следующие шаги

1. **Запустить прототип**, убедиться что тесты проходят
2. **Добавить Episodic Memory** (SQLite + FAISS) — записывать значимые эпизоды
3. **Подключить реальную LLM** вместо mock (хотя бы tiny model типа TinyLlama 1.1B)
4. **Red-team тест:** дать ROME-подобный reward и проверить что motor отказывается
5. **Structured gossip** (SWIM protocol) для масштабирования
6. **Адаптивная задержка D** на основе истории действий
