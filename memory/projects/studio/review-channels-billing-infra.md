# Ревью модулей: CHANNELS, BILLING, NODES, SANDBOX, BROWSER POOL

> Составлено: 2026-04-04  
> Архитектор: Аркаша  
> Источники: `arkadius-modules.md` (разделы 7, 10, 13–17), `nano-claude-code` (github.com/SafeRL-Lab/nano-claude-code v3.03)

---

## Контекст: чему учит утечка Claude Code

nano-claude-code — реализация Claude Code CLI, которая воспроизводит ключевые паттерны системного промпта и архитектуры Anthropic. Для Аркадиуса она ценна следующим:

| Паттерн | В nano-claude-code | Статус в Аркадиусе |
|---------|-------------------|-------------------|
| Tool permission (auto/manual/deny) | ✅ | ✅ включён |
| Context compression | ✅ | ✅ включён |
| AskUserQuestion | ✅ v3.02 | ✅ включён |
| Dual-scope memory | ✅ | ✅ включён |
| Sub-agents (typed) | ✅ | ✅ включён |
| **Task management** (TaskCreate/List/Deps) | ✅ v3.03 | ❌ ПРОПУЩЕНО |
| **MCP support** | ✅ v3.01 | ❌ ПРОПУЩЕНО |
| Plugin system | ✅ v3.02 | ⚠️ частично через IntegrationBuilder |

**Вывод**: Аркадиус хорошо воспроизводит агент-loop и memory паттерны, но полностью пропускает Task Management и MCP — два из трёх крупных дополнений v3.x. Это важные пробелы не только для feature-parity, но и для пользовательского опыта (агент не может управлять задачами между сессиями).

---

## 1. CHANNELS (apps/channels/)

### 1.1 Оценка правильности

Архитектура **правильная**: BaseChannel абстракция, отдельные handler-ы per-channel, ChannelRouter как диспетчер — стандартный и рабочий паттерн. ChannelType enum, normalize() для нормализации входящих событий, media_pipeline — всё логично.

Однако реализация **поверхностная**: описаны классы и методы, но не описаны критические операционные детали, без которых канал не доживёт до продакшена.

### 1.2 Пропущенное

**Критично:**

1. **Webhook verification** не вынесен в абстракцию. Каждый канал имеет свой механизм:
   - Telegram: `secret_token` в заголовке `X-Telegram-Bot-Api-Secret-Token`
   - VK: HMAC-SHA256 + `secret` из кабинета
   - MAX: собственный механизм подписи
   
   В `BaseChannel` нужен метод `verify_webhook(request) -> bool`. Без него — уязвимость.

2. **Update deduplication** отсутствует. Telegram отправляет одно событие несколько раз при сетевых сбоях (update_id повторяется). Нужен Redis SET: `telegram:processed:{update_id}` с TTL 24h.

3. **Outgoing retry / dead-letter queue**. `send_message()` может упасть (Telegram API 429, VK 503). Нет описания что происходит: ответ агента теряется. Нужна очередь retry с Celery beat.

4. **Long message splitting**. Telegram: лимит 4096 символов. VK: 4096. MAX: 4096. Агент может сгенерировать 8000+ символов. Нет авто-разбивки — сообщение упадёт с ошибкой API.

5. **Typing indicator**. `sendChatAction(action="typing")` в Telegram — пользователь не понимает что агент думает без этого. Влияет на UX критично.

**Важно:**

6. **Channel-specific formatting** не описан. MarkdownV2 в Telegram требует эскейпинга спецсимволов (`_`, `*`, `[`, `]`, ...). Агент генерирует Markdown → Telegram его не принимает или рендерит неправильно. Нужен `format_for_channel(text, channel_type) -> str`.

7. **Graceful degradation** при недоступности канального API. Если Telegram API недоступен 2 минуты — всё должно буферизоваться, не падать.

