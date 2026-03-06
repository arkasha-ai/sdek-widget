# GitHub 🐙

## ✅ СТАТУС: arkasha-bot АКТИВЕН (20.02.2026)

**Аккаунт:** `arkasha-bot` — машинный аккаунт для CI/CD и автоматизации  
**Email:** `arkadiy@jakeberrimor.com`  
**Owner:** @topitip  
**Орги:** @LuminesFox (добавлен 25.02.2026)

### Медленный старт (правильный подход)
- ✅ Bio: "🤖 Machine account. Owner: @topitip" — добавлен через browser
- ✅ SSH key добавлен
- ✅ PAT создан (repo scope)
- **НЕ делать:** Коммиты в первые 2-3 дня
- **Цель:** Избежать антиспам триггеров GitHub

---

## Credentials arkasha-bot

- **Username:** `arkasha-bot`
- **Email:** `arkadiy@jakeberrimor.com`
- **Password:** `~/.openclaw/secrets.env` → GITHUB_ARKASHA_BOT_PASSWORD
- **PAT:** `~/.openclaw/secrets.env` → GITHUB_ARKASHA_BOT_TOKEN
- **SSH key:** `~/.ssh/github_arkasha_bot`

## SSH Config

```bash
Host github.com-arkasha-bot
  HostName github.com
  User git
  IdentityFile ~/.ssh/github_arkasha_bot
  IdentitiesOnly yes
```

**Usage:**
```bash
git clone git@github.com-arkasha-bot:user/repo.git
```

---

## ✅ СТАТУС: arkasha-ai АКТИВЕН (разблокирован 25.02.2026)

**Причина блокировки:** Новый аккаунт + 8 коммитов за ночь = антиспам триггер GitHub.  
**Разблокирован:** GitHub Support тикет #4087174, Brian ответил за 10 минут.
**Роль:** Основной аккаунт, человекоподобное присутствие, личные репо, старые проекты.

**Personal account Denis:** `topitip` — НЕ использовать для автоматизации (защищаем личный аккаунт)!

---

## Старые credentials arkasha-ai (заблокирован)

- **Username:** `arkasha-ai`
- **Email:** `a.parmeev@jakeberrimor.com`
- **Password:** `~/.openclaw/secrets.env` → ARKADY_PASSWORD
- **SSH key:** `~/.ssh/github_arkasha`

## 2FA (если понадобится для arkasha-bot)

```bash
oathtool --totp --base32 "$(grep GITHUB_2FA_SECRET ~/.openclaw/secrets.env | cut -d= -f2)"
# Secret: GITHUB_2FA_SECRET=MDI5DUTHXV2ELVBI
```

---

## GitHub CLI (gh)

```bash
gh auth login
gh auth status
```

**Token:** Use `GITHUB_ARKASHA_BOT_TOKEN` from secrets.env

---

## Repos (arkasha-ai, заблокированы)

- `arkasha-ai/archdoc` — Fork от topitip/archdoc (ветка feature/improvements-v2)
- `topitip/openclaw-imap-idle` — Collaborator access

---

## GitHub Notifications (IMAP IDLE)

1. GitHub mention → email на `arkadiy@jakeberrimor.com`
2. IMAP IDLE listener ловит мгновенно (<1 sec)
3. Webhook триггерит меня

**IMAP listener:** `scripts/imap_idle_listener_v2.py` (5 accounts включая arkadiy)

---

## Best Practices (после arkasha-ai бана)

1. **Bio сразу:** "🤖 Machine account. Owner: @topitip"
2. **Медленный старт:** Первые 2-3 дня никаких коммитов
3. **Не спамить:** Максимум 1-2 PR/день в первую неделю
4. **GitHub Pro?** Можно подумать ($4/мес) для легитимности
5. **Organization:** Denis может создать через topitip, добавить arkasha-bot

---

_Обновлено: 2026-02-20 23:50_
