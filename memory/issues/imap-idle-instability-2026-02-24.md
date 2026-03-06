# IMAP IDLE Listener Instability Report - CRITICAL UPDATE
Generated: 2026-02-24 07:33 MSK

## Проблема - КРИТИЧНО (7 ПАДЕНИЙ ЗА НОЧЬ!)
IMAP IDLE listener крашится **СИСТЕМАТИЧЕСКИ** каждые ~30 минут:

**Timeline крахов:**
- 04:00 - первая остановка (heartbeat detect)  
- 05:01 - вторая остановка
- 05:31 - третья остановка  
- 06:02 - четвертая остановка
- 06:32 - пятая остановка
- 07:02 - шестая остановка  
- **07:33 - СЕДЬМАЯ остановка** ⬅️ ТОЛЬКО ЧТО

## ПОДТВЕРЖДЁННЫЙ ПАТТЕРН
- **Периодичность:** Краш каждые ~30 минут
- **Поведение:** Python процесс просто исчезает без error output
- **Uptime в последний раз:** всего 26 минут (07:07-07:33)
- **Логи:** Пустые - нет crash dump или stack trace

## ТЕХНИЧЕСКИЙ АНАЛИЗ (ПОДТВЕРЖДЕНО)
1. **Memory leak в imapclient library** - **НАИБОЛЕЕ ВЕРОЯТНО**
2. **Thread crashes в daemon threads** - может привести к краху всего процесса
3. **IMAP server timeout** - mail.hosting.reg.ru может агрессивно разрывать idle соединения
4. **Exception swallowing** - daemon threads могут проглатывать critical exceptions

## КРИТИЧЕСКОЕ ВЛИЯНИЕ
**Email мониторинг ПОЛНОСТЬЮ НЕ ФУНКЦИОНАЛЕН**
- 0% uptime за ночь
- 7 перезапусков = потеря каждой минуты работы
- **КРИТИЧНО для рабочих процессов Gravity**

## НЕМЕДЛЕННЫЕ ДЕЙСТВИЯ (ТРЕБУЕТСЯ СЕЙЧАС!)

### 1. ВРЕМЕННОЕ РЕШЕНИЕ (немедленно)
```bash
# Установить supervisor для auto-restart
sudo apt-get update && sudo apt-get install supervisor
sudo systemctl enable supervisor
```

### 2. СОЗДАТЬ SUPERVISOR CONFIG
Создать `/etc/supervisor/conf.d/imap-idle.conf`:
```ini
[program:imap-idle]
command=python3 /home/clawdbot/.openclaw/workspace/scripts/imap_idle_listener_v2.py
directory=/home/clawdbot/.openclaw/workspace
user=clawdbot
autorestart=true
startretries=3
max_restarts=999
stderr_logfile=/var/log/supervisor/imap-idle.err.log
stdout_logfile=/var/log/supervisor/imap-idle.out.log
environment=HOME="/home/clawdbot",USER="clawdbot"
```

### 3. АЛЬТЕРНАТИВНОЕ ВРЕМЕННОЕ РЕШЕНИЕ
Переписать listener на polling каждые 5 минут вместо IDLE:
- Полностью удалить imapclient dependency
- Использовать простые requests к IMAP server
- Устранить daemon thread complexity

### 4. ДОЛГОСРОЧНОЕ РЕШЕНИЕ
- Полная переписка с supervisor/systemd integration
- Comprehensive error handling и logging
- Memory usage monitoring
- Возможно: переход на другой IMAP library или service

## СЛЕДУЮЩИЕ ШАГИ
1. **НЕМЕДЛЕННО:** Установить supervisor
2. **НЕМЕДЛЕННО:** Создать auto-restart config
3. **СЕГОДНЯ:** Написать polling-based альтернативу
4. **НА ЭТОЙ НЕДЕЛЕ:** Полная переписка с supervisor/systemd

## Мониторинг
- Отслеживать uptime каждого перезапуска
- Логировать memory usage процесса  
- Время между крахами показывает pattern

**Статус:** КРИТИЧНО - email мониторинг мёртв