8. **send_stream vs send_message** — нечёткое разделение. Только Web-канал реально поддерживает streaming. Telegram/VK/MAX получают полный ответ. В `BaseChannel.send_stream()` нужна явная пометка: "для non-web каналов — буферизовать и отправить единым сообщением".

### 1.3 Лишнее для MVP

| Компонент | Почему лишнее |
|-----------|--------------|
| **VK канал** | Нишевая аудитория РФ-корпоратов, сложный API (группы, Callback API, проверка Confirmation). Post-MVP. |
| **MAX канал** | ex-ICQ, минимальная живая аудитория. Post-MVP. |
| **media_pipeline.transcribe_audio** | Whisper транскрипция голосовых — для MVP достаточно "голосовые сообщения не поддерживаются". |
| **GroupParticipantProfile (секция 8)** | Двухуровневая модель групп с профилями — сложно. Для MVP: один уровень, простая membership. |

**MVP-минимум по каналам:** Web + Telegram.

### 1.4 Конкретные улучшения

```python
# 1. BaseChannel — добавить абстрактные методы
class BaseChannel(ABC):
    @abstractmethod
    async def verify_webhook(self, request: Request) -> bool: ...
    
    @abstractmethod
    def split_message(self, text: str) -> List[str]:
        """Разбить по лимиту символов для этого канала."""
        ...
    
    @abstractmethod
    async def send_typing(self, channel_id: str) -> None: ...

# 2. Telegram deduplication
async def on_message(self, update: aiogram.Update):
    key = f"telegram:processed:{update.update_id}"
    if await redis.set(key, "1", nx=True, ex=86400):
        await self.process(update)
    # дублирующий webhook — молча игнорируем

# 3. Outgoing retry через Celery
@celery_app.task(bind=True, max_retries=3, default_retry_delay=60)
async def send_channel_message(self, channel_type, channel_id, text):
    try:
        channel = ChannelFactory.get(channel_type)
        await channel.send_message(channel_id, text)
    except ChannelAPIError as exc:
        raise self.retry(exc=exc)
```

**Правило для MarkdownV2**: добавить утилиту `escape_markdown_v2(text)` и использовать режим по умолчанию `HTML` вместо MarkdownV2 (меньше эскейпинга).

---

## 2. BILLING (apps/billing/)

### 2.1 Оценка правильности

Структура **правильная**: CreditManager с атомарными debit/credit, UsageTracker, pricing.py, ЮKassa в admin-repo, Redis pub/sub для событий оплаты. Разделение concerns между arkadius и arkadius-admin — верное решение.

**Серьёзная архитектурная проблема**: описание не соответствует заявленному MVP. По задаче MVP = "один Anthropic ключ в admin, счётчик токенов per-user". Текущая архитектура сразу реализует полный биллинг (тарифные планы, ЮKassa, prepaid кредиты). Это не MVP.

### 2.2 Пропущенное

**Критично:**

1. **MVP-режим "один ключ"** отсутствует. В LiteLLM конфиге хранится admin Anthropic API key. Нужен флаг в `Settings`:
   ```python
   BILLING_MODE: Literal["admin_key", "prepaid_credits"] = "admin_key"
   ```
   В режиме `admin_key` — только считать токены per-user, не блокировать по балансу.

2. **Idempotency топапов** критически важна. Если ЮKassa webhook отправится дважды (retry) — пользователь получит двойное начисление. Нужен `UNIQUE(yokassa_payment_id)` на CreditTransaction.

3. **Daily/Monthly token cap** отсутствует. Без жёсткого лимита пользователь может за ночь потратить весь Admin ключ через runaway agent loop. Нужен `daily_token_limit` в AgentConfig.

4. **Pre-execution cost estimate** отсутствует. Перед запуском дорогой операции (субагент + sandbox + 10 шагов) — нет оценки стоимости и запроса подтверждения.

**Важно:**

5. **Billing event для debit** не публикуется в Redis. Сейчас только `billing:topup` события. Для real-time мониторинга нужны и `billing:debit:{user_id}`.

