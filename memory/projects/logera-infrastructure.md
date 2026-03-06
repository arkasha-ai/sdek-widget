# Logera Infrastructure — Полный анализ

> **Ветка:** `feature/design-improvements`
> **Дата анализа:** 2026-02-14
> **Compose project name:** `logera` (prod), `logera-dev` (dev), `logera-test` (test)

---

## 1. docker-compose.yml (корневой, production-like)

### 1.1 nginx
| Параметр | Значение |
|---|---|
| **Image** | `nginx:alpine` |
| **Container** | `logera-nginx` |
| **Ports** | `80:80` |
| **Volumes** | `./nginx/nginx.conf:/etc/nginx/conf.d/default.conf:ro` |
| **Depends_on** | `web`, `app-front` |
| **Networks** | `logera-network` |
| **Restart** | `unless-stopped` |
| **Healthcheck** | нет |
| **Resource limits** | нет |

### 1.2 app-front (SvelteKit)
| Параметр | Значение |
|---|---|
| **Build** | `./app-front/Dockerfile` |
| **Image** | `logera/app-front:dev` |
| **Container** | `logera-app-front` |
| **Ports** | нет (через nginx) |
| **Environment** | `NODE_ENV=production`, `PUBLIC_API_BASE=http://nginx/api`, `ORIGIN=http://localhost` |
| **Networks** | `logera-network` |
| **Restart** | `unless-stopped` |
| **Healthcheck** | `wget -q --spider http://localhost:3000` — interval 30s, timeout 10s, retries 3, start_period 30s |

### 1.3 web (FastAPI Backend)
| Параметр | Значение |
|---|---|
| **Build** | `./back-end/Dockerfile`, arg `APP_PORT_ARG=${APP_PORT:-8000}` |
| **Image** | `logera/web:dev` |
| **Container** | `logera-back-end-dev` |
| **Ports** | нет (через nginx) |
| **Env_file** | `./back-end/.env` |
| **Volumes** | `./back-end:/app` (live reload) |
| **Depends_on** | `db` (service_healthy), `redis` (service_healthy) |
| **Networks** | `logera-network` |
| **Restart** | `unless-stopped` |
| **Healthcheck** | `curl -f http://localhost:${APP_PORT:-8000}/api/health` — interval 30s, timeout 10s, retries 3, start_period 40s |

### 1.4 db (PostgreSQL)
| Параметр | Значение |
|---|---|
| **Image** | `postgres:17.5-alpine` |
| **Container** | `logera-db-dev` |
| **Ports** | `127.0.0.1:${EXT_DB_PORT:-5433}:5432` |
| **Env_file** | `./back-end/.env` |
| **Environment** | `POSTGRES_USER=${POSTGRES_USER:-devuser}`, `POSTGRES_PASSWORD=${POSTGRES_PASSWORD:-devpass}`, `POSTGRES_DB=${POSTGRES_DB:-devdb}`, `POSTGRES_HOST_AUTH_METHOD=scram-sha-256` |
| **Volumes** | `postgres_data_logera_dev:/var/lib/postgresql/data` |
| **Networks** | `logera-network` |
| **Healthcheck** | `pg_isready -U $POSTGRES_USER -d $POSTGRES_DB` — interval 10s, timeout 5s, retries 5 |

### 1.5 redis
| Параметр | Значение |
|---|---|
| **Image** | `redis:7.2.4-alpine` |
| **Container** | `logera-redis-dev` |
| **Ports** | `${EXT_REDIS_PORT:-6380}:6379` |
| **Volumes** | `redis_data_logera_dev:/data` |
| **Command** | `redis-server --appendonly yes` |
| **Healthcheck** | `redis-cli ping` — interval 10s, timeout 5s, retries 5 |

### 1.6 minio (S3-compatible)
| Параметр | Значение |
|---|---|
| **Image** | `minio/minio:RELEASE.2023-09-07T02-05-02Z` |
| **Container** | `logera-minio-dev` |
| **Ports** | `9001:9001` (console) |
| **Environment** | `MINIO_ROOT_USER=${MINIO_ROOT_USER:-minioadmin}`, `MINIO_ROOT_PASSWORD=${MINIO_ROOT_PASSWORD:-minioadmin}` |
| **Volumes** | `minio_data_logera_dev:/data` |
| **Command** | `server /data --console-address ":9001"` |
| **Healthcheck** | `curl -f http://localhost:9000/minio/health/live` — interval 10s, timeout 5s, retries 5 |

### 1.7 rabbitmq
| Параметр | Значение |
|---|---|
| **Image** | `rabbitmq:3.13-management` |
| **Container** | `logera-rabbitmq-dev` |
| **Ports** | `5672:5672` (AMQP), `15672:15672` (management UI) |
| **Environment** | `RABBITMQ_DEFAULT_USER=${RABBITMQ_USER:-guest}`, `RABBITMQ_DEFAULT_PASS=${RABBITMQ_PASSWORD:-guest}` |
| **Healthcheck** | `rabbitmq-diagnostics -q ping` — interval 10s, timeout 5s, retries 5 |

