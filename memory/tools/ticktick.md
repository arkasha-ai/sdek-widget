# TickTick 🎯

**API:** Open API v1
**Token:** `~/.openclaw/workspace/.ticktick_token.json`
**Credentials:** `secrets.env` (TICKTICK_CLIENT_ID, TICKTICK_CLIENT_SECRET)

## Команды

```bash
ticktick projects                          # Список проектов
ticktick tasks <project_id>               # Задачи проекта
ticktick add "Задача" --project <id> --due 2026-02-20 --priority 3 --content "Описание"
ticktick complete <project_id> <task_id>  # Завершить (delete не работает!)
```

**Приоритеты:** 0=нет / 1=низкий / 3=средний / 5=высокий

## ID Проектов

| Проект | ID |
|--------|----|
| 🤖 Аркаша Tasks | `6998c6fb1ff4510b9e851f9f` | **← Heartbeat automation**
| 🏠 Личный | `695bc6dd7d799105bb21e874` |
| 💼 Работа | `695bc7447dd51105bb21e8ee` |
| 🏃 Фитнес | `695bfa4ba268d125f73668e9` |
| Ясень Финанс | `695bfa4ba268d125f73668e9` |
| Front-end | `695bfb43ab63d125f7366aa6` |
| Back-end | `695bfb43ab63d125f7366aa6` |
| Управление | `695bfb653ef81125f7366ad5` |

## Известные ограничения

- Delete endpoint → 404, используй `complete` вместо удаления
- Для complete нужны оба: project_id + task_id