6. **Refund flow** не описан. `YoKassaInvoice.status` может стать `refunded`, но нет обратного начисления кредитов.

7. **Free starter credits** отсутствуют. При регистрации нет welcome bonus — пользователь должен сразу платить. Для growth это проблема.

### 2.3 Лишнее для MVP

| Компонент | Почему лишнее |
|-----------|--------------|
| **PricingPlan (планы подписки)** | Для MVP фиксированная ставка: 1₽ = 100 кредитов, 1000 токенов = 1 кредит. Без планов. |
| **track_tool_usage по duration_ms** | Биллинг за использование инструментов — сложно для MVP. Только LLM токены. |
| **get_usage_stats(period)** | Аналитика использования — post-MVP. |
| **YoKassaInvoice как отдельная таблица** | Для MVP достаточно поля `yokassa_payment_id` в CreditTransaction. |
| **ЮKassa полная интеграция** | Для закрытого MVP вообще не нужна — admin вручную начисляет кредиты через API. |

### 2.4 Конкретные улучшения

```python
# 1. MVP-режим: только токен-счётчик
class UsageTracker:
    async def track_llm_usage(self, user_id, session_id, usage: UsageStats):
        # Всегда логируем
        await self._log_usage(user_id, usage)
        
        settings = get_settings()
        if settings.BILLING_MODE == "prepaid_credits":
            cost = self.calculate_cost(usage)
            await self.credit_manager.debit(user_id, cost, ...)
        # В admin_key режиме — просто счётчик, не блокируем

# 2. Daily cap check
class AgentConfig(BaseModel):
    daily_token_limit: int = 100_000  # дефолт: 100k токенов/день
    
# 3. Idempotency
class CreditTransaction(Base):
    __table_args__ = (
        UniqueConstraint('idempotency_key', name='uq_credit_idempotency'),
    )
    idempotency_key: str  # = yokassa_payment_id или uuid

# 4. Welcome bonus при регистрации
async def create_user(email, password) -> User:
    user = await user_repo.create(...)
    await credit_manager.credit(
        user.id, 
        amount=settings.WELCOME_BONUS_CREDITS,
        description="Welcome bonus",
        ref_id="welcome"
    )
    return user
```

---

## 3. NODES (apps/agent/src/nodes/)

### 3.1 Оценка правильности

Концепция **верная**: SSH-нода для серверов пользователя, клиентская нода для локальных машин, WebSocket туннель, vault для SSH ключей. Это позволяет агенту работать непосредственно в среде пользователя — сильная дифференциация от конкурентов.

**Главная проблема**: архитектура описана на уровне "что" но не "как". WebSocket туннель упомянут, но протокол не определён. Без протокола NodeExecutor — заглушка.

### 3.2 Пропущенное

**Критично:**

1. **WebSocket протокол не определён**. NodeExecutor "выполняет команды через WebSocket туннель" — но нет ни framing, ни message types, ни sequence IDs. Это должно быть:
   ```python
   class NodeMessage(BaseModel):
       type: Literal["exec_req", "exec_resp", "file_read_req", "file_read_resp",
                     "heartbeat", "heartbeat_ack", "cancel"]
       request_id: str  # UUID, для матчинга req/resp
       payload: dict
       timestamp: datetime
   ```

2. **Node authentication** не описана. Как нода доказывает что она "наша"? JWT токен при подключении (node_token), который хранится в vault нода. При реконнекте нода предъявляет токен.

3. **Reconnection / offline queue**. Ноды периодически теряют соединение (VPN, сон ноутбука). Что происходит с pending командами? Нужна очередь в Redis с TTL.

4. **Node capabilities schema** не определён. `capabilities JSONB` — что туда писать? Предлагаю:
   ```json
   {
     "os": "linux",
     "arch": "x86_64",
     "python": "3.11",
     "docker": true,
     "gpu": false,
     "memory_gb": 8,
     "disk_gb": 100
   }
   ```