### 1.8 qdrant (Vector DB)
| Параметр | Значение |
|---|---|
| **Image** | `qdrant/qdrant:latest` |
| **Container** | `logera-qdrant-dev` |
| **Ports** | `6333:6333` (HTTP), `6334:6334` (gRPC) |
| **Healthcheck** | нет |
| **Volumes** | нет (в prod), в dev — `qdrant_data_logera_dev:/qdrant/storage` |

### 1.9 opensearch
| Параметр | Значение |
|---|---|
| **Image** | `opensearchproject/opensearch:2.17.0` |
| **Container** | `logera-opensearch` |
| **Ports** | `9200:9200`, `9600:9600` |
| **Environment** | `discovery.type=single-node`, `bootstrap.memory_lock=true`, `OPENSEARCH_JAVA_OPTS=-Xms1g -Xmx1g`, `OPENSEARCH_INITIAL_ADMIN_PASSWORD=${OPENSEARCH_PASSWORD:-ddAs2@falAd}`, `plugins.security.disabled=true` |
| **Ulimits** | `memlock: soft=-1, hard=-1` |

### 1.10 opensearch_dashboards
| Параметр | Значение |
|---|---|
| **Image** | `opensearchproject/opensearch-dashboards:2.17.0` |
| **Container** | `logera-opensearch-dashboards` |
| **Ports** | `5601:5601` |
| **Environment** | `OPENSEARCH_HOSTS=["http://opensearch:9200"]`, `DISABLE_SECURITY_DASHBOARDS_PLUGIN=true` |
| **Depends_on** | `opensearch` (service_started) |

### 1.11 media_prep_worker
| Параметр | Значение |
|---|---|
| **Build** | context `.`, dockerfile `workers/media_prep/Dockerfile.cpu` |
| **Image** | `logera/media-prep:dev` |
| **Container** | `logera-media-prep-worker` |
| **Depends_on** | `rabbitmq` (healthy), `minio` (healthy) |
| **Env_file** | `./back-end/.env` |
| **Volumes** | `models_data_logera_dev:/models/noice_of` |
| **Healthcheck** | `curl -f http://localhost:8080/healthz` — interval 30s |
| **GPU** | нет (CPU) |

### 1.12 diarization_worker ⚡ GPU
| Параметр | Значение |
|---|---|
| **Platform** | `linux/amd64` |
| **Build** | `workers/diarization/Dockerfile.gpu` |
| **Image** | `logera/diarization:dev` |
| **Container** | `logera-diarization-worker` |
| **GPU** | `deploy.resources.reservations.devices: capabilities: ["gpu"]` |
| **Depends_on** | `rabbitmq` (healthy), `minio` (healthy) |
| **Env_file** | `./back-end/.env`, `.env.common`, `.env.diarization` |
| **Environment** | `DEVICE_TYPE=${DEVICE_TYPE:-cuda}` |
| **Volumes** | `models_data_logera_dev:/models` |
| **Healthcheck** | `curl -f http://localhost:8081/healthz` |

### 1.13 asr_worker ⚡ GPU + Resource Limits
| Параметр | Значение |
|---|---|
| **Platform** | `linux/amd64` |
| **Build** | `workers/asr/Dockerfile.gpu` |
| **Image** | `logera/asr:dev` |
| **Container** | `logera-asr-worker` |
| **GPU** | `deploy.resources.reservations.devices: capabilities: ["gpu"]` |
| **CPU Limits** | `limits: cpus '4.0'`, `reservations: cpus '2.0'` |
| **Depends_on** | `rabbitmq` (healthy), `minio` (healthy) |
| **Env_file** | `./back-end/.env`, `.env.common`, `.env.asr` |
| **Environment** | `DEVICE_TYPE=cuda`, `OMP_NUM_THREADS=4`, `MKL_NUM_THREADS=4`, `OPENBLAS_NUM_THREADS=4`, `TORCH_NUM_THREADS=4` |
| **Volumes** | `models_data_logera_dev:/models:ro` |
| **Healthcheck** | `curl -f http://localhost:8082/healthz` |

### 1.14 speaker_linking_worker
| Параметр | Значение |
|---|---|
| **Build** | `workers/speaker_linking/Dockerfile.cpu` |
| **Image** | `logera/speaker-linking:dev` |
| **Depends_on** | `rabbitmq` (healthy), `minio` (healthy), `qdrant` (started) |
| **Env_file** | `.env`, `.env.common`, `.env.speaker_linking` |
| **Volumes** | `hf_cache_logera_dev:/cache` |
| **Healthcheck** | `curl -f http://localhost:8083/healthz` |

### 1.15 indexer_worker
| Параметр | Значение |
|---|---|
| **Build** | `workers/indexer/Dockerfile.cpu` |
| **Depends_on** | `rabbitmq` (healthy), `minio` (healthy), `opensearch` (started) |
| **Env_file** | `.env`, `.env.common`, `.env.indexer` |
| **Healthcheck** | `curl -f http://localhost:8084/healthz` |

