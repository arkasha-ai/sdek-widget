# Архитектура системы синхронного речевого перевода в реальном времени (WebRTC)

> Исследование — 22 февраля 2026

## Содержание
1. [Рекомендуемый стек технологий](#1-рекомендуемый-стек-технологий)
2. [Архитектурная схема](#2-архитектурная-схема)
3. [Latency бюджет](#3-latency-бюджет)
4. [Chunking стратегия](#4-chunking-стратегия)
5. [WebRTC SFU — выбор и схема](#5-webrtc-sfu--выбор-и-схема)
6. [End-to-end модели перевода](#6-end-to-end-модели-перевода)
7. [Маршрутизация потоков по языкам](#7-маршрутизация-потоков-по-языкам)
8. [Риски и открытые вопросы](#8-риски-и-открытые-вопросы)

---

## 1. Рекомендуемый стек технологий

| Компонент | Рекомендация | Обоснование |
|-----------|-------------|-------------|
| **WebRTC SFU** | **LiveKit** (self-hosted) | Open source, Go, первоклассный Python SDK (livekit-agents), встроенная поддержка audio processing pipeline, on-prem ready |
| **VAD** | **Silero VAD** | Лучшее качество среди лёгких VAD, ~30ms latency на chunk, Python-native, настраиваемый порог |
| **Модель перевода** | **Ваша end-to-end модель** (primary) + **SeamlessStreaming** (fallback/comparison) | Своя модель уже есть; SeamlessStreaming — единственная модель с нативным streaming и ~2s latency |
| **Codec** | **Opus** (via opuslib/PyOgg) | Стандарт WebRTC, 20ms фреймы, отличное качество при низком битрейте |
| **Оркестрация** | **Python asyncio** + LiveKit Agents SDK | Весь pipeline на Python, async обработка нескольких потоков |
| **Буферизация** | **Redis Streams** или in-memory asyncio.Queue | Для межпроцессной коммуникации между pipeline'ами |

---

## 2. Архитектурная схема

```
┌─────────────────────────────────────────────────────────────────┐
│                        КЛИЕНТЫ (WebRTC)                        │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐      до 10 чел.     │
│  │ User A   │  │ User B   │  │ User C   │      ...            │
│  │ lang=EN  │  │ lang=RU  │  │ lang=HI  │                     │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘                     │
│       │publish       │publish      │publish                     │
└───────┼──────────────┼─────────────┼───────────────────────────┘
        │              │             │
        ▼              ▼             ▼
┌─────────────────────────────────────────────────────────────────┐
│                    LiveKit SFU Server                           │
│                    (on-premise, Go)                              │
│                                                                 │
│  Принимает audio tracks от участников                           │
│  Маршрутизирует обработанные tracks обратно                     │
└───────┬──────────────┬─────────────┬───────────────────────────┘
        │ subscribe     │             │
        ▼              ▼             ▼
┌─────────────────────────────────────────────────────────────────┐
│              Translation Agent (Python, LiveKit Agents)          │
│                                                                 │
│  ┌──────────────────────────────────────────────────────┐       │
│  │  Per-participant input pipeline:                      │       │
│  │                                                       │       │
│  │  Audio In → Opus Decode → Silero VAD → Chunk Buffer  │       │
│  │                              │                        │       │
│  │                    speech detected                     │       │
│  │                              │                        │       │
│  │                              ▼                        │       │
│  │                   ┌─────────────────────┐             │       │
│  │                   │  Chunk ready (1-4s)  │             │       │
│  │                   └──────────┬──────────┘             │       │
│  └──────────────────────────────┼────────────────────────┘       │
│                                 │                                │
│  ┌──────────────────────────────┼────────────────────────┐       │
│  │  Per-target-language pipeline (fanout):                │       │
│  │                                                        │       │
│  │  For each target language ≠ speaker's language:        │       │
│  │                                                        │       │
│  │  Audio Chunk ──→ E2E Translation Model ──→ TTS Audio  │       │
│  │                   (your model, RTF~1.3)                │       │
│  │                              │                         │       │
│  │                              ▼                         │       │
│  │                   Opus Encode → Audio Track            │       │
│  │                              │                         │       │
│  │            publish to LiveKit (per-language track)      │       │
│  └──────────────────────────────┼─────────────────────────┘       │
│                                 │                                │
└─────────────────────────────────┼────────────────────────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────┐
│                   LiveKit: Track Routing                         │
│                                                                 │
│  track "tts-ru" → subscribe: все участники с lang=RU            │
│  track "tts-en" → subscribe: все участники с lang=EN            │
│  track "tts-hi" → subscribe: все участники с lang=HI            │
│                                                                 │
│  Participant НЕ получает свой перевод (не подписан на свой язык) │
│  Participant НЕ получает оригинальный audio других               │
└─────────────────────────────────────────────────────────────────┘
```

### Упрощённый data flow для одного высказывания

```
User A (EN) говорит фразу "Hello everyone"
    │
    ├─→ VAD детектирует речь, буферизация ~2s
    │
    ├─→ Pipeline RU: E2E model(EN→RU) → "Привет всем" (TTS audio)
    │       └─→ publish track "tts-ru-from-A" → User B получает
    │
    └─→ Pipeline HI: E2E model(EN→HI) → "सबको नमस्ते" (TTS audio)
            └─→ publish track "tts-hi-from-A" → User C получает
```

---

## 3. Latency бюджет

### С вашей E2E моделью (RTF 1.3, batch processing)

| Компонент | Latency | Комментарий |
|-----------|---------|-------------|
| WebRTC capture + network | 50–100ms | Opus encoding + network jitter |
| VAD + буферизация чанка | 1500–3000ms | Ожидание паузы в речи (~2s средний чанк) |
| E2E Translation (RTF 1.3) | 1950–3900ms | RTF 1.3 × длина чанка (1.5–3s audio) |
| Opus encode + network back | 50–100ms | |
| **ИТОГО** | **3.5–7.1s** | От конца фразы до начала воспроизведения |

> **RTF 1.3 означает:** обработка 1 секунды аудио занимает 1.3 секунды. Для 3-секундного чанка — 3.9 секунд inference. Это **медленнее реального времени** — главный bottleneck.

### С SeamlessStreaming (streaming mode)

| Компонент | Latency | Комментарий |
|-----------|---------|-------------|
| WebRTC capture + network | 50–100ms | |
| SeamlessStreaming (incremental) | ~2000ms | EMMA mechanism, не ждёт конца фразы |
| TTS synthesis (если cascaded) | 200–500ms | Встроенный vocoder |
| Opus encode + network back | 50–100ms | |
| **ИТОГО** | **~2.3–2.7s** | Нативный streaming — значительно лучше |

### Perceived latency — как минимизировать

- **Начинать воспроизведение до окончания генерации TTS** — streaming TTS с побайтовой отдачей
- **Overlap чанков** — начинать перевод следующего чанка пока играет предыдущий
- **Predictive chunking** — не ждать длинной паузы, резать при коротких паузах (300–500ms)
- **Pre-buffering** — для jitter: 100–200ms playback buffer на клиенте

---

## 4. Chunking стратегия

### Рекомендуемый подход: Adaptive VAD-based chunking

```python
# Параметры Silero VAD
SILERO_CONFIG = {
    "threshold": 0.5,           # порог детекции речи (0.3–0.7)
    "min_speech_duration_ms": 250,   # мин. длина речевого сегмента
    "min_silence_duration_ms": 500,  # пауза для разделения (ключевой параметр!)
    "speech_pad_duration_ms": 100,   # padding вокруг речи
    "max_speech_duration_s": 5.0,    # принудительный split при длинной речи
    "window_size_samples": 512,      # 32ms при 16kHz
}
```

### Стратегии (от простого к сложному)

| Стратегия | Описание | Плюсы | Минусы |
|-----------|----------|-------|--------|
| **Pause-based (рекомендуемая)** | Silero VAD, split при паузе 500ms | Естественные границы фраз | Длинные фразы без пауз = большой чанк |
| **Fixed-size + VAD** | Max 4s, но только на границе VAD | Предсказуемый latency | Может обрезать середину мысли |
| **Hybrid** | Pause 500ms ИЛИ max 4s (выбираем ближайшую границу слова) | Баланс | Сложнее реализовать |
| **Semantic (LLM-based)** | ASR → punctuation model → split | Лучшее качество перевода | +300–500ms latency от ASR |

### Рекомендация

**Hybrid подход:**
1. Silero VAD детектирует речь / тишину
2. При паузе ≥500ms — отправить накопленный буфер на перевод
3. При непрерывной речи ≥4s — принудительный split (но с overlap 300ms для контекста)
4. Overlap контекст: при отправке чанка N, prepend последние 500ms чанка N-1 (не для перевода, а для контекста модели)

### Silero VAD vs WebRTC VAD

| | Silero VAD | WebRTC VAD (via py-webrtcvad) |
|---|-----------|------------------------------|
| Качество | ★★★★★ | ★★★ |
| Latency | ~30ms per frame | ~10ms per frame |
| Шум | Устойчив | Чувствителен к фоновому шуму |
| Язык | Python (PyTorch) | C + Python bindings |
| Модель | Neural net (ONNX ~2MB) | Rule-based GMM |
| **Вердикт** | **Для продакшена** | Для простых случаев |

---

## 5. WebRTC SFU — выбор и схема подключения

### Сравнение SFU

| Критерий | LiveKit | mediasoup | Janus |
|----------|---------|-----------|-------|
| Язык | Go | C++ (Node.js API) | C |
| Python SDK | ✅ livekit-agents (первоклассный) | ❌ (нужен Node.js signaling) | ❌ (REST API) |
| On-premise | ✅ Docker / binary | ✅ npm install | ✅ Docker |
| Audio processing integration | ✅ Agents SDK — подписка на audio track, publish audio track напрямую из Python | ⚠️ Через внешний RTP/DataChannel — нужен GStreamer или FFmpeg | ⚠️ Через audioBridge plugin — ограничено |
| Масштабируемость | ✅ Distributed (multi-node) | ⚠️ Single process | ⚠️ Single process |
| Сообщество / поддержка | ✅ Активное, хорошая документация | ✅ Зрелое | ✅ Зрелое |
| Сложность интеграции | Низкая | Средняя | Высокая |
| License | Apache 2.0 | ISC | GPL-3.0 |

### Рекомендация: **LiveKit**

**Почему:**
1. **Python-native Agents SDK** — ключевое преимущество. Можно подписаться на audio track участника, обработать в Python, и publish обратно как новый track — всё через SDK, без GStreamer/FFmpeg hacks
2. **Rooms + Tracks model** — каждый agent может publish multiple audio tracks (по одному на язык)
3. **Data channels** — для метаданных (выбор языка, статус)
4. **On-prem** — один бинарник или Docker, TURN/STUN встроены

### Схема подключения LiveKit

```python
# Simplified LiveKit Agent for translation
from livekit import agents, rtc
import asyncio

class TranslationAgent:
    def __init__(self, room: rtc.Room):
        self.room = room
        self.vad = SileroVAD()
        self.pipelines = {}  # per-speaker pipelines
    
    async def on_track_subscribed(self, track: rtc.AudioTrack, 
                                   participant: rtc.RemoteParticipant):
        """Called when we receive audio from a participant"""
        speaker_lang = participant.metadata  # e.g. "EN"
        
        audio_stream = rtc.AudioStream(track)
        async for frame in audio_stream:
            # Frame: PCM 16-bit, 48kHz (LiveKit default)
            chunk = self.vad.process(frame, speaker_id=participant.sid)
            if chunk is not None:
                # VAD detected complete utterance
                await self.translate_and_publish(
                    chunk, speaker_lang, participant.sid
                )
    
    async def translate_and_publish(self, audio_chunk, source_lang, speaker_id):
        """Translate to all target languages and publish"""
        target_langs = {"EN", "RU", "HI"} - {source_lang}
        
        for target_lang in target_langs:
            # Run translation (your E2E model)
            translated_audio = await self.e2e_model.translate(
                audio_chunk, source_lang, target_lang
            )
            
            # Publish as a named track
            track_name = f"tts-{target_lang.lower()}-{speaker_id}"
            source = rtc.AudioSource(sample_rate=24000, num_channels=1)
            track = rtc.LocalAudioTrack.create_audio_track(track_name, source)
            
            await self.room.local_participant.publish_track(track)
            await source.capture_frame(translated_audio)
```

### Opus encode/decode в Python

```python
# Варианты:
# 1. opuslib (pip install opuslib) — биндинги к libopus
# 2. PyOgg (pip install pyogg)  
# 3. LiveKit SDK обрабатывает Opus автоматически (frames приходят уже decoded)

# LiveKit Agents SDK: audio frames приходят как PCM — 
# Opus decode/encode происходит внутри SDK, вам не нужно делать это вручную!
```

---

## 6. End-to-end модели перевода

### Обзор моделей

| Модель | Тип | RTF (GPU) | Streaming | EN | RU | HI | Open Source |
|--------|-----|-----------|-----------|----|----|----|----|
| **SeamlessM4T v2 Large** | E2E multimodal | ~0.5–0.8 (A100) | ❌ batch only | ✅ | ✅ | ✅ | ✅ |
| **SeamlessStreaming** | E2E streaming | N/A (incremental, ~2s delay) | ✅ нативный | ✅ | ✅ | ✅ | ✅ |
| **Whisper + NLLB + TTS** | Cascade | ~1.5–3.0 (суммарно) | ⚠️ per-component | ✅ | ✅ | ✅ | ✅ |
| **Translatotron 2** | E2E | ~1.0 | ❌ | ✅ | ❌ | ❌ | ❌ (Google internal) |
| **AudioPaLM** | LLM-based | >>1.0 | ❌ | ✅ | ? | ? | ❌ (Google internal) |
| **Ваша модель** | E2E | 1.3 | ❌ batch | ✅ | ✅ | ✅ | N/A |

### SeamlessStreaming — детальнее

- Использует **EMMA (Efficient Monotonic Multihead Attention)** — генерирует перевод инкрементально, по мере поступления входного аудио
- Не ждёт конца фразы — **ключевое отличие** от всех batch-моделей
- Latency ~2 секунды (policy-based, настраивается)
- Поддерживает ~100 языков, включая EN, RU, HI
- Качество немного ниже офлайн-модели SeamlessM4T v2 (~1-2 BLEU)
- **Проблема**: S2ST (speech-to-speech) streaming пока экспериментальный; S2TT (speech-to-text) streaming стабилен → можно использовать SeamlessStreaming(S2TT) + streaming TTS

### RTF 1.3 — что это значит для вашей системы

- **RTF (Real-Time Factor)** = время обработки / длительность аудио
- RTF 1.3 → 1 секунда аудио обрабатывается 1.3 секунды
- **Это медленнее реального времени** — система не успевает обрабатывать поток "вживую"
- Решение: **chunking + параллелизм**
  - При чанке 2s: ожидание 2.6s inference + 2s буферизации = 4.6s задержка
  - Параллельная обработка нескольких чанков (pipeline parallelism)
  - GPU batching: если модель поддерживает batch inference, можно обрабатывать несколько пар языков одновременно

### Рекомендация по моделям

**Стратегия "два режима":**
1. **Primary**: Ваша E2E модель с chunking (4–7s latency) — лучшее качество
2. **Low-latency fallback**: SeamlessStreaming S2TT → fast TTS (2–3s latency) — для случаев когда latency критичен
3. **Будущее**: Когда SeamlessStreaming S2ST стабилизируется — переход на него как primary

---

## 7. Маршрутизация потоков по языкам

### Паттерн: N speakers × M languages

Для 10 участников и 3 языков:
- **Входящие потоки**: 10 (по одному от каждого участника)
- **Translation pipelines**: до 10 × 2 = 20 (каждый участник → 2 других языка)
- **Исходящие tracks**: 10 × 2 = 20 audio tracks (но участник подписан только на tracks для своего языка от других)

### Оптимизация: shared translation per language pair

```
Вместо:
  Speaker A (EN) → translate to RU → User B
  Speaker A (EN) → translate to RU → User D  (оба RU)

Делаем:
  Speaker A (EN) → translate to RU → один track "tts-ru-from-A"
                                      ├→ User B subscribes
                                      └→ User D subscribes
```

Это уже встроено в SFU модель — один published track, множество subscribers. **Перевод делается один раз на пару (speaker, target_lang).**

### Фактическое количество переводов

```
Speakers per language: EN=3, RU=4, HI=3
Translation jobs per utterance:
  EN speaker says something → translate to RU (1 job) + HI (1 job) = 2 jobs
  RU speaker → EN + HI = 2 jobs
  HI speaker → EN + RU = 2 jobs

Max concurrent: если все говорят одновременно (маловероятно в конференции):
  10 speakers × 2 target langs = 20 jobs
  
Realistic: 1-2 active speakers = 2-4 concurrent translation jobs
```

### GPU resource planning

С RTF 1.3 и 2-секундными чанками:
- 1 translation job = 2.6s GPU time
- 4 concurrent jobs на 1 GPU = нужен batch inference или 4 GPU
- **Рекомендация**: 2× A100/A10 GPU для comfortable headroom при 10 участниках

### Буферизация

```
Client-side:
  - Jitter buffer: 100–200ms (WebRTC default, adaptive)
  - Playback buffer: начать воспроизведение после получения первых 200ms

Server-side:
  - Audio input buffer: ring buffer per speaker, 10s max
  - Translation output queue: asyncio.Queue per (speaker, target_lang)
  - Overlap handling: если новый перевод готов, а предыдущий ещё играет →
    плавный crossfade или queue
```

---

## 8. Риски и открытые вопросы

### Критические риски

| Риск | Severity | Митигация |
|------|----------|-----------|
| **RTF > 1.0 — не real-time** | 🔴 Высокий | Chunking + parallel GPU inference + рассмотреть SeamlessStreaming |
| **Накопление задержки** | 🔴 Высокий | При непрерывной речи задержка растёт. Нужен механизм "skip" — если pipeline перегружен, пропускать чанки |
| **Качество перевода коротких чанков** | 🟡 Средний | Чанк 1–2s может не содержать полную мысль. Передавать контекст предыдущих чанков |
| **GPU capacity при 10 участниках** | 🟡 Средний | Нужно 2+ GPU; batching модели критичен |
| **Overlap речи (crosstalk)** | 🟡 Средний | Когда говорят двое одновременно — обе pipeline работают, latency растёт |

### Открытые вопросы

1. **Ваша E2E модель — поддерживает ли batch inference?** Если да — можно обрабатывать несколько переводов на одном GPU параллельно, это критично
2. **Можно ли дотюнить модель для streaming?** Перевод с partial context (неполная фраза) — нужен fine-tuning или промптинг
3. **SeamlessStreaming S2ST** — стоит ли инвестировать в интеграцию? Может заменить всю модель, но качество для RU/HI нужно тестировать
4. **Голос TTS** — ваша E2E модель уже генерирует speech? Или нужен отдельный TTS?
5. **Масштабирование GPU** — модель помещается на одну карту? Нужен ли model parallelism?
6. **Fallback при сбое GPU** — очередь или пропуск чанков?

### Дорожная карта реализации (предложение)

```
Phase 1 (2-3 недели): MVP
  - LiveKit server on-prem
  - Простой web-клиент (React + LiveKit SDK)
  - 1 agent: VAD → ваша модель → publish track
  - 2 участника, 2 языка
  - Оценка реальной latency

Phase 2 (2-3 недели): Multi-language routing
  - 3 языка, до 5 участников
  - Language selection UI
  - Track subscription по языку
  - Monitoring latency per component

Phase 3 (2-3 недели): Optimization
  - SeamlessStreaming как альтернативный backend
  - GPU batching
  - Adaptive chunking (hybrid strategy)
  - Fallback / skip при перегрузке
  - до 10 участников
```

---

## Приложение: Полезные ресурсы

- **LiveKit Agents SDK**: https://docs.livekit.io/agents/ — Python SDK для audio processing
- **SeamlessStreaming**: https://github.com/facebookresearch/seamless_communication — Meta's streaming model
- **Silero VAD**: https://github.com/snakers4/silero-vad — лучший open-source VAD
- **LiveKit self-hosted**: https://docs.livekit.io/home/self-hosting/local/ — деплой на своём сервере
- **SeamlessM4T v2**: https://huggingface.co/facebook/seamless-m4t-v2-large — offline модель для сравнения