5. **Health monitoring** отсутствует. KAIROS должен ping ноды каждые 5 минут и обновлять `node.status`. Без этого агент не знает доступна ли нода.

**Важно:**

6. **Multi-node routing алгоритм** не описан. NodeRegistry есть, но по какому критерию выбирается нода? Предложение: приоритет по `node.status == ONLINE`, затем по `capabilities` (нужен docker → выбрать ноду с docker=true).

7. **arkadius-node-server** описан только как "Rust daemon" в таблице репозиториев. Нет API, нет списка команд, нет WebSocket эндпоинта. Нужен отдельный раздел.

### 3.3 Лишнее для MVP

| Компонент | Почему лишнее |
|-----------|--------------|
| **ssh_installer.py** | Автоустановка через SSH — сложно, риски безопасности. Для MVP: дать пользователю install.sh скрипт. |
| **Multi-node routing** | Для MVP достаточно одной ноды на пользователя. |
| **File operations через ноду** | FileReadTool/FileWriteTool через WebSocket — сложно. Для MVP только exec. |

### 3.4 Конкретные улучшения

```python
# 1. NodeStatus enum
class NodeStatus(str, Enum):
    PENDING = "pending"      # зарегистрирована, не подключена
    ONLINE = "online"        # активное WS соединение
    OFFLINE = "offline"      # WS соединение разорвано
    ERROR = "error"          # ошибка последней операции

# 2. Node authentication при WS handshake
# arkadius-node-server при старте получает node_token из vault
# При подключении: ws.send({"type": "auth", "node_token": "..."})
# Сервер проверяет токен, возвращает {"type": "auth_ok", "node_id": "..."}

# 3. Offline queue
async def execute_on_node(node_id, cmd, timeout=30) -> ExecResult:
    node = await node_registry.get(node_id)
    if node.status != NodeStatus.ONLINE:
        raise NodeOfflineError(f"Node {node_id} is offline")
    
    request_id = str(uuid4())
    await ws_manager.send(node_id, {
        "type": "exec_req",
        "request_id": request_id,
        "payload": {"cmd": cmd, "timeout": timeout}
    })
    
    # Ждём ответ через Redis BLPOP (не busy-poll)
    result = await redis.blpop(f"node:resp:{request_id}", timeout=timeout+5)
    return ExecResult.parse_raw(result)

# 4. KAIROS heartbeat
@celery_app.task
async def check_node_health():
    nodes = await node_manager.get_all_online()
    for node in nodes:
        if time.time() - node.last_ping_at > 300:  # 5 мин без пинга
            await node_manager.set_status(node.id, NodeStatus.OFFLINE)
```

---

## 4. SANDBOX (apps/sandbox/ + arkadius-admin/apps/sandbox/)

### 4.1 Оценка правильности

Концепция **правильная**: Docker контейнеры по требованию, три уровня ресурсов, автоочистка idle контейнеров через Celery, приоритет ноды перед облачным sandbox. Разделение SandboxRouter (arkadius) и SandboxManager (arkadius-admin) логично.

**Проблема**: полностью отсутствует security-spec контейнеров. Docker из коробки небезопасен для публичного доступа — нужны явные ограничения.

### 4.2 Пропущенное

**Критично:**

1. **Ресурсные лимиты не определены**. Micro/Small/Medium — пустые названия без цифр. Нужно:
   ```python
   SANDBOX_TIERS = {
       "micro":  {"cpu_quota": 25000, "mem_limit": "256m", "storage": "1g"},
       "small":  {"cpu_quota": 50000, "mem_limit": "512m", "storage": "5g"},
       "medium": {"cpu_quota": 100000, "mem_limit": "1g",  "storage": "10g"},
   }
   ```