### 1.16 nlp_worker
| Параметр | Значение |
|---|---|
| **Platform** | `linux/amd64` |
| **Build** | `workers/nlp_adapter/Dockerfile.cpu` |
| **Depends_on** | `rabbitmq`, `minio`, `db`, `opensearch` |
| **Env_file** | `.env`, `.env.common` |
| **Environment** | `LITELLM_BASE_URL`, `LITELLM_API_KEY`, `LLM_MODEL=gpt-4o-mini`, `LLM_TIMEOUT_SEC=60`, `NLP_USE_ENHANCED`, `NLP_CONTEXT_ENABLED`, `NLP_PERSON_EXTRACTION_ENABLED`, `NLP_CONTEXT_MAX_RESULTS=20` |
| **Healthcheck** | `curl -f http://localhost:8085/healthz` |

### 1.17 cleanup_worker
| Параметр | Значение |
|---|---|
| **Build** | `workers/cleanup/Dockerfile` |
| **Depends_on** | `rabbitmq` (healthy), `minio` (healthy) |
| **Environment** | `CLEANUP_DELETE_PREPARED=true`, `CLEANUP_DELETE_CHUNKS=true`, `CLEANUP_DELETE_DIARIZATION=false` |
| **Healthcheck** | `curl -f http://localhost:8087/healthz` |

### 1.18 onlyoffice
| Параметр | Значение |
|---|---|
| **Image** | `onlyoffice/documentserver:8.2` |
| **Container** | `logera-onlyoffice` |
| **Ports** | `8443:443` |
| **Environment** | `JWT_ENABLED=true`, `JWT_SECRET=${ONLYOFFICE_JWT_SECRET:-logera-onlyoffice-secret}`, `JWT_HEADER=Authorization`, `JWT_IN_BODY=false` |
| **Volumes** | `onlyoffice_data:/var/www/onlyoffice/Data`, `onlyoffice_logs:/var/log/onlyoffice` |
| **Healthcheck** | `curl -f http://localhost/healthcheck` — start_period 60s |

### 1.19 rabbitmq_exporter
| Параметр | Значение |
|---|---|
| **Image** | `kbudde/rabbitmq-exporter:v0.29.0` |
| **Ports** | `9419:9419` |
| **Environment** | `RABBIT_URL=http://rabbitmq:15672`, `RABBIT_USER/PASSWORD`, `PUBLISH_PORT=9419` |

### 1.20 prometheus
| Параметр | Значение |
|---|---|
| **Image** | `prom/prometheus:v2.55.1` |
| **Ports** | `9090:9090` |
| **Volumes** | `prometheus.yml:ro`, `alerts.yml:ro` |
| **Command** | `--config.file=... --storage.tsdb.retention.time=15d` |

### 1.21 grafana
| Параметр | Значение |
|---|---|
| **Image** | `grafana/grafana:11.1.4` |
| **Ports** | `3000:3000` |
| **Depends_on** | `prometheus` (started) |
| **Environment** | `GF_SECURITY_ADMIN_USER/PASSWORD=${GRAFANA_ADMIN_USER:-admin}` |
| **Volumes** | `./back-end/monitoring/grafana/provisioning:/etc/grafana/provisioning:ro` |

---

## 2. Отличия compose-файлов

### 2.1 docker-compose.dev.yml

| Отличие | dev | prod (docker-compose.yml) |
|---|---|---|
| **Project name** | `logera-dev` | `logera` |
| **Nginx config** | `nginx.dev.conf` | `nginx.conf` |
| **Frontend Dockerfile** | `Dockerfile.dev` (Vite dev server) | `Dockerfile` (production build) |
| **Frontend port** | `5173:5173` (exposed) | нет (только через nginx) |
| **Frontend env** | `NODE_ENV=development`, `PUBLIC_SSR_API_BASE=http://web:8000` | `NODE_ENV=production` |
| **Frontend volumes** | `./app-front/src:/app/src:rw`, `./app-front/static:/app/static:rw` (hot reload) | нет |
| **Backend healthcheck** | uses `python -c "import urllib.request..."` | uses `curl -f` |
| **DB env** | из env_file, no defaults in compose | explicit defaults `devuser/devpass/devdb` |
| **Порты** | всё на `127.0.0.1:` (localhost only) | многое на `0.0.0.0` |
| **Qdrant volumes** | `qdrant_data_logera_dev:/qdrant/storage` | нет volume |
| **OpenSearch volumes** | `opensearch_data_logera_dev:/usr/share/opensearch/data` | нет volume |
| **OnlyOffice image** | `onlyoffice/documentserver-de:latest` | `onlyoffice/documentserver:8.2` |
| **GPU workers (diar)** | extra `PYTORCH_CUDA_ALLOC_CONF=max_split_size_mb:512`, `OMP_NUM_THREADS=4` | нет |
| **ASR CPU limits** | `6.0/3.0` | `4.0/2.0` |
| **Мониторинг** | отсутствует (нет prometheus/grafana/exporter) | есть |
| **NLP worker** | без env_common, без LiteLLM env vars | с LiteLLM, NLP feature flags |
| **Доп. volumes** | `qdrant_data_logera_dev`, `opensearch_data_logera_dev` | нет |
| **MinIO ports** | `127.0.0.1:9000:9000` + `127.0.0.1:9001:9001` | только `9001:9001` |

