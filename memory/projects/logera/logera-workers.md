# Logera Media Pipeline — Детальная документация воркеров

> Ветка: `feature/design-improvements` | Дата анализа: 2026-02-14

---

## Оглавление

1. [Архитектура pipeline](#архитектура-pipeline)
2. [Workers](#workers)
   - [media_prep](#1-media_prep)
   - [diarization](#2-diarization)
   - [asr](#3-asr)
   - [speaker_linking](#4-speaker_linking)
   - [nlp_adapter](#5-nlp_adapter)
   - [indexer](#6-indexer)
   - [cleanup](#7-cleanup)
3. [packages/logera_common](#packageslogera_common)
4. [Pipeline Flow](#pipeline-flow)
5. [Тесты](#тесты)

---

## Архитектура pipeline

```
job.created ──► media_prep ──► diarization ──┬──► asr ──┬──► nlp_adapter
                                             │          │
                                             │          └──► indexer ──► cleanup
                                             │
                                             └──► speaker_linking
```

**AMQP Exchange:** `logera.jobs` (topic, durable)
**DLX Exchange:** `logera.dlx` (topic, durable)

| Воркер | Queue | Слушает routing key | Публикует routing key | Health Port | GPU |
|--------|-------|--------------------|-----------------------|-------------|-----|
| media_prep | `q.media_prep` | `job.created` | `media.prepared` | 8081 | ❌ |
| diarization | `q.diarization` | `media.prepared` | `dia.ready` | 8081 | ✅ |
| asr | `q.asr` | `dia.ready` | `asr.ready` | 8082 | ✅ |
| speaker_linking | `q.speaker_linking` | `dia.ready` | `link.ready` | 8084 | ❌ |
| nlp_adapter | `q.nlp_adapter` | `asr.ready` | `nlp.ready` | 8085 | ❌ |
| indexer | `q.indexer` | `asr.ready` | `indexed.ready` | 8085 | ❌ |
| cleanup | `q.cleanup` | `indexed.ready` | — | 8087 | ❌ |

**Параллельные ветки после `dia.ready`:** ASR и speaker_linking работают параллельно.
**Параллельные ветки после `asr.ready`:** NLP adapter и indexer работают параллельно.

---

## Workers

### 1. media_prep

**Назначение:** Подготовка исходного медиафайла — конвертация в 16kHz mono WAV, VAD (Voice Activity Detection), создание логического манифеста чанков.

#### Точка входа
- `workers/media_prep/main.py` → `FastAPI` app + AMQP consumer
- CMD: `python -m media_prep.main`
- Dockerfile: `workers/media_prep/Dockerfile.cpu` (Python 3.11-slim)

#### AMQP
- **Queue:** `q.media_prep`
- **Routing key (consume):** `job.created`
- **Routing key (publish):** `media.prepared`

#### Модель входного события (`JobCreated`)
```python
class JobCreated(BaseModel):
    type: str = "job.created"
    job_id: str
    org_id: int
    node_id: int
    version: int
    storage_key: str        # путь к исходному файлу в MinIO (e.g. "originals/100/meeting.mp4")
    mime: str               # MIME-type (e.g. "video/mp4", "audio/wav")
    created_by: int | None
    owner_user_id: int | None
    project_scope_id: int | None
    idempotency_key: str    # формат "{org_id}:{node_id}:{version}"
    timestamp: str
```

#### Алгоритм пошагово

1. **Чтение исходного файла** — `logera_minio_read(minio, org_id, storage_key)` → bytes
2. **Конвертация в 16kHz WAV** — `ffmpeg_extract_wav16k(original_bytes)`:
   - Через `ffmpeg-python`: input → output(ar=16000, ac=1, acodec='pcm_s16le', format='wav')
   - Используются temp-файлы для ffmpeg
3. **Декодирование в numpy** — `soundfile.read(wav_bytes, dtype='float32')`, mono
4. **VAD (Silero)** — `run_silero_vad(wav16k_bytes, sample_rate=16000, threshold)`:
   - Загружает Silero VAD через `torch.hub.load('snakers4/silero-vad')`
   - Модель кэшируется глобально (`_silero`)
   - Возвращает список `(start_s, end_s)` интервалов речи
5. **Merge overlapping intervals** — `_merge_intervals(vad_intervals)`
6. **Создание логических чанков** — фильтрует интервалы < 1.0 сек, формирует manifest `[{index, start_s, end_s, duration}]`
7. **Сохранение в MinIO:**
   - `prepared/{node_id}/audio.wav` — 16kHz mono WAV (metadata: org_id, node_id, version, sample_rate, channels, duration_s)
   - `prepared/{node_id}/chunks.json` — JSON manifest (metadata: org_id, node_id, version, chunks_count)
8. **Публикация `media.prepared`** через `safe_publish`

#### Выходное событие
```json
{
  "type": "media.prepared",
  "event_version": 1,
  "job_id": "uuid",
  "org_id": 1,
  "node_id": 100,
  "version": 1,
  "owner_user_id": null,
  "project_scope_id": null,
  "prepared_key": "prepared/100/audio.wav",
  "chunks_manifest_key": "prepared/100/chunks.json",
  "finished_at": "ISO-8601"
}
```

#### Артефакты в MinIO

| Путь | Content-Type | Описание |
|------|-------------|----------|
| `prepared/{node_id}/audio.wav` | `audio/wav` | 16kHz mono WAV |
| `prepared/{node_id}/chunks.json` | `application/json` | VAD intervals manifest |

#### Конфигурация (ENV)

| Переменная | Default | Описание |
|------------|---------|----------|
| `MEDIA_PREP_VAD_THRESHOLD` | `0.5` | Порог Silero VAD |
| `MEDIA_PREP_USE_AFFTDN` | `true` | Denoise фильтр (в config.py) |
| `MEDIA_PREP_USE_LOUDNORM` | `true` | Нормализация громкости (в config.py) |

#### Prometheus метрики

| Метрика | Тип | Описание |
|---------|-----|----------|
| `media_prep_events_total` | Counter | Обработанные job.created |
| `media_prep_duration_seconds` | Histogram | Время обработки (buckets: 0.5–300s) |

#### Health Check
- `GET /healthz` → `{"status": "ok", "time": "..."}`
- `GET /readyz` → `{"status": "ready"}`
- `GET /metrics` → Prometheus text

#### Error Handling
- Ошибка чтения из MinIO → `logger.error`, return (без re-raise)
- Все прочие ошибки → `logger.error`, без публикации error-event (TODO в коде)
- Consumer auto-restart: `while True` → `consume()` → `except: sleep(5)`

#### Зависимости (requirements.txt)
```
fastapi==0.115.12, uvicorn, aio-pika==9.4.3, minio==7.2.7, pydantic==2.11.5,
pydantic-settings==2.9.1, soundfile==0.12.1, webrtcvad==2.0.10, numpy==1.26.4,
ffmpeg-python==0.2.0, prometheus-client==0.22.0, torch==2.7.1, torchaudio==2.7.1
```

#### Dockerfile
- Base: `python:3.11-slim`
- System deps: ffmpeg, build-essential, libsndfile1, libav*-dev
- FFmpeg runtime libs installed best-effort для torio compat
- Expose: 8080
- CMD: `python -m media_prep.main`

---

### 2. diarization

**Назначение:** Speaker diarization — определение временных границ речи каждого спикера + глобальная кластеризация embeddings.

#### Точка входа
- `workers/diarization/main.py` → FastAPI + AMQP consumer
- CMD: `python -m diarization.main`
- Dockerfile: `workers/diarization/Dockerfile.gpu` (pytorch/pytorch:2.8.0-cuda12.8-cudnn9-runtime)

#### AMQP
- **Queue:** `q.diarization`
- **Routing key (consume):** `media.prepared`
- **Routing key (publish):** `dia.ready`

#### Модель входного события (`MediaPrepared`)
```python
class MediaPrepared(BaseModel):
    type: str = "media.prepared"
    event_version: int = 1
    job_id: str
    org_id: int
    node_id: int
    version: int
    owner_user_id: int | None
    project_scope_id: int | None
    prepared_key: str               # "prepared/{node_id}/audio.wav"
    chunks_manifest: list[dict] | None
    chunks_manifest_key: str | None # "prepared/{node_id}/chunks.json"
```

#### Алгоритм пошагово

1. **Загрузка chunks manifest** — если `chunks_manifest` = None, читает из MinIO по `chunks_manifest_key`
2. **Загрузка prepared audio** — `read_prepared_wav()` → `(torch.Tensor, sr)`
3. **Выбор pipeline** на основе ENV:

   **A) Community Pipeline** (`USE_COMMUNITY_PIPELINE=true`):
   - Загружает `pyannote/speaker-diarization-community-1`
   - Запускает `pipeline({"waveform": tensor, "sample_rate": sr}, **constraints)`
   - Constraints: `num_speakers`, `min_speakers`, `max_speakers` из ENV
   - Итерирует `diarization.itertracks(yield_label=True)` → segments

   **B) Mentor VAD** (`USE_MENTOR_VAD=true`):
   - Загружает `pyannote/segmentation-3.0` как VoiceActivityDetection
   - Получает `speech_timeline` → сегменты без спикеров

   **C) Window-based (default)**:
   - `generate_windows_from_chunks(manifest)` → sliding windows (default 20s window, 10s hop)
   - Для каждого окна:
     - Вырезает waveform из full audio по timestamps
     - Запускает `pyannote/speaker-diarization-community-1` pipeline
     - Конвертирует результат в абсолютные timestamps (offset)
   - Pipeline кэшируется глобально (`_pipeline_cache`)

4. **Global Speaker Linking** — `_perform_global_speaker_linking(all_segments, waveform, sr)`:
   - Извлекает embeddings для каждого сегмента (duration >= `SPEAKER_EMB_MIN_DURATION`)
   - **Clustering:** AgglomerativeClustering (cosine, average linkage)
     - Порог: `DIA_GLOBAL_CLUSTERING_DISTANCE` (default 0.75)
   - **Multi-step refinement:**
     - Core selection по coverage threshold (default 90%)
     - Reassignment мелких кластеров к ближайшим core (threshold `DIA_CLUSTER_REASSIGN_DISTANCE` 0.25)
     - Secondary clustering core центроидов (threshold `DIA_SECONDARY_CLUSTER_DISTANCE` 0.4)
     - Финальные группы → `SPEAKER_01`, `SPEAKER_02`, ...
   - Pending segments (too short for embedding) → nearest centroid assignment

5. **Merge close segments** (optional, `DIA_ENABLE_MERGE=1`) — `_merge_close_same_speaker(max_gap=0.5, max_duration=30.0)`

6. **Mentor post-processing** (optional, `USE_MENTOR_POSTPROCESSING=true`):
   - Фильтрация спикеров с total duration < `MENTOR_MIN_SPEAKER_DURATION`

7. **Фильтрация** — удаление сегментов < `DIA_MIN_SEGMENT_DURATION` (default 0.5s)

8. **Сохранение в MinIO:** `diarization/{node_id}/segments.jsonl` (JSONL)

9. **Публикация `dia.ready`**

#### Выходное событие
```json
{
  "type": "dia.ready",
  "event_version": 1,
  "job_id": "uuid",
  "org_id": 1,
  "node_id": 100,
  "version": 1,
  "owner_user_id": null,
  "project_scope_id": null,
  "diarization_key": "diarization/100/segments.jsonl",
  "prepared_key": "prepared/100/audio.wav",
  "chunks_manifest": [...],
  "finished_at": "ISO-8601"
}
```

#### Формат segments.jsonl
```jsonl
{"start": 0.5, "end": 3.2, "speaker_label": "SPEAKER_01"}
{"start": 3.2, "end": 7.8, "speaker_label": "SPEAKER_02"}
```

#### Артефакты в MinIO

| Путь | Content-Type | Описание |
|------|-------------|----------|
| `diarization/{node_id}/segments.jsonl` | `application/jsonl` | Сегменты со спикерами |

#### Модели ML

| Модель | Назначение |
|--------|-----------|
| `pyannote/speaker-diarization-community-1` | Основная диаризация |
| `pyannote/speaker-diarization-3.1` | Full pipeline (альтернатива) |
| `pyannote/segmentation-3.0` | VAD (Mentor mode) |
| `pyannote/voice-activity-detection` | OSD intervals |
| `speechbrain/spkrec-ecapa-voxceleb` | Speaker embeddings (legacy) |
| `pyannote/embedding` | Speaker embeddings (Mentor mode) |

#### Конфигурация (ENV)

| Переменная | Default | Описание |
|------------|---------|----------|
| `DIA_MIN_SPEAKERS` | `1` | Мин. спикеров для pipeline |
| `DIA_MAX_SPEAKERS` | `24` | Макс. спикеров |
| `DIA_GLOBAL_CLUSTERING_DISTANCE` | `0.75` | Порог AgglomerativeClustering |
| `DIA_CLUSTER_COVERAGE` | `0.9` | Coverage threshold для core selection |
| `DIA_CLUSTER_REASSIGN_DISTANCE` | `0.25` | Порог reassignment мелких кластеров |
| `DIA_SECONDARY_CLUSTER_DISTANCE` | `0.4` | Порог secondary clustering |
| `DIA_MIN_CLUSTER_DURATION` | `1.5` | Мин. длительность кластера |
| `DIA_MIN_SEGMENT_DURATION` | `0.5` | Мин. длительность финального сегмента |
| `DIA_WINDOW_DURATION` | `20.0` | Длительность sliding window |
| `DIA_WINDOW_HOP` | `10.0` | Hop sliding window |
| `DIA_MIN_WINDOW` | `3.0` | Мин. длительность финального окна |
| `DIA_ENABLE_MERGE` | `0` | Merge close same-speaker segments |
| `DIA_MODE` | `annotation` | Режим: annotation/osd |
| `DIA_CLUSTERING_THRESHOLD` | `0.6` | Порог clustering в pyannote pipeline |
| `USE_COMMUNITY_PIPELINE` | `false` | Использовать community pipeline |
| `USE_MENTOR_VAD` | `false` | Mentor VAD mode |
| `USE_MENTOR_CLUSTERING` | `false` | Mentor single-step AHC |
| `USE_MENTOR_POSTPROCESSING` | `false` | Mentor post-processing |
| `USE_MENTOR_EMBEDDINGS` | `false` | pyannote/embedding вместо speechbrain |
| `MENTOR_AHC_DISTANCE_THRESHOLD` | `0.6` | Порог Mentor AHC |
| `MENTOR_MIN_SPEAKER_DURATION` | `2.0` | Мин. duration для speaker filtering |
| `SPEAKER_EMB_MIN_DURATION` | `0.5` | Мин. duration для embedding extraction |
| `SPEAKER_EMB_MODEL_ID` | `speechbrain/spkrec-ecapa-voxceleb` | Embedding модель |
| `HF_TOKEN` | (required) | HuggingFace token для pyannote |
| `DEVICE_TYPE` | `cpu` | `cuda`/`mps`/`cpu` |

#### Prometheus метрики

| Метрика | Тип | Описание |
|---------|-----|----------|
| `dia_events_total` | Counter | Events dia.ready |
| `dia_duration_seconds` | Histogram | Duration (buckets: 0.5–1200s) |
| `webhook_requests_total` | Counter | Webhook requests (labels: endpoint, status) |
| `webhook_request_duration_seconds` | Histogram | Webhook latency |

#### Health Check
- `GET /healthz`, `GET /readyz`, `GET /metrics`

#### Error Handling
- Consumer auto-restart (`while True` + `sleep(5)`)
- Webhook отправка async в background (`asyncio.create_task`)

#### Зависимости
```
torch==2.8.0, torchaudio==2.8.0, pyannote.audio==4.0.3, speechbrain==1.0.3,
scikit-learn==1.7.2, numpy==2.3.3, soundfile==0.13.1, fastapi, uvicorn, aio-pika,
minio, prometheus-client, httpx
```

#### Dockerfile
- Base: `pytorch/pytorch:2.8.0-cuda12.8-cudnn9-runtime`
- `--extra-index-url https://download.pytorch.org/whl/cu128` для torchcodec
- Expose: 8081

---

### 3. asr

**Назначение:** Speech-to-text транскрибация каждого сегмента из diarization с помощью Whisper.

#### Точка входа
- `workers/asr/main.py` → FastAPI + AMQP consumer
- CMD: `python -m asr.main`
- Dockerfile: `workers/asr/Dockerfile.gpu` (pytorch/pytorch:2.7.1-cuda12.6-cudnn9-devel)

#### AMQP
- **Queue:** `q.asr`
- **Routing key (consume):** `dia.ready`
- **Routing key (publish):** `asr.ready`

#### Модель входного события (`DiaReady`)
```python
class DiaReady(BaseModel):
    type: str = "dia.ready"
    event_version: int = 1
    job_id: str
    org_id: int
    node_id: int
    version: int
    owner_user_id: int | None
    project_scope_id: int | None
    prepared_key: str | None          # "prepared/{node_id}/audio.wav"
    diarization_key: str              # "diarization/{node_id}/segments.jsonl"
    chunks_manifest: List[dict] | None
```

#### Алгоритм пошагово

1. **Чтение diarization segments** — `read_diarization_json()` → JSONL → `[{start, end, speaker_label}]`
2. **Загрузка prepared audio в память** — `read_wav()` → `(np.ndarray, sr)` — ОДИН РАЗ
3. **Загрузка Whisper модели** — `load_whisper()`:
   - Backend: `WHISPER_BACKEND` = `hf` (default) или OpenAI whisper
   - HF backend: `transformers.pipeline("automatic-speech-recognition")` с `HFASRAdapter`
   - Модель: `dvislobokov/whisper-large-v3-turbo-russian` (или `WHISPER_HF_MODEL_ID`)
   - Prefetched в Docker image: `/app/models/hf/whisper-large-v3-turbo-russian`
   - Thread-safe initialization (`_model_lock`)
   - Supports: 8-bit quantization, FlashAttention-2, BetterTransformer, torch.compile
   - Warmup при startup (1 sec silence)

4. **Normalize & merge diarization segments:**
   - `normalize_segments()` — валидация, сортировка
   - `filter_short_overlaps()` — разрешение коротких overlap (< 1s) по longest containing speaker
   - `merge_speaker_segments()` — merge consecutive segments same speaker (gap ≤ `ASR_MERGE_GAP_MAX` 1.5s, duration ≤ `ASR_MERGE_DUR_MAX` 25s)

5. **Smart batching by duration:**
   - Bucket 0: ≤ 2s, Bucket 1: ≤ 5s, Bucket 2: ≤ 10s, Bucket 3: > 10s
   - Batch size: `ASR_BATCH_SIZE` (default 16)

6. **Для каждого batch:**
   - `extract_audio_for_interval(start, end, pad)` — numpy slicing из waveform в памяти (pad = `ASR_PAD_SEC` 0.15s)
   - `model.transcribe_batch()`:
     - `language`: `ASR_FORCE_LANGUAGE` (default `ru`, `auto` для автодетекта)
     - `beam_size`: `ASR_BEAM_SIZE` (default 1)
     - `initial_prompt`: `ASR_PROMPT_PREFIX` + `ASR_HOTWORDS`
     - Hotwords через: sequence_bias → LogitsProcessorList → force_words_ids
     - Repetition control: `ASR_REPETITION_PENALTY` (1.1), `ASR_NO_REPEAT_NGRAM` (2)
     - `max_new_tokens`: budget_guard (respects prompt_ids length, max 448 positions)

7. **Quality Control** per segment:
   - `avg_logprob` ≥ `ASR_MIN_AVG_LOGPROB` (-0.25)
   - `compression_ratio` ≤ `ASR_MAX_COMPRESSION` (2.4)
   - `no_speech_prob` ≤ `ASR_MAX_NO_SPEECH` (0.85)
   - chars/sec ≤ `ASR_MAX_CHARS_PER_SEC` (14.0)
   - repetition ratio ≤ `ASR_MAX_REPETITION` (0.6)

8. **Retry failed segments** с beam search (`ASR_BATCH_SIZE_BEAMS` default 4), более мягкие пороги

9. **Deduplication** — `_dedup_overlaps(outputs, sensitivity=0.85)` — удаляет overlap суффикс/префикс

10. **Сохранение в MinIO:** `asr/{node_id}/segments.jsonl`

11. **Публикация `asr.ready`**, webhooks в background

#### Выходное событие
```json
{
  "type": "asr.ready",
  "event_version": 1,
  "job_id": "uuid",
  "org_id": 1,
  "node_id": 100,
  "version": 1,
  "owner_user_id": null,
  "project_scope_id": null,
  "segments_key": "asr/100/segments.jsonl",
  "finished_at": "ISO-8601"
}
```

#### Формат segments.jsonl
```jsonl
{"start": 0.5, "end": 3.2, "speaker_label": "SPEAKER_01", "text": "Добрый день.", "merged": false, "num_parts": 1, "overlap_long": false, "source": "prepared", "pad_ms": 150}
```

#### Артефакты в MinIO

| Путь | Content-Type | Описание |
|------|-------------|----------|
| `asr/{node_id}/segments.jsonl` | `application/jsonl` | Сегменты с текстом |

#### Конфигурация (ENV)

| Переменная | Default | Описание |
|------------|---------|----------|
| `WHISPER_BACKEND` | `hf` | `hf` или OpenAI whisper |
| `WHISPER_HF_MODEL_ID` | `dvislobokov/whisper-large-v3-turbo-russian` | HF модель |
| `WHISPER_HF_LOCAL_DIR` | `/app/models/hf/whisper-large-v3-turbo-russian` | Локальный путь |
| `ASR_BEAM_SIZE` | `1` | Beam size (1 = greedy) |
| `ASR_BATCH_SIZE` | `16` | Batch size inference |
| `ASR_BATCH_SIZE_BEAMS` | `4` | Beam size для retry |
| `ASR_PAD_SEC` | `0.15` | Padding сегментов |
| `ASR_FORCE_LANGUAGE` | `ru` | Язык (auto для автодетекта) |
| `ASR_PROMPT_PREFIX` | `` | Prompt prefix |
| `ASR_HOTWORDS` | `` | Ключевые слова (CSV) |
| `ASR_HOTWORDS_BOOST` | `0` | Boost factor для hotwords |
| `ASR_MERGE_GAP_MAX` | `1.5` | Max gap для merge |
| `ASR_MERGE_DUR_MAX` | `25.0` | Max duration merged segment |
| `ASR_MIN_AVG_LOGPROB` | `-0.25` | QC: min avg logprob |
| `ASR_MAX_COMPRESSION` | `2.4` | QC: max compression ratio |
| `ASR_MAX_NO_SPEECH` | `0.85` | QC: max no_speech_prob |
| `ASR_MAX_CHARS_PER_SEC` | `14.0` | QC: max chars/sec |
| `ASR_MAX_REPETITION` | `0.6` | QC: max repetition ratio |
| `ASR_DEDUP_SENSITIVITY` | `0.85` | Dedup overlap sensitivity |
| `ASR_ENABLE_RETRY` | `1` | Enable beam search retry |
| `ASR_EMPTY_CACHE_INTERVAL` | `10` | GPU cache cleanup каждые N batches |
| `ASR_MAX_NEW_TOKENS` | `500` | Max new tokens |
| `ASR_REPETITION_PENALTY` | `1.1` | Repetition penalty |
| `ASR_NO_REPEAT_NGRAM` | `2` | No-repeat ngram size |
| `ASR_NO_SPEECH_THRESHOLD` | `0.7` | HF pipeline no_speech threshold |
| `ASR_COMPRESSION_RATIO_THRESHOLD` | `2.4` | HF pipeline compression threshold |
| `ASR_LOGPROB_THRESHOLD` | `-0.35` | HF pipeline logprob threshold |
| `ASR_CONDITION_ON_PREV` | `0` | Condition on previous text |
| `ASR_USE_FLASH_ATTENTION` | `0` | FlashAttention-2 |
| `ASR_USE_BETTER_TRANSFORMER` | `0` | BetterTransformer |
| `ASR_TORCH_COMPILE` | `0` | torch.compile |
| `ASR_TORCH_COMPILE_MODE` | `reduce-overhead` | Compile mode |
| `WHISPER_8BIT` | `0` | 8-bit quantization |
| `DEVICE_TYPE` | `cpu` | Device |
| `AMQP_PREFETCH_COUNT` | `16` | AMQP prefetch (ASR may use 64) |

#### Prometheus метрики

| Метрика | Тип | Описание |
|---------|-----|----------|
| `asr_events_total` | Counter | Events asr.ready |
| `asr_segments_total` | Counter | Транскрибированные сегменты |
| `asr_segments_merged_total` | Counter | Merged сегменты |
| `asr_overlap_short_handled_total` | Counter | Short overlap resolved |
| `asr_event_duration_seconds` | Histogram | Full event duration (0.5–600s) |
| `asr_batch_inference_duration_seconds` | Histogram | Batch inference (0.1–10s) |
| `asr_audio_load_duration_seconds` | Histogram | Audio load from MinIO (0.01–2s) |
| `asr_batch_size` | Histogram | Batch sizes (1–64) |
| `asr_fallbacks_total` | Counter | Fallback activations (labels: stage, level) |
| `webhook_requests_total` | Counter | Webhook requests |
| `webhook_request_duration_seconds` | Histogram | Webhook latency |

#### Dockerfile
- Base: `pytorch/pytorch:2.7.1-cuda12.6-cudnn9-devel`
- Prefetches HF model into image
- Multi-platform: cuda для amd64, MPS для arm64
- Optional: `flash-attn`, `optimum`
- Expose: 8082

#### Зависимости
```
torch==2.7.1, torchvision, torchaudio, openai-whisper==20250625, transformers==4.56.1,
accelerate==1.10.1, sentencepiece, safetensors, fastapi, uvicorn, aio-pika, minio,
numpy==1.26.4, soundfile, ffmpeg-python, httpx, prometheus-client
```

---

### 4. speaker_linking

**Назначение:** Связывание спикеров между файлами по голосовым embeddings через Qdrant.

#### Точка входа
- `workers/speaker_linking/main.py`
- CMD: `python -m speaker_linking.main`
- Dockerfile: `workers/speaker_linking/Dockerfile.cpu`

#### AMQP
- **Queue:** `q.speaker_linking`
- **Routing key (consume):** `dia.ready`
- **Routing key (publish):** `link.ready`

#### Модель входного события (`DiaReady`)
```python
class DiaReady(BaseModel):
    type: str = "dia.ready"
    job_id: str
    org_id: int
    node_id: int
    version: int
    diarization_key: str
    prepared_key: str | None
```

#### Алгоритм пошагово

1. **Чтение diarization segments** из MinIO
2. **Загрузка prepared audio** → `(np.ndarray, sr)`
3. **Группировка по спикерам** — by `speaker_label`, normalize to upper case
4. **Merge overlapping intervals** per speaker
5. **Extract embeddings** — для каждого интервала ≥ 2s:
   - `speechbrain/spkrec-ecapa-voxceleb` (192-dim ECAPA-TDNN)
   - `EncoderClassifier.encode_batch(tensor)` → numpy embedding
6. **Qdrant operations:**
   - Collection: `speakers_{org_id}` (192-dim, cosine)
   - `ensure_collection()` — создаёт collection + payload indexes (node_id, org_id)
   - `delete_node_embeddings()` — удаляет старые embeddings этого node (clean re-processing)
   - `link_speakers_to_existing()`:
     - Для каждого спикера: search по всем его embeddings (exclude current node)
     - Majority vote по matched speaker_id
     - Threshold: `LINK_MATCH_THRESHOLD` (default 0.68)
     - Если нет match → `speaker_id(org_id, node_id, version, label)` (blake2b hash)
   - `upsert_embeddings()` — сохраняет embeddings в Qdrant

7. **Обновление сегментов** — добавляет `linked_speaker_id` в каждый сегмент
8. **Сохранение в MinIO:**
   - `speaker_linking/{node_id}/segments.jsonl` — сегменты с linked_speaker_id
   - `link/{node_id}/speakers.json` — маппинг спикеров

9. **Публикация `link.ready`**

#### Выходное событие
```json
{
  "type": "link.ready",
  "event_version": 1,
  "job_id": "uuid",
  "org_id": 1,
  "node_id": 100,
  "version": 1,
  "linked_segments_key": "speaker_linking/100/segments.jsonl",
  "speakers_key": "link/100/speakers.json",
  "finished_at": "ISO-8601"
}
```

#### Формат speakers.json
```json
{
  "org_id": 1,
  "node_id": 100,
  "version": 1,
  "speakers": [
    {
      "speaker_label": "SPEAKER_01",
      "resolved_label": "SPEAKER_01",
      "profile_id": null,
      "linked_speaker_id": "abc123..."
    }
  ]
}
```

#### Артефакты в MinIO

| Путь | Content-Type | Описание |
|------|-------------|----------|
| `speaker_linking/{node_id}/segments.jsonl` | `application/jsonl` | Segments + linked_speaker_id |
| `link/{node_id}/speakers.json` | `application/json` | Speaker mapping for backend |

#### Qdrant

| Параметр | Значение |
|----------|----------|
| Collection | `speakers_{org_id}` (per-org, NOT per-file) |
| Vector size | 192 (ECAPA-TDNN) |
| Distance | COSINE |
| Payload indexes | `node_id` (integer), `org_id` (integer) |

#### Конфигурация

| Переменная | Default | Описание |
|------------|---------|----------|
| `QDRANT_URL` | `http://qdrant:6333` | Qdrant URL |
| `QDRANT_API_KEY` | None | Qdrant API key |
| `LINK_MATCH_THRESHOLD` | `0.68` | Cosine similarity threshold |
| `LINK_MATCH_MAX_RESULTS` | `5` | Max search results |
| `SPEAKER_EMB_MODEL_ID` | `speechbrain/spkrec-ecapa-voxceleb` | Embedding model |
| `SPEAKER_EMB_MODEL_PATH` | None | Local model cache path |

#### Prometheus метрики

| Метрика | Тип |
|---------|-----|
| `link_events_total` | Counter |
| `link_duration_seconds` | Histogram (0.5–300s) |
| `webhook_requests_total` | Counter |
| `webhook_request_duration_seconds` | Histogram |

#### Зависимости
```
torch==2.7.1, pyannote-audio==3.3.2, speechbrain==1.0.2, qdrant-client==1.9.2,
numpy==2.1.3, soundfile, fastapi, uvicorn, aio-pika, minio, httpx, prometheus-client
```

---

### 5. nlp_adapter

**Назначение:** LLM-powered NLP обработка — суммаризация с цитатами, action items, extraction информации о спикерах, person notes.

#### Точка входа
- `workers/nlp_adapter/main.py`
- CMD: `python -m nlp_adapter.main`
- Dockerfile: `workers/nlp_adapter/Dockerfile.cpu`

#### AMQP
- **Queue:** `q.nlp_adapter`
- **Routing key (consume):** `asr.ready`
- **Routing key (publish):** `nlp.ready`

#### Модель входного события (`AsrReady`)
```python
class AsrReady(BaseModel):
    type: str = "asr.ready"
    event_version: int = 1
    job_id: str
    org_id: int
    node_id: int
    version: int
    segments_key: str
    owner_user_id: int | None
    project_scope_id: int | None
```

#### Алгоритм пошагово

1. **Загрузка segments** из MinIO (JSONL)
2. **Построение full transcript** — join всех text
3. **Извлечение участников** — unique speakers из segments
4. **LLM Summary** — `llm_service.generate_summary()`:
   - System prompt: русский markdown с :::cite blocks
   - User prompt: транскрипт с timestamps, контекст, notes, участники
   - Format: Участники → Ключевые моменты (с цитатами) → Принятые решения
5. **Action Items** — `llm_service.extract_action_items()`:
   - Response format: JSON
   - Fields: title, description, assignee, due_date, priority, confidence, source_text
6. **Speaker Info** (if `NLP_PERSON_EXTRACTION_ENABLED`):
   - Для каждого спикера с > 50 chars text
   - `llm_service.extract_speaker_info(segments, label)` → name, company, position, confidence
7. **Person Notes** — для каждого identified спикера:
   - `llm_service.extract_person_notes(segments, name, existing_notes)` → notes with types
   - Types: preference, fact, relationship, history
8. **Сохранение в MinIO:**
   - `nlp/{node_id}/summary.md` — markdown summary
   - `nlp/{node_id}/analysis.json` — полный analysis JSON
9. **Публикация `nlp.ready`** (event_version=2) с inline `nlp` payload для backend

#### LLM Service (`services/llm_service.py`)
- **API:** OpenAI-compatible через LiteLLM proxy
- **Endpoint:** `{LITELLM_BASE_URL}/v1/chat/completions`
- **Model:** `LLM_MODEL` (default `gpt-4o-mini`)
- **Temperature:** 0.3
- **Max tokens:** 4096
- **Timeout:** `LLM_TIMEOUT_SEC` (default 60s)
- **Response format:** `json_object` для structured outputs

#### Выходное событие
```json
{
  "type": "nlp.ready",
  "event_version": 2,
  "job_id": "uuid",
  "org_id": 1,
  "node_id": 100,
  "version": 1,
  "nlp_segments_key": "asr/100/segments.jsonl",
  "nlp_analysis_key": "nlp/100/analysis.json",
  "nlp": {
    "summary_key": "nlp/100/summary.md",
    "summary_content": "## Участники...",
    "llm_model": "gpt-4o-mini",
    "llm_tokens_used": 1234,
    "llm_latency_ms": 5000,
    "action_items": [...],
    "person_candidates": [...],
    "person_notes": [...],
    "context_references": []
  },
  "finished_at": "ISO-8601"
}
```

#### Артефакты в MinIO

| Путь | Content-Type | Описание |
|------|-------------|----------|
| `nlp/{node_id}/summary.md` | `text/markdown` | LLM summary |
| `nlp/{node_id}/analysis.json` | `application/json` | Full analysis |

#### Конфигурация

| Переменная | Default | Описание |
|------------|---------|----------|
| `LITELLM_BASE_URL` | `http://litellm:4000` | LiteLLM proxy URL |
| `LITELLM_API_KEY` | `sk-1234` | API key |
| `LLM_MODEL` | `gpt-4o-mini` | LLM model name |
| `LLM_TIMEOUT_SEC` | `60` | Request timeout |
| `NLP_CONTEXT_ENABLED` | `true` | Cross-call context |
| `NLP_PERSON_EXTRACTION_ENABLED` | `true` | Speaker info extraction |

#### Prometheus метрики

| Метрика | Тип | Описание |
|---------|-----|----------|
| `nlp_enhanced_events_total` | Counter | Events (labels: status=success/empty/error) |
| `nlp_enhanced_processing_seconds` | Histogram | Duration (1–120s) |
| `nlp_llm_tokens_total` | Counter | Total LLM tokens |
| `nlp_llm_latency_seconds` | Histogram | LLM call latency (0.5–30s) |

#### Зависимости
```
fastapi, uvicorn, aio-pika, minio, pydantic, pydantic-settings,
httpx, prometheus-client, orjson, ujson
```

---

### 6. indexer

**Назначение:** Индексация транскриптов в OpenSearch + генерация export файлов (SRT, TXT).

#### Точка входа
- `workers/indexer/main.py`
- CMD: `python -m indexer.main`
- Dockerfile: `workers/indexer/Dockerfile.cpu`

#### AMQP
- **Queue:** `q.indexer`
- **Routing key (consume):** `asr.ready`
- **Routing key (publish):** `indexed.ready`

#### Модель входного события (`AsrReady`)
```python
class AsrReady(BaseModel):
    type: str = "asr.ready"
    job_id: str
    org_id: int
    owner_user_id: int | None
    project_scope_id: int | None
    node_id: int
    version: int
    segments_key: str

    @computed_field
    def effective_org_id(self) -> int | None:
        return self.org_id if self.org_id and self.org_id != 0 else None

    @computed_field
    def effective_owner_user_id(self) -> int | None:
        return self.owner_user_id if self.org_id == 0 else None
```

#### Алгоритм пошагово

1. **Resolve tenant context** — org_id > 0 → org-space; org_id = 0 + owner_user_id → personal-space
2. **Загрузка segments** из MinIO (JSONL)
3. **Index to OpenSearch** — `index_segments()`:
   - Index name: `asr_segments-org{org_id}` или `asr_segments-personal-u{owner_user_id}`
   - `ensure_index()` — создаёт index с mapping если не существует
   - Document fields: org_id, owner_user_id, project_scope_id, node_id, version, speaker_label, speaker_id, start, end, start_ms, end_ms, text, duration, merged, num_parts, overlap_long, source, quality_hint, created_at
   - **Doc ID (idempotency):** `{node_id}:{version}:{start_ms}:{end_ms}`
   - Bulk indexing via `opensearchpy.helpers.bulk`
4. **Build exports:**
   - `build_srt(segments)` → SRT subtitles
   - `build_txt(segments)` → `[SPEAKER_01] text\n`
5. **Сохранение exports в MinIO:**
   - `exports/{node_id}/transcript.srt`
   - `exports/{node_id}/transcript.txt`
   - `exports/{node_id}/index_manifest.json`
6. **Публикация `indexed.ready`** (event_version=2)

#### Выходное событие
```json
{
  "type": "indexed.ready",
  "event_version": 2,
  "job_id": "uuid",
  "org_id": 1,
  "owner_user_id": null,
  "project_scope_id": 456,
  "node_id": 100,
  "version": 1,
  "export_files": {
    "srt": "exports/100/transcript.srt",
    "txt": "exports/100/transcript.txt"
  },
  "manifest_key": "exports/100/index_manifest.json",
  "finished_at": "ISO-8601"
}
```

#### Артефакты в MinIO

| Путь | Content-Type | Описание |
|------|-------------|----------|
| `exports/{node_id}/transcript.srt` | `text/srt` | SRT subtitles |
| `exports/{node_id}/transcript.txt` | `text/txt` | Plain text |
| `exports/{node_id}/index_manifest.json` | `application/json` | Index metadata |

#### OpenSearch

| Параметр | Значение |
|----------|----------|
| Index name (org) | `asr_segments-org{org_id}` |
| Index name (personal) | `asr_segments-personal-u{owner_user_id}` |
| Doc ID | `{node_id}:{version}:{start_ms}:{end_ms}` |
| Shards | 1 |
| Replicas | 1 |

#### Tenant Isolation
- Каждая org → свой индекс → полная физическая изоляция
- Personal space → `asr_segments-personal-u{user_id}`
- `org_id=0` → requires `owner_user_id`
- `index_name()` валидирует XOR (org_id xor owner_user_id)

#### Конфигурация

| Переменная | Default | Описание |
|------------|---------|----------|
| `OPENSEARCH_URL` | `http://opensearch:9200` | OpenSearch URL |
| `OPENSEARCH_USERNAME` | `admin` | Username |
| `OPENSEARCH_PASSWORD` | `admin` | Password |
| `OPENSEARCH_INDEX_PREFIX` | `asr_segments` | Index prefix |
| `OPENSEARCH_TIMEOUT` | `20` | Request timeout |

#### Prometheus метрики

| Метрика | Тип | Описание |
|---------|-----|----------|
| `indexed_events_total` | Counter | Events (labels: status=success/empty/error) |
| `index_docs_total` | Counter | Indexed documents |
| `webhook_requests_total` | Counter | Webhook requests |
| `webhook_request_duration_seconds` | Histogram | Webhook latency |

#### Зависимости
```
fastapi==0.111.0, uvicorn, aio-pika, minio==7.2.9, orjson, opensearch-py==2.7.1,
python-dateutil, httpx, prometheus-client
```

---

### 7. cleanup

**Назначение:** Удаление промежуточных файлов после успешной индексации.

#### Точка входа
- `workers/cleanup/main.py`
- CMD: `python -m uvicorn main:app --host 0.0.0.0 --port 8087`
- Dockerfile: `workers/cleanup/Dockerfile`

#### AMQP
- **Queue:** `q.cleanup`
- **Routing key (consume):** `indexed.ready`
- **Routing key (publish):** — (не публикует)

#### Алгоритм пошагово

1. Валидация payload: `org_id`, `node_id` обязательны
2. **Удаление `prepared/{node_id}/`** (if `CLEANUP_DELETE_PREPARED=true`):
   - `minio.list_objects(bucket, prefix, recursive=True)`
   - `minio.remove_object()` для каждого
3. **Удаление `chunks/{node_id}/`** (if `CLEANUP_DELETE_CHUNKS=true`)
4. **Удаление `diarization/{node_id}/`** (if `CLEANUP_DELETE_DIARIZATION=false` по умолчанию)
5. Логирование количества удалённых файлов

**Сохраняемые файлы:**
- `uploads/` (originals)
- `asr/{node_id}/` (финальные сегменты)
- `exports/{node_id}/` (экспорты)

#### Конфигурация

| Переменная | Default | Описание |
|------------|---------|----------|
| `CLEANUP_DELETE_PREPARED` | `true` | Удалять prepared/ |
| `CLEANUP_DELETE_CHUNKS` | `true` | Удалять chunks/ |
| `CLEANUP_DELETE_DIARIZATION` | `false` | Удалять diarization/ |

#### Prometheus метрики

| Метрика | Тип | Описание |
|---------|-----|----------|
| `cleanup_events_total` | Counter | Processed events |
| `cleanup_duration_seconds` | Histogram | Duration (0.1–10s) |
| `cleanup_files_deleted_total` | Counter | Deleted files (labels: prefix=prepared/chunks/diarization) |

#### Dockerfile
- Base: `python:3.11-slim`
- HEALTHCHECK встроен в Dockerfile (every 30s)
- Expose: 8087

#### Зависимости
```
fastapi==0.104.1, uvicorn, prometheus-client==0.19.0, aio-pika==9.3.1,
minio==7.2.0, pydantic==2.5.2, pydantic-settings==2.1.0
```

---

## packages/logera_common

Общий пакет для всех воркеров. Установлен как editable pip package (`-e`).

### amqp.py

**Responsibilities:** AMQP connection management, publishing, consuming.

**Architecture:**
- **Consumer connection:** `_conn`, `_chan`, `_ex_main` — для consume
- **Publisher connection:** `_pub_conn`, `_pub_chan`, `_pub_ex_main` — изолирован от consumer (разные TCP connections)

**Key functions:**

```python
async def consume(queue_name, handler, routing_keys) -> None
```
- Declares exchanges (`logera.jobs` topic + `logera.dlx` topic)
- Declares queue with DLX arguments: `x-dead-letter-exchange`, `x-dead-letter-routing-key`
- Compatible fallback: если queue уже с другими args → passive declare
- Binds queue to exchange for each routing_key
- Iterator pattern: `async for message in queue.iterator()`
- On handler exception: message rejected (requeue=False) → DLX
- On CancelledError: graceful shutdown

```python
async def safe_publish(routing_key, payload, headers, message_id, correlation_id) -> None
```
- Retries: `AMQP_PUBLISH_RETRIES` (default 5)
- Exponential backoff: `AMQP_PUBLISH_RETRY_DELAY` (default 0.5s) × 2^attempt
- On failure: resets connection/channel caches, reconnects
- Messages: persistent delivery mode, JSON body

**Configuration:**
- `AMQP_PREFETCH_COUNT` (default 16)
- `AMQP_PUBLISH_CONFIRMS` (default 1)
- `AMQP_PUBLISH_RETRIES` (default 5)
- `AMQP_PUBLISH_RETRY_DELAY` (default 0.5)

### config.py

**Pydantic-settings** based configuration. Reads from `.env` file.

```python
class CommonSettings(BaseSettings):
    # AMQP
    amqp_url: str = "amqp://guest:guest@rabbitmq:5672/"
    amqp_exchange_main: str = "logera.jobs"
    amqp_exchange_dlx: str = "logera.dlx"

    # MinIO
    minio_endpoint: str = "minio:9000"
    minio_access_key: str = "minioadmin"
    minio_secret_key: str = "minioadmin"
    minio_secure: bool = False
    bucket_format: str = "org-{org_id}"

    # Qdrant
    qdrant_url: str = "http://qdrant:6333"
    qdrant_api_key: str | None = None

    # OpenSearch
    opensearch_url: str = "http://opensearch:9200"
    opensearch_username: str = "admin"
    opensearch_password: str = "admin"
    opensearch_index_prefix: str = "asr_segments"
    opensearch_timeout: int = 20

    # Webhooks
    webhook_urls: str = ""  # CSV
    webhook_secret: str | None = None

    # Media prep tuning
    media_prep_use_afftdn: bool = True
    media_prep_use_loudnorm: bool = True
    media_prep_ffmpeg_probe_size: int = 100_000_000
    media_prep_ffmpeg_analyze_duration: int = 100_000_000

    transformers_offline: bool = True
```

### minio_io.py

**Functions:**

```python
get_minio_client() -> Minio           # Creates client from settings
resolve_bucket(org_id) -> str          # org_id in (-1,0) → "personal", else "org-{org_id}"
ensure_bucket(client, bucket) -> None  # make_bucket if not exists
put_bytes(client, org_id, object_name, data, content_type, metadata) -> None
get_object(client, org_id, object_name) -> response  # caller must .read() and .close()
```

**Bucket naming:**
- `org_id > 0` → `org-{org_id}` (e.g. `org-1`)
- `org_id ∈ {-1, 0}` → `personal`

### text_embeddings.py

**Назначение:** Semantic search для text chunks (транскрипты + документы) через Qdrant.

**Providers:**
- `litellm` (default): OpenAI-compatible API через LiteLLM proxy, model `text-embedding-3-small` (1536 dim)
- `local`: `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2` (384 dim)

**Collections:** `texts_{org_id}` (отдельно от speaker embeddings `speakers_{org_id}`)

**Payload indexes:** node_id, org_id, chunk_type, content_type, speaker_label, start_ms, end_ms, file_type, page_number, section_type

**Key functions:**
- `embed_texts(texts)` → list of vectors
- `upsert_text_chunks(chunks, org_id, node_id, version)` — batch upsert with blake2b IDs
- `search_similar_texts(query, org_id, filters)` — semantic search
- `search_by_filters_only(org_id, filters)` — metadata-only filter (scroll)
- `get_context_for_rag(query, org_id)` — convenience for RAG

**Content types:** `transcript` (with start_ms, end_ms, speaker_label) and `document` (with file_type, page_number, section_type)

**Configuration:**
- `TEXT_EMBEDDING_PROVIDER` (default `litellm`)
- `LITELLM_BASE_URL`, `LITELLM_API_KEY`
- `TEXT_EMBEDDING_MODEL` (default `text-embedding-3-small`)
- `TEXT_EMBEDDING_DIM` (default 1536)
- `TEXT_EMBEDDING_LOCAL_MODEL`

### webhooks.py

**Functions:**

```python
parse_webhook_urls(raw: str) -> list[str]   # Parses CSV string
async def notify_webhooks(event, default_event_type, urls, secret, ...) -> None
```

**Features:**
- HMAC-SHA256 signature: `X-Logera-Signature: sha256={hex}`
- Headers: `X-Logera-Event`, `Content-Type: application/json`
- Retry: max 5 attempts, jittered exponential backoff (0.5s → 8s)
- Uses `orjson` if available, fallback to `json`
- `on_result` callback for metrics
- Timeout: 5s per request

---

## Pipeline Flow

### Полная цепочка от upload до indexed

```
┌──────────────────────────────────────────────────────────────────────┐
│ 1. Backend: User uploads file                                        │
│    → Saves to MinIO: originals/{node_id}/v1/filename.mp4            │
│    → Creates FsNode + FsVersion in DB                                │
│    → Publishes job.created to exchange "logera.jobs"                  │
│      routing_key: "job.created"                                      │
│      payload: {job_id, org_id, node_id, version, storage_key, mime,  │
│                idempotency_key: "{org_id}:{node_id}:{version}"}      │
└──────────────────────────────┬───────────────────────────────────────┘
                               ▼
┌──────────────────────────────────────────────────────────────────────┐
│ 2. media_prep (q.media_prep ← job.created)                          │
│    → Reads original from MinIO                                       │
│    → ffmpeg → 16kHz mono WAV                                        │
│    → Silero VAD → speech intervals                                   │
│    → Saves: prepared/{node_id}/audio.wav                            │
│    → Saves: prepared/{node_id}/chunks.json                          │
│    → Publishes: media.prepared                                       │
└──────────────────────────────┬───────────────────────────────────────┘
                               ▼
┌──────────────────────────────────────────────────────────────────────┐
│ 3. diarization (q.diarization ← media.prepared)                     │
│    → Loads prepared audio + chunks manifest                          │
│    → pyannote speaker-diarization (GPU)                             │
│    → Global speaker clustering (AgglomerativeClustering, cosine)     │
│    → Saves: diarization/{node_id}/segments.jsonl                    │
│    → Publishes: dia.ready                                            │
└──────────────┬──────────────────────────────┬────────────────────────┘
               ▼                              ▼
┌──────────────────────────────┐  ┌──────────────────────────────────┐
│ 4a. asr (q.asr ← dia.ready) │  │ 4b. speaker_linking              │
│   → Loads dia segments       │  │   (q.speaker_linking ← dia.ready)│
│   → Loads prepared audio     │  │   → Extract speaker embeddings   │
│   → Whisper transcription    │  │   → Qdrant: search existing      │
│     (batched, QC, retry)     │  │   → Link or create speaker IDs   │
│   → Saves: asr/{node_id}/   │  │   → Saves: speaker_linking/...   │
│     segments.jsonl           │  │   → Saves: link/{node_id}/...    │
│   → Publishes: asr.ready    │  │   → Publishes: link.ready        │
└──────────┬──────────┬────────┘  └──────────────────────────────────┘
           ▼          ▼                    (parallel, no dependency)
┌────────────────┐ ┌──────────────────────────────────────────────────┐
│ 5a. nlp_adapter│ │ 5b. indexer (q.indexer ← asr.ready)             │
│ (q.nlp_adapter │ │   → Loads ASR segments from MinIO               │
│  ← asr.ready)  │ │   → Index to OpenSearch (per-tenant index)      │
│   → LLM summary│ │     doc_id: {node_id}:{version}:{start_ms}:... │
│   → Action items│ │   → Build exports: SRT, TXT                    │
│   → Speaker info│ │   → Saves: exports/{node_id}/*                 │
│   → Person notes│ │   → Publishes: indexed.ready                   │
│   → Saves: nlp/ │ └──────────────────────────┬─────────────────────┘
│   → Publishes:  │                             ▼
│     nlp.ready   │ ┌──────────────────────────────────────────────────┐
└─────────────────┘ │ 6. cleanup (q.cleanup ← indexed.ready)          │
                    │   → Deletes: prepared/{node_id}/ (default ON)   │
                    │   → Deletes: chunks/{node_id}/ (default ON)     │
                    │   → Keeps: uploads/, asr/, exports/             │
                    └──────────────────────────────────────────────────┘
```

### AMQP Events Summary

| Event | Routing Key | Publisher | Consumers |
|-------|------------|-----------|-----------|
| `job.created` | `job.created` | Backend/Orchestrator | media_prep |
| `media.prepared` | `media.prepared` | media_prep | diarization |
| `dia.ready` | `dia.ready` | diarization | asr, speaker_linking |
| `asr.ready` | `asr.ready` | asr | nlp_adapter, indexer |
| `nlp.ready` | `nlp.ready` | nlp_adapter | Backend consumer |
| `link.ready` | `link.ready` | speaker_linking | Backend consumer |
| `indexed.ready` | `indexed.ready` | indexer | cleanup, Backend consumer |

### MinIO Артефакты — полный перечень

| Путь | Создаёт | Удаляет cleanup | Описание |
|------|---------|-----------------|----------|
| `originals/{node_id}/v{ver}/{filename}` | Backend | ❌ | Исходный файл |
| `prepared/{node_id}/audio.wav` | media_prep | ✅ | 16kHz mono WAV |
| `prepared/{node_id}/chunks.json` | media_prep | ✅ | VAD manifest |
| `diarization/{node_id}/segments.jsonl` | diarization | ❌ (default) | Speaker segments |
| `asr/{node_id}/segments.jsonl` | asr | ❌ | Transcribed segments |
| `speaker_linking/{node_id}/segments.jsonl` | speaker_linking | ❌ | Segments + linked IDs |
| `link/{node_id}/speakers.json` | speaker_linking | ❌ | Speaker mapping |
| `nlp/{node_id}/summary.md` | nlp_adapter | ❌ | LLM summary |
| `nlp/{node_id}/analysis.json` | nlp_adapter | ❌ | Full NLP analysis |
| `exports/{node_id}/transcript.srt` | indexer | ❌ | SRT subtitles |
| `exports/{node_id}/transcript.txt` | indexer | ❌ | Plain text |
| `exports/{node_id}/index_manifest.json` | indexer | ❌ | Index metadata |

### Tenant Isolation Model

- **Org-space:** `org_id > 0` → bucket `org-{org_id}`, index `asr_segments-org{org_id}`, Qdrant `speakers_{org_id}`
- **Personal-space:** `org_id = 0` + `owner_user_id` → bucket `personal`, index `asr_segments-personal-u{user_id}`
- **Bucket resolution:** `resolve_bucket(org_id)` → `org_id ∈ {-1,0}` = `"personal"`, else `"org-{org_id}"`
- **Index naming:** XOR validation — exactly one of `org_id > 0` or `owner_user_id`

### Idempotency

- **AMQP message_id:** `{org_id}:{node_id}:{version}` — для дедупликации
- **OpenSearch doc_id:** `{node_id}:{version}:{start_ms}:{end_ms}` — upsert вместо insert
- **Qdrant:** `delete_node_embeddings()` перед upsert — clean re-processing
- **DLX:** failed messages → `{queue_name}.dlq` для manual retry

---

## Тесты

Директория: `tests/integration/`

### Инфраструктура
- Docker Compose: `docker-compose.test.yml`
- Изолированные сервисы: `db-test`, `redis-test`, `minio-test`, `rabbitmq-test`, `opensearch-test`, `qdrant-test`
- conftest.py: автоматические миграции при старте, fixtures для всех сервисов

### Категории тестов

#### 1. E2E Pipeline (`test_pipeline_e2e.py`)

**Тестирует полный flow с реальными воркерами.**

| Тест | Описание | Timeout |
|------|----------|---------|
| `test_org_full_pipeline` | upload → job.created → ... → indexed.ready (org-space) | 600s |
| `test_personal_full_pipeline` | upload → indexed.ready (personal-space, org_id=0) | 600s |
| `test_pipeline_with_project_scope` | project_scope_id propagation через pipeline | 600s |
| `test_job_created_roundtrip` | Publish + consume job.created event | 5s |
| `test_indexed_ready_roundtrip` | Publish + consume indexed.ready event | 5s |

**Механика:**
- Загружает реальный тестовый видеофайл (`fixtures/test_video.mp4`)
- Публикует `job.created` в exchange
- Ждёт `indexed.ready` через temporary queue с filter_fn
- Проверяет tenant fields, OpenSearch segments

#### 2. Idempotency (`test_idempotency.py`)

| Тест | Описание |
|------|----------|
| `test_double_index_same_segments_no_duplicates` | Повторная индексация → тот же count |
| `test_update_segments_replaces_old` | Upsert с новым text → обновляет |
| `test_different_version_creates_separate` | Разные version → разные doc_id |
| `test_personal_double_index_no_duplicates` | Personal space: no duplication |
| `test_doc_id_format` | Формат `{node_id}:{version}:{start_ms}:{end_ms}` |
| `test_same_doc_id_updates_not_creates` | Тот же doc_id → update |
| `test_reindex_node1_does_not_affect_node2` | Cross-node independence |

#### 3. Tenant Isolation (`test_tenant_isolation.py`)

**Критические security тесты.**

| Тест | Описание |
|------|----------|
| `test_org1_cannot_search_org2_segments` | org1 search → only org1 results |
| `test_org_indexes_are_separate` | Разные индексы для разных org |
| `test_cross_org_node_id_no_collision` | Same node_id, different org → no clash |
| `test_user_a_cannot_search_user_b_segments` | Personal isolation |
| `test_personal_indexes_are_separate` | Separate personal indexes |
| `test_cross_user_text_search_isolated` | Text search isolated |
| `test_org_id_zero_requires_owner_user_id` | org_id=0 w/o owner → ValueError |
| `test_search_with_zero_org_requires_owner` | Validation |
| `test_index_name_validation` | XOR(org_id, owner_user_id) |
| `test_org_and_personal_fully_isolated` | Mixed tenant isolation |
| `test_same_text_different_tenants` | Same text, different tenants → isolated |

#### 4. Project Scope (`test_project_scope.py`)

| Тест | Описание |
|------|----------|
| `test_file_inherits_folder_scope` | CTE recursive query inheritance |
| `test_file_scope_overrides_folder` | File scope > folder scope |
| `test_nested_folders_inheritance` | Deep hierarchy (3 levels) |
| `test_scope_xor_validation` | XOR(org_id, owner_user_id) |
| `test_org_scope_only_for_org_nodes` | Cross-org scope prevention |
| `test_segments_indexed_with_scope` | OpenSearch docs have scope |
| `test_filter_by_project_scope` | Filter by scope in OpenSearch |
| `test_segments_without_scope` | null scope handling |

#### 5. Org Pipeline (`test_pipeline_org.py`)

| Тест | Описание |
|------|----------|
| `test_asr_ready_indexes_segments` | asr.ready → OpenSearch indexing |
| `test_search_returns_only_org_segments` | Org isolation in search |
| `test_minio_bucket_isolation` | Files in correct buckets |
| `test_segments_indexed_with_project_scope` | Scope in indexed docs |
| `test_filter_by_project_scope` | Scope filtering |

#### 6. Personal Pipeline (`test_pipeline_personal.py`)

| Тест | Описание |
|------|----------|
| `test_personal_segments_indexed` | Personal index creation + indexing |
| `test_personal_minio_bucket` | `personal-u{user_id}` bucket |
| `test_org_cannot_see_personal_segments` | Cross-space isolation |
| `test_different_index_names` | org vs personal index names |
| `test_minio_bucket_separation` | Physical bucket separation |

### Test Helpers (`helpers.py`)

- `generate_test_wav(duration_sec)` — синтетический WAV (тишина)
- `generate_test_segments(num)` — синтетические сегменты
- `upload_test_file()`, `upload_test_segments()` — MinIO helpers
- `publish_event()`, `wait_for_event()`, `wait_for_event_with_filter()` — AMQP helpers
- `create_test_index()`, `index_test_segments()`, `search_segments()` — OpenSearch helpers
- `create_test_fs_node()`, `create_test_project_scope()` — DB helpers
- `assert_tenant_isolated()`, `assert_segments_match()` — Assertions

### Запуск

```bash
# Быстрые тесты (без воркеров) — ~15 сек
docker-compose -f docker-compose.test.yml run --rm test-runner \
  tests/integration/ --ignore=tests/integration/test_pipeline_e2e.py -v

# Полные E2E (с воркерами) — 5-10 мин
docker-compose -f docker-compose.test.yml run --rm test-runner \
  tests/integration/ -v

# С GPU
DEVICE_TYPE=cuda docker-compose -f docker-compose.test.yml run --rm test-runner
```

---

## Common Utilities

### `workers/common/device_utils.py`

Единый модуль выбора device для PyTorch:
- `get_device()` — по ENV `DEVICE_TYPE` (cuda/mps/cpu), с fallback
- `get_torch_dtype(device)` — cuda→fp16, rest→fp32
- `supports_8bit_quantization(device)` — only cuda
- `supports_flash_attention(device)` — only cuda

### `workers/common/timeline.py`

Unified Timeline Format (v2) — альтернатива отдельным diarization + asr JSONL:
- `TimelineBuilder` — строит timeline с speaker stats
- `timeline_to_srt()`, `timeline_to_txt()`, `timeline_to_vtt()` — экспорты
- **Пока не используется в production** — код содержит `example_usage_in_asr_handler()`