2. **Network isolation** не описана. По умолчанию Docker контейнер имеет доступ к host network. Нужно:
   - `--network=sandbox_net` (изолированная сеть)
   - Запрет доступа к internal IP диапазонам (169.254.x.x, 10.x.x.x)
   - Whitelist только для PyPI, npm, apt

3. **Security hardening** полностью отсутствует:
   ```python
   docker.containers.run(
       image=SANDBOX_IMAGE,
       user="sandbox:sandbox",          # non-root
       read_only=True,                   # read-only root FS
       tmpfs={"/tmp": "size=100m"},      # writable tmp
       security_opt=["no-new-privileges"],
       cap_drop=["ALL"],
       cap_add=["NET_BIND_SERVICE"],     # минимум
   )
   ```

4. **Sandbox базовый образ** не описан. Что включено? Python 3.11? pip? node? git? Нужна явная спецификация Dockerfile с зафиксированными версиями.

5. **stdout truncation** отсутствует. Агент может запустить `cat largefile.csv` — 50MB stdout. Нужно обрезать вывод > 50KB с сообщением "[output truncated, X bytes omitted]".

**Важно:**

6. **Pre-warmed pool** отсутствует. Cold start Docker ~2-5 секунд. Для хорошего UX нужен небольшой пул "тёплых" контейнеров:
   ```python
   PREWARM_POOL_SIZE = 3  # держать 3 готовых контейнера
   ```

7. **Workspace persistence** не описана. Что выживает между сессиями в sandbox? Предложение: `/workspace` маунтится из S3 через s3fs-fuse или явно синхронизируется при start/stop.

8. **Параллельные задачи одного пользователя** — race condition. Два субагента одновременно запускают код в одном контейнере. Нужен lock или отдельный контейнер per task.

### 4.3 Лишнее для MVP

| Компонент | Почему лишнее |
|-----------|--------------|
| **FUSE/S3 mount** | Сложная настройка, часто ненадёжна. Для MVP: явный sync через `docker cp` при start/stop. |
| **Три уровня Micro/Small/Medium** | Для MVP один уровень (Small). Уровни добавить с биллингом. |
| **IntegrationBuilder** (использует sandbox) | Агент пишет интеграции — это advanced feature, post-MVP. |

### 4.4 Конкретные улучшения

```python
# 1. Строгий Docker create
class DockerSandboxManager:
    async def create_sandbox(self, user_id: str, tier: str = "small") -> SandboxInfo:
        limits = SANDBOX_TIERS[tier]
        container = self.docker_client.containers.create(
            image=settings.SANDBOX_IMAGE,
            name=f"arkadius-sandbox-{user_id}",
            user="1000:1000",
            read_only=True,
            tmpfs={"/tmp": "size=100m,exec", "/workspace": "size=" + limits["storage"]},
            network=settings.SANDBOX_NETWORK,
            mem_limit=limits["mem_limit"],
            cpu_quota=limits["cpu_quota"],
            cpu_period=100000,
            security_opt=["no-new-privileges"],
            cap_drop=["ALL"],
            environment={"HOME": "/workspace", "PATH": "/usr/local/bin:/usr/bin:/bin"},
        )
        return SandboxInfo(container_id=container.id, ...)

# 2. stdout truncation
MAX_OUTPUT_BYTES = 50 * 1024  # 50KB

class ExecResult:
    def truncate(self) -> "ExecResult":
        if len(self.stdout.encode()) > MAX_OUTPUT_BYTES:
            truncated = self.stdout.encode()[:MAX_OUTPUT_BYTES].decode(errors="replace")
            self.stdout = truncated + f"\n[output truncated]"
            self.was_truncated = True
        return self
```

---

## 5. BROWSER POOL (arkadius-admin/infra/browser_pool.py)

### 5.1 Оценка правильности

Концепция **правильная**: pool браузеров фиксированного размера, acquire/release паттерн, session persistence через vault, Camoufox для защищённых сайтов. Паттерн connection pool хорошо известен и применим к браузерам.