### 2.2 docker-compose.test.yml

| Отличие | Описание |
|---|---|
| **Project name** | `logera-test` |
| **Сеть** | `logera-test-network` (изолирована) |
| **Порты** | **никаких** — всё внутри сети |
| **test-runner** | Отдельный контейнер с pytest, зависит от ВСЕХ сервисов |
| **backend-test** | Отдельный backend с `APP_MODE=test`, `DEBUG=true` |
| **Все env** | hardcoded (не из файлов): `logera_test/logera_test/logera_test` |
| **Redis** | `--appendonly no --save ""` (без persistence) |
| **OpenSearch** | версия `2.11.0`, JVM `-Xms256m -Xmx256m` (минимум) |
| **Qdrant** | версия `v1.7.4` (pinned) |
| **GPU workers** | diarization/asr с `driver: nvidia, count: all` |
| **diarization-test** | `shm_size: '2g'` |
| **ASR model** | `WHISPER_MODEL=tiny` (лёгкая для тестов) |
| **Restart** | `"no"` для всех воркеров |
| **Volumes** | отдельные `*_test` volumes |

### 2.3 docker-compose.scale.yml (back-end/)

Overlay-файл для масштабирования ASR:
- Убирает `container_name` у `asr_worker` (чтобы можно было запускать несколько)
- Устанавливает `scale: 2` (2 параллельных ASR воркера)
- Использется: `docker-compose -f docker-compose.yml -f back-end/docker-compose.scale.yml up -d`

---

## 3. Nginx — полная конфигурация

### 3.1 nginx.conf (production)

**Upstreams:**
- `backend` → `web:8000`
- `frontend` → `app-front:3000`
- `onlyoffice` → `onlyoffice:80`

**Глобальные настройки:**
- `client_max_body_size 500M`

**Locations:**

| Location | Upstream | Особенности |
|---|---|---|
| `~ ^/api/v1/jobs/[^/]+/events$` | `backend` | **SSE**: `proxy_buffering off`, `proxy_cache off`, `proxy_read_timeout 24h`, `Connection ''`, `chunked_transfer_encoding off` |
| `/api/` | `backend` | WebSocket upgrade, `proxy_read_timeout 300s`, `proxy_connect_timeout 75s` |
| `/docs` | `backend` | OpenAPI Swagger UI |
| `/openapi.json` | `backend` | OpenAPI spec |
| `/redoc` | `backend` | ReDoc |
| `/onlyoffice/` | `onlyoffice` (trailing `/`) | WebSocket upgrade, `proxy_read_timeout 36000s` (10h), `X-Forwarded-Host $host/onlyoffice` |
| `/` | `frontend` | WebSocket upgrade для HMR |

### 3.2 nginx.dev.conf — отличия

| Отличие | Описание |
|---|---|
| `frontend` upstream | `app-front:5173` (Vite dev server вместо production :3000) |
| `map $http_upgrade` | Добавлен `$connection_upgrade` map для корректного HMR |
| `/` location | Использует `$connection_upgrade`, `proxy_read_timeout 86400` (24h) для Vite HMR WebSocket |

---

## 4. Мониторинг

### 4.1 Prometheus (prometheus.yml)

**Глобально:**
- `scrape_interval: 15s`
- `evaluation_interval: 15s`
- `rule_files: [alerts.yml]`

**Scrape targets:**

| Job | Target |
|---|---|
| `media_prep_worker` | `media_prep_worker:8080` |
| `diarization_worker` | `diarization_worker:8081` |
| `asr_worker` | `asr_worker:8082` |
| `speaker_linking_worker` | `speaker_linking_worker:8083` |
| `indexer_worker` | `indexer_worker:8084` |
| `rabbitmq` | `rabbitmq_exporter:9419` |
| `dcgm` | `dcgm_exporter:9400` (NVIDIA DCGM, не в compose — внешний) |

### 4.2 Alert Rules (alerts.yml)

**Group `logera-pipeline`:**

1. **StageHighLatencyP95** — severity: warning, for 10m
   - ASR p95 > 120s
   - Diarization p95 > 120s
   - Media prep p95 > 60s
   - Speaker linking p95 > 60s

2. **WebhookErrorRate** — severity: warning, for 5m
   - `webhook_requests_total{status!~"success|2.."}` > 0.05/s

**Group `rabbitmq`:**

3. **RabbitMQBacklogGrowing** — severity: warning, for 10m
   - `rabbitmq_queue_messages_ready` > 100

### 4.3 RabbitMQ Exporter

- **Image:** `kbudde/rabbitmq-exporter:v0.29.0`
- Подключается к RabbitMQ Management API (`http://rabbitmq:15672`)
- Экспортирует метрики на порт `9419`
- Метрики: `rabbitmq_queue_messages_ready`, `rabbitmq_queue_messages_unacked`, publish/deliver rates

### 4.4 Grafana Dashboards (5 штук)

**Datasource:** Prometheus (`http://prometheus:9090`), auto-provisioned.

**Dashboards (auto-provisioned из JSON):**

1. **Pipeline Overview**
   - Throughput (jobs/min) — stat panel
   - Webhook errors/min — stat panel
   - Stage p95 (s) — graph
   - ASR segments per job — graph
   - Indexed docs per job — graph

2. **Workers Overview**
   - Events rate (1m) — graph
   - Webhook requests — graph
   - Durations — graph
   - Average durations (5m) — graph

3. **GPU Overview**
   - GPU Utilization (%) — graph (из DCGM exporter)
   - Memory Used (MiB) — graph

4. **RabbitMQ Overview**
   - Messages ready / unacked — graph
   - Publish / Deliver rate — graph

5. **Webhooks Overview**
   - Webhook rate by endpoint/status — graph
   - Webhook p95 duration (s) — graph

---

## 5. Dockerfiles

### 5.1 app-front (Dockerfile — production)
- **Multi-stage:** builder (`node:20-alpine`) + production
- Builder: pnpm install, `NODE_OPTIONS=--max-old-space-size=4096`, `pnpm run build`
- Production: `node:20-alpine`, pnpm prod deps only, `node build`
- **Expose:** 3000

### 5.2 app-front (Dockerfile.dev)
- **Single stage:** `node:20-alpine`
- `pnpm install --frozen-lockfile`, `pnpm dev --host 0.0.0.0`
- **Expose:** 5173

### 5.3 back-end (Dockerfile)
- **Base:** `python:3.12.3-slim`
- **Build arg:** `APP_PORT_ARG=8000`
- **System deps:** gcc, libpq-dev, pandoc, wkhtmltopdf
- **User:** `appuser` (1000:1000) создан но не активирован (закомментирован)
- **Entrypoint:** `apply-migrations.sh` (применяет миграции при старте)
- **CMD:** `uvicorn app:app --host 0.0.0.0 --port 8000 --reload`
- **Expose:** 8000

### 5.4 ASR Worker (Dockerfile.gpu)
- **Base:** `pytorch/pytorch:2.7.1-cuda12.6-cudnn9-devel`
- **System deps:** ffmpeg, libsndfile1
- **Python deps:** fastapi, uvicorn, aio-pika, minio, openai-whisper, transformers, accelerate, sentencepiece, safetensors, prometheus-client, httpx
- **PyTorch:** Conditional install — CUDA для amd64, MPS для arm64
- **Оптимизации:** optimum, flash-attn (optional)
- **Модель:** Prefetch `dvislobokov/whisper-large-v3-turbo-russian` в образ при сборке
- **Shared package:** `packages/logera_common` installed as editable
- **Expose:** 8082
- **CMD:** `python -m asr.main`

### 5.5 Diarization Worker (Dockerfile.gpu)
- **Base:** `pytorch/pytorch:2.8.0-cuda12.8-cudnn9-runtime`
- **System deps:** ffmpeg, libsndfile1, libav* dev headers
- **Deps:** из `requirements.txt`, extra-index для torchcodec CUDA wheels
- **Expose:** 8081
- **CMD:** `python -m diarization.main`

### 5.6 Media Prep Worker (Dockerfile.cpu)
- **Base:** `python:3.11-slim`
- **System deps:** ffmpeg, build-essential, libsndfile1, libav* dev headers
- **Доп.:** Попытка установить runtime FFmpeg libs для разных версий (56-60)
- **Expose:** 8080
- **CMD:** `python -m media_prep.main`

### 5.7 NLP Adapter Worker (Dockerfile.cpu)
- **Base:** `python:3.11-slim`
- **System deps:** ffmpeg, libsndfile1
- **Expose:** 8085
- **CMD:** `python -m nlp_adapter.main`

### 5.8 Indexer Worker (Dockerfile.cpu)
- **Base:** `python:3.11-slim`
- **System deps:** ffmpeg, libsndfile1
- **Expose:** 8084
- **CMD:** `python -m indexer.main`

### 5.9 Speaker Linking Worker (Dockerfile.cpu)
- **Base:** `python:3.11-slim`
- **System deps:** ffmpeg, libsndfile1
- **Expose:** 8083
- **CMD:** `python -m speaker_linking.main`

### 5.10 Cleanup Worker (Dockerfile)
- **Base:** `python:3.11-slim`
- **Особенность:** `logera_common` установлен из копии (не editable), requirements отдельно
- **HEALTHCHECK** в Dockerfile (не только в compose): python requests
- **CMD:** `uvicorn main:app --host 0.0.0.0 --port 8087`
- **Expose:** 8087