**Проблема**: детали реализации не определены. Что происходит при queue overflow, browser crash, expired cookies — нет ответов.

### 5.2 Пропущенное

**Критично:**

1. **Timeout для acquire** не определён. Если все 50 браузеров заняты — пользователь ждёт бесконечно? Нужен max_wait:
   ```python
   async def acquire(user_id, timeout_ms=30_000) -> BrowserSession:
       try:
           return await asyncio.wait_for(self._queue.get(), timeout=timeout_ms/1000)
       except asyncio.TimeoutError:
           raise BrowserPoolExhaustedError("All browsers busy, try again later")
   ```

2. **Browser crash recovery** не описан. Playwright процесс может упасть (OOM, segfault). Нужен health check и автоперезапуск:
   ```python
   async def _health_check_loop(self):
       while True:
           for session in self.pool:
               if not await session.is_alive():
                   await self._restart_browser(session)
           await asyncio.sleep(30)
   ```

3. **Per-user browser limit** отсутствует. Один пользователь может взять все 50 браузеров одновременно. Нужен лимит: `max_per_user=3`.

4. **Expired session handling** не описан. Cookies могут истечь между сессиями. Нужно при restore_state: если основной login-cookie expired → возвращать `SessionExpiredError` вместо тихого сбоя.

5. **Camoufox selection criteria** не определён. Как решается использовать обычный Playwright или Camoufox? Предложение: параметр `stealth: bool = False` в BrowserTool, или авто-upgrade при 403/challenge detection.

**Важно:**

6. **Screenshot delivery** не описан. screenshot() возвращает bytes. Для агента 2MB base64 в tool_result — огромный context. Нужно: автозагрузка в S3, возврат presigned URL.

7. **JavaScript execution** отсутствует. `evaluate_js(code)` нет в BrowserTool. Многие задачи автоматизации требуют JS (извлечение данных, клики через JS).

8. **Proxy support** не описан. Camoufox без residential proxy легко детектируется по IP. Нужна конфигурация proxy в CamoufoxDriver.

9. **Download handling** не описан. Файловые загрузки через браузер — где сохраняются? В S3 sandbox пользователя?

### 5.3 Лишнее для MVP

| Компонент | Почему лишнее |
|-----------|--------------|
| **~50 браузеров** | Для MVP 5-10 достаточно. RAM: один Chromium ~150-300MB, 50 = 7-15GB RAM. |
| **Camoufox** | Для MVP обычный Playwright. Camoufox добавить по требованию конкретных сайтов. |
| **browser_state.py** (session persistence) | Для MVP браузер без persistent state — каждый раз чистый контекст. |
| **BrowserTool как отдельный инструмент** | Для MVP достаточно web_fetch для большинства задач. Browser — только если реально нужен JS. |

### 5.4 Конкретные улучшения

```python
# 1. acquire с timeout и per-user limit
class BrowserPool:
    _per_user_count: dict[str, int] = defaultdict(int)
    MAX_PER_USER = 3
    
    async def acquire(self, user_id: str, stealth: bool = False, 
                      timeout_ms: int = 30_000) -> BrowserSession:
        if self._per_user_count[user_id] >= self.MAX_PER_USER:
            raise BrowserLimitError(f"Max {self.MAX_PER_USER} browsers per user")
        
        session = await asyncio.wait_for(
            self._available.get(), 
            timeout=timeout_ms / 1000
        )
        
        if stealth and not isinstance(session.driver, CamoufoxDriver):
            session = await self._upgrade_to_camoufox(session)
        
        self._per_user_count[user_id] += 1
        session.user_id = user_id
        return session

# 2. Screenshots → S3
class BrowserTool(BaseTool):
    async def screenshot(self) -> ToolResult:
        png_bytes = await self.session.page.screenshot()
        s3_key = f"screenshots/{self.context.user_id}/{uuid4()}.png"
        await s3_client.upload_bytes("screenshots", s3_key, png_bytes)
        url = await s3_client.generate_presigned_url("screenshots", s3_key, expires=3600)
        return ToolResult(success=True, output={"screenshot_url": url})

# 3. evaluate_js добавить
class BrowserTool(BaseTool):
    async def evaluate_js(self, js_code: str) -> ToolResult:
        result = await self.session.page.evaluate(js_code)
        return ToolResult(success=True, output={"result": str(result)})

# 4. Health check loop
class BrowserPool:
    async def _health_loop(self):
        while True:
            dead = [s for s in self.all_sessions if not await s.is_alive()]
            for s in dead:
                self.all_sessions.remove(s)
                new_s = await self._create_browser_session()
                self.all_sessions.append(new_s)
                await self._available.put(new_s)
            await asyncio.sleep(30)
```