### 5.11 Test Runner (tests/Dockerfile)
- **Base:** `python:3.11-slim`
- **Deps:** tests/requirements.txt + back-end/requirements.txt + logera_common
- **Fixtures:** реальные медиафайлы из `tests/integration/fixtures`
- **PYTHONPATH:** `/app/back-end:/app/workers:/app`
- **ENTRYPOINT:** `pytest`
- **CMD:** `tests/integration/ -v --tb=short`

---

## 6. Сети и Volumes

### 6.1 Networks

| Network | Driver | Используется в |
|---|---|---|
| `logera-network` | bridge | docker-compose.yml, docker-compose.dev.yml |
| `logera-test-network` | bridge | docker-compose.test.yml |

Все сервисы в одной bridge-сети. Общение по container name (DNS).

### 6.2 Volumes (production)

| Volume | Назначение | Используется |
|---|---|---|
| `postgres_data_logera_dev` | PostgreSQL data | db |
| `redis_data_logera_dev` | Redis AOF persistence | redis |
| `minio_data_logera_dev` | S3 object storage | minio |
| `models_data_logera_dev` | ML models (pyannote, whisper, embedding) | media_prep, diarization, asr |
| `hf_cache_logera_dev` | HuggingFace model cache | speaker_linking |
| `onlyoffice_data` | OnlyOffice document data | onlyoffice |
| `onlyoffice_logs` | OnlyOffice logs | onlyoffice |

### 6.3 Дополнительные volumes (dev)

| Volume | Назначение |
|---|---|
| `qdrant_data_logera_dev` | Qdrant vector storage |
| `opensearch_data_logera_dev` | OpenSearch indices |

### 6.4 Topology (data flow)

```
                          ┌─────────┐
                          │  nginx  │ :80
                          └────┬────┘
                     ┌─────────┼─────────┐
                     │         │         │
              ┌──────▼──┐ ┌───▼────┐ ┌──▼────────┐
              │app-front│ │  web   │ │onlyoffice │
              │ :3000   │ │ :8000  │ │ :443      │
              └─────────┘ └───┬────┘ └───────────┘
                         ┌────┼────┐
                    ┌────▼┐ ┌▼────┐│
                    │ db  │ │redis││
                    │:5432│ │:6379││
                    └─────┘ └─────┘│
                                   │
                    ┌──────────────▼──────────────┐
                    │         rabbitmq             │
                    │      :5672 / :15672           │
                    └──┬──┬──┬──┬──┬──┬───────────┘
                       │  │  │  │  │  │
              ┌────────▼┐ │  │  │  │  └────────────┐
              │media_prep│ │  │  │  │              │
              │ :8080   │ │  │  │  │              │
              └─────────┘ │  │  │  │              │
                  ┌───────▼┐ │  │  │              │
                  │diarize │ │  │  │              │
                  │ :8081  │ │  │  │              │
                  │ [GPU]  │ │  │  │              │
                  └────────┘ │  │  │              │
                     ┌───────▼┐ │  │              │
                     │  asr   │ │  │              │
                     │ :8082  │ │  │              │
                     │ [GPU]  │ │  │              │
                     └────────┘ │  │              │
                        ┌──────▼┐  │              │
                        │speaker│  │              │
                        │linking│  │              │
                        │:8083 │  │              │
                        └──┬───┘  │              │
                           │   ┌──▼────┐  ┌─────▼──┐
                      ┌────▼┐  │indexer│  │cleanup │
                      │qdrant│ │:8084  │  │:8087   │
                      │:6333│  └──┬───┘  └────────┘
                      └─────┘     │
                           ┌──────▼────┐
                           │opensearch │
                           │ :9200     │
                           └───────────┘
                    ┌──────────┐
                    │  minio   │ :9000/:9001
                    └──────────┘
            (used by all workers + web)

   Monitoring:
   rabbitmq_exporter:9419 ──► prometheus:9090 ──► grafana:3000
```

---

## 7. ENV Variables — полный список

### 7.1 .env.sample (back-end/.env)

| Variable | Default | Описание |
|---|---|---|
| `APP_MODE` | `development` | `development` / `production` / `test` |
| `PROJECT_VERSION` | `1.0.0` | Version string |
| `DEBUG` | `true` | Debug mode |
| `POSTGRES_HOST` | `localhost` | DB host |
| `POSTGRES_PORT` | `5432` | DB port |
| `POSTGRES_DB` | `oauth_server` | DB name |
| `POSTGRES_USER` | `postgres` | DB user |
| `POSTGRES_PASSWORD` | `postgres` | DB password |
| `REDIS_URL` | `redis://localhost:6379` | Redis URL |
| `JWT_SECRET_KEY` | — | JWT signing key (256-bit) |
| `JWT_ALGORITHM` | `HS256` | JWT algorithm |
| `JWT_ACCESS_TOKEN_EXPIRE_MINUTES` | `30` | Access token TTL |
| `JWT_REFRESH_TOKEN_EXPIRE_DAYS` | `7` | Refresh token TTL |
| `OAUTH_CLIENT_ID` | `default_client` | OAuth client ID |
| `OAUTH_CLIENT_SECRET` | `default_secret` | OAuth client secret |
| `ALLOWED_HOSTS` | `localhost,127.0.0.1` | Allowed hosts |
| `CORS_ORIGINS` | `http://localhost:3000,...` | CORS origins |
| `LOG_LEVEL` | `INFO` | Log level |
| `LOG_FORMAT` | `json` | Log format |
| `RATE_LIMIT_REQUESTS_PER_MINUTE` | `100` | API rate limit |
| `RATE_LIMIT_AUTH_REQUESTS_PER_MINUTE` | `10` | Auth rate limit |
| `SMTP_HOST` | `smtp.gmail.com` | SMTP host |
| `SMTP_PORT` | `587` | SMTP port |
| `SMTP_USER` | — | SMTP user |
| `SMTP_PASSWORD` | — | SMTP password |
| `SMTP_FROM_NAME` | `OAuth Server` | Email sender name |
| `ENABLE_METRICS` | `true` | Prometheus metrics |
| `ENABLE_HEALTH_CHECK` | `true` | Health endpoint |
| `RELOAD` | `true` | Uvicorn auto-reload |
| `WORKERS` | `1` | Uvicorn workers |

### 7.2 .env.common (all workers)

| Variable | Описание |
|---|---|
| `HUGGING_FACE_TOKEN` / `HF_TOKEN` | HuggingFace API token |
| `CUDA_VISIBLE_DEVICES` | `0` — GPU index |
| `SPEAKER_EMB_MODEL_PATH` | `/models/embedding` |
| `SPEAKER_EMB_MODEL_ID` | `speechbrain/spkrec-ecapa-voxceleb` |
| `SPEAKER_EMB_VECTOR_SIZE` | `192` |
| `SPEAKER_EMB_MIN_DURATION` | `1.0` sec |
| `NLP_USE_ENHANCED` | `true` |
| `WEBHOOK_URLS` | `http://web:8000/api/internal/hooks/logera` |
| `WEBHOOK_SECRET` | (пусто) |
| `AMQP_PREFETCH_COUNT` | `16` |
| `OPENSEARCH_PASSWORD` | `ddAs2@falAd` |

### 7.3 .env.asr

| Variable | Value | Описание |
|---|---|---|
| `WHISPER_BACKEND` | `hf` | HuggingFace backend |
| `WHISPER_HF_MODEL_ID` | `dvislobokov/whisper-large-v3-turbo-russian` | ASR model |
| `WHISPER_HF_REVISION` | `main` | Model revision |
| `WHISPER_HF_LOCAL_DIR` | `/app/models/hf/whisper-large-v3-turbo-russian` | Local model path |
| `ASR_ATTN_IMPL` | `sdpa` | Attention implementation |
| `WHISPER_8BIT` | `0` | 8-bit quantization off |
| `ASR_BATCH_SIZE` | `12` | Batch size |
| `ASR_BATCH_SIZE_BEAMS` | `4` | Beam batch |
| `ASR_BEAM_SIZE` | `2` | Beam search width |
| `ASR_TORCH_COMPILE` | `1` | torch.compile enabled |
| `ASR_USE_FLASH_ATTENTION` | `1` | Flash Attention |
| `ASR_EMPTY_CACHE_INTERVAL` | `10` | CUDA cache clear interval |
| `ASR_TORCH_COMPILE_MODE` | `reduce-overhead` | Compile mode |
| `AMQP_PREFETCH_COUNT` | `64` | Override from common |
| `ASR_MAX_NEW_TOKENS` | `300` | Max output tokens |
| `ASR_FORCE_LANGUAGE` | `ru` | Force Russian |
| `ASR_CONDITION_ON_PREV` | `1` | Use prev context |
| `ASR_REPETITION_PENALTY` | `1.2` | Repetition penalty |
| `ASR_NO_REPEAT_NGRAM` | `2` | No-repeat n-gram |
| `ASR_PROMPT_PREFIX` | (long prompt) | System prompt |
| `ASR_HOTWORDS` | `хотфикс,мердж-реквест,...` | Boosted words |
| `ASR_HOTWORDS_BOOST` | `1.0` | Boost factor |
| `ASR_NO_SPEECH_THRESHOLD` | `0.92` | Quality threshold |
| `ASR_LOGPROB_THRESHOLD` | `-0.35` | Quality threshold |
| `ASR_COMPRESSION_RATIO_THRESHOLD` | `2.4` | Quality threshold |
| `ASR_PAD_SEC` | `0.15` | Segment padding |
| `ASR_DEDUP_SENSITIVITY` | `0.85` | Dedup threshold |
| `TRANSFORMERS_NO_TORCHVISION` | `1` | Skip torchvision |
| `TRANSFORMERS_OFFLINE` | `0` | Allow downloads |

### 7.4 .env.diarization