---

## Сводная таблица: что делать прямо сейчас vs post-MVP

### Прямо сейчас (MVP blocker)

| # | Модуль | Действие |
|---|--------|---------|
| 1 | BILLING | Добавить `BILLING_MODE=admin_key` — режим без списания, только счётчик |
| 2 | BILLING | `UNIQUE(idempotency_key)` в CreditTransaction — защита от двойных начислений |
| 3 | BILLING | `daily_token_limit` в AgentConfig — hard cap |
| 4 | CHANNELS | Webhook verification в BaseChannel — уязвимость |
| 5 | CHANNELS | Update deduplication для Telegram |
| 6 | CHANNELS | Long message splitting |
| 7 | SANDBOX | Security hardening: non-root, read-only FS, cap_drop |
| 8 | SANDBOX | Network isolation для контейнеров |
| 9 | SANDBOX | stdout truncation (50KB limit) |
| 10 | NODES | Определить WebSocket протокол (NodeMessage schema) |
| 11 | NODES | Node authentication (node_token) |
| 12 | BROWSER POOL | Timeout для acquire + per-user limit |

### Post-MVP (не блокируют запуск)

| # | Модуль | Действие |
|---|--------|---------|
| 1 | CHANNELS | VK + MAX каналы |
| 2 | CHANNELS | Typing indicator |
| 3 | BILLING | ЮKassa интеграция (MVP = ручное начисление admin-ом) |
| 4 | BILLING | PricingPlan / тарифные планы |
| 5 | SANDBOX | Pre-warmed pool |
| 6 | SANDBOX | FUSE/S3 mount (пока `docker cp`) |
| 7 | NODES | ssh_installer.py (пока install.sh скрипт) |
| 8 | NODES | Multi-node routing |
| 9 | BROWSER POOL | Camoufox (пока только Playwright) |
| 10 | BROWSER POOL | Session persistence через vault |
| 11 | ОБЩЕЕ | Task Management (TaskCreate/List/Deps) — из nano-claude-code v3.03 |
| 12 | ОБЩЕЕ | MCP support — из nano-claude-code v3.01 |

---

## Итого по каждому модулю

| Модуль | Оценка концепции | Готовность к MVP | Главная проблема |
|--------|-----------------|-----------------|-----------------|
| CHANNELS | ✅ Верная | ⚠️ 60% | Нет webhook verification, deduplication, message splitting |
| BILLING | ✅ Верная | ⚠️ 40% | Нет MVP-режима "admin key", нет idempotency |
| NODES | ✅ Верная | ❌ 20% | Не определён WebSocket протокол — заглушка |
| SANDBOX | ✅ Верная | ⚠️ 50% | Нет security hardening — небезопасен |
| BROWSER POOL | ✅ Верная | ⚠️ 45% | Нет timeout, no crash recovery, per-user limit |

**Общий вердикт**: Архитектурные решения по всем пяти модулям правильные. Проблема не в концепциях, а в отсутствии операционных деталей: протоколов, security-spec, edge-case handling. Перед началом кодинга каждый модуль должен получить явные: (а) протокол взаимодействия, (б) security-spec, (в) перечень edge cases.