| Variable | Value | Описание |
|---|---|---|
| `PYANNOTE_PIPELINE_PATH` | `/models/pyannote` | Pyannote model path |
| `DIA_MIN_SEGMENT_SEC` | `0.35` | Min segment duration |
| `DIA_MERGE_GAP_SEC` | `0.5` | Merge gap |
| `DIA_MERGE_DUR_MAX` | `25` | Max merged duration |
| `DIA_MIN_SPEAKERS` | `2` | Min speakers |
| `DIA_MAX_SPEAKERS` | `24` | Max speakers |
| `DIA_CLUSTERING_THRESHOLD` | `0.5` | Clustering threshold |
| `DIA_GLOBAL_CLUSTERING_DISTANCE` | `0.75` | Global distance |
| `DIA_WINDOW_DURATION` | `20.0` | Window size (sec) |
| `DIA_WINDOW_HOP` | `10.0` | Window hop (sec) |
| `USE_COMMUNITY_PIPELINE` | `true` | Use community pipeline |
| `USE_MENTOR_VAD` | `true` | Mentor VAD |
| `MENTOR_VAD_ONSET` | `0.7` | VAD onset |
| `MENTOR_VAD_OFFSET` | `0.45` | VAD offset |
| `MENTOR_AHC_DISTANCE_THRESHOLD` | `0.9` | AHC distance |
| `HF_HOME` | `/models/hf` | HF cache |
| `HF_HUB_OFFLINE` | `0` | Allow downloads |

### 7.5 .env.indexer

| Variable | Value |
|---|---|
| `OPENSEARCH_URL` | `http://opensearch:9200` |
| `OPENSEARCH_USERNAME` | `admin` |
| `OPENSEARCH_PASSWORD` | `ddAs2@falAd` |
| `OPENSEARCH_INDEX_PREFIX` | `asr_segments` |

### 7.6 .env.speaker_linking

| Variable | Value |
|---|---|
| `QDRANT_URL` | `http://qdrant:6333` |
| `SPEAKER_EMB_MODEL_PATH` | `/cache/embedding` |
| `SPEAKER_EMB_MODEL_ID` | `speechbrain/spkrec-ecapa-voxceleb` |
| `SPEAKER_EMB_VECTOR_SIZE` | `192` |
| `SPEAKER_EMB_MIN_DURATION` | `1.0` |
| `HF_HOME` | `/cache/hf` |
| `HF_HUB_ENABLE_XET` | `0` |

### 7.7 Compose-level env vars (from host/defaults)

| Variable | Default | Used by |
|---|---|---|
| `APP_PORT` | `8000` | web |
| `EXT_DB_PORT` | `5433` | db |
| `EXT_REDIS_PORT` | `6380` | redis |
| `MINIO_ROOT_USER` | `minioadmin` | minio |
| `MINIO_ROOT_PASSWORD` | `minioadmin` | minio |
| `RABBITMQ_USER` | `guest` | rabbitmq |
| `RABBITMQ_PASSWORD` | `guest` | rabbitmq |
| `OPENSEARCH_PASSWORD` | `ddAs2@falAd` | opensearch |
| `DEVICE_TYPE` | `cuda` | diarization, asr |
| `ONLYOFFICE_JWT_SECRET` | `logera-onlyoffice-secret` | onlyoffice |
| `GRAFANA_ADMIN_USER` | `admin` | grafana |
| `GRAFANA_ADMIN_PASSWORD` | `admin` | grafana |
| `LITELLM_BASE_URL` | `http://litellm:4000` | nlp_worker |
| `LITELLM_API_KEY` | `sk-1234` | nlp_worker |
| `LLM_MODEL` | `gpt-4o-mini` | nlp_worker |
| `LLM_TIMEOUT_SEC` | `60` | nlp_worker |
| `NLP_USE_ENHANCED` | `false` | nlp_worker |
| `NLP_CONTEXT_ENABLED` | `true` | nlp_worker |
| `NLP_PERSON_EXTRACTION_ENABLED` | `true` | nlp_worker |
| `NLP_CONTEXT_MAX_RESULTS` | `20` | nlp_worker |

### 7.8 Frontend (.env.example)

| Variable | Value |
|---|---|
| `DATABASE_URL` | `postgres://root:mysecretpassword@localhost:5432/local` |

---

## 8. Общая сводка

| Метрика | Значение |
|---|---|
| **Всего сервисов (prod)** | 21 |
| **GPU-сервисы** | 2 (asr, diarization) |
| **CPU-воркеры** | 5 (media_prep, speaker_linking, indexer, nlp, cleanup) |
| **Инфра-сервисы** | 8 (nginx, db, redis, minio, rabbitmq, qdrant, opensearch, opensearch_dashboards) |
| **Бизнес-сервисы** | 3 (web, app-front, onlyoffice) |
| **Мониторинг** | 3 (prometheus, grafana, rabbitmq_exporter) |
| **Named volumes (prod)** | 7 |
| **Named volumes (dev)** | 9 |
| **Grafana dashboards** | 5 |
| **Alert rules** | 3 |
| **Env files** | 6 (.env, .env.common, .env.asr, .env.diarization, .env.indexer, .env.speaker_linking) |
