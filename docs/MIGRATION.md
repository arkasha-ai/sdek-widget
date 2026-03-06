# MIGRATION.md — Перенос Аркаши на новый сервер

> Этот документ описывает полное восстановление без потери памяти, настроек и личности.
> Последнее обновление: 2026-03-06

---

## Что составляет "меня"

1. **Личность и правила** — `SOUL.md`, `AGENTS.md`, `IDENTITY.md`, `USER.md`, `MEMORY.md`, `HEARTBEAT.md`
2. **Долгосрочная память** — `memory/*.md`, `memory/projects/`, `memory/tools/`, `memory/rules/`, `memory/people/`
3. **Состояние** — `memory/state/*.json` (heartbeat, lastDenisMessageAt и т.д.)
4. **Скрипты** — `scripts/`
5. **История разговоров** — `agents/main/sessions/*.jsonl` (из S3)
6. **OpenClaw config** — `~/.openclaw/config.json` (из S3)
7. **Секреты** — `~/.openclaw/secrets.env` (нужно передать вручную!)

---

## Шаг 1: Подготовка нового сервера

```bash
# Создать пользователя clawdbot
adduser clawdbot
usermod -aG sudo,adm,docker clawdbot

# Войти под clawdbot
su - clawdbot
```

## Шаг 2: Установить OpenClaw

```bash
# Установить Node.js (через nvm или apt)
curl -fsSL https://deb.nodesource.com/setup_22.x | sudo -E bash -
sudo apt-get install -y nodejs

# Установить OpenClaw
npm install -g openclaw

# Инициализировать
openclaw init
```

## Шаг 3: Восстановить workspace из git

```bash
cd ~/.openclaw

# Клонировать workspace
git clone git@github.com:arkasha-ai/arkasha-workspace-backup.git workspace

# Настроить SSH ключ для GitHub (arkasha-ai аккаунт)
# Ключ хранится в ~/.ssh/github_arkasha — взять из secrets.env или создать новый
ssh-keygen -t ed25519 -C "arkasha@jakeberrimor.com" -f ~/.ssh/github_arkasha
# Добавить pub ключ в GitHub: https://github.com/settings/keys (аккаунт arkasha-ai)

cat >> ~/.ssh/config << 'EOF'
Host github.com-arkasha
    HostName github.com
    User git
    IdentityFile ~/.ssh/github_arkasha
EOF
```

## Шаг 4: Восстановить сессии и снапшот из S3

```bash
pip3 install s3cmd --break-system-packages

cat > ~/.s3cfg << 'EOF'
[default]
access_key = L2TXSHMAN2Z8AWF6BIXZ
secret_key = Ks4w19KlpPmJxhZXsoFAgzdGTpEEy0eEzt7mj75O
host_base = s3.firstvds.ru
host_bucket = %(bucket)s.s3.firstvds.ru
use_https = True
signature_v2 = False
EOF

# Восстановить сессии
mkdir -p ~/.openclaw/agents/main/sessions
s3cmd sync s3://arkasha/sessions/ ~/.openclaw/agents/main/sessions/

# Восстановить workspace snapshot (если git не достаточно)
# s3cmd get s3://arkasha/workspace-snapshots/workspace-YYYY-MM-DD.tar.gz /tmp/ws.tar.gz
# tar -xzf /tmp/ws.tar.gz -C ~/.openclaw/
```

## Шаг 5: Восстановить secrets

```bash
# Скачать зашифрованный файл из S3
s3cmd get s3://arkasha/secrets/secrets.env.enc /tmp/secrets.env.enc

# Расшифровать (нужен пароль который знает только Денис)
openssl enc -d -aes-256-cbc -pbkdf2 -iter 600000 \
  -in /tmp/secrets.env.enc \
  -out ~/.openclaw/secrets.env \
  -pass pass:'ВАШ_ПАРОЛЬ'

chmod 600 ~/.openclaw/secrets.env
rm /tmp/secrets.env.enc
```

> Пароль хранится только у Дениса. Файл зашифрован AES-256.

## Шаг 6: Восстановить OpenClaw config

```bash
# Из S3 (последний сохранённый)
s3cmd ls s3://arkasha/config/ | tail -5  # найти последний
s3cmd get s3://arkasha/config/config-YYYY-MM-DD.json ~/.openclaw/config.json

# Или вручную от Дениса
```

## Шаг 7: Настроить systemd сервисы

```bash
# OpenClaw Gateway
mkdir -p ~/.config/systemd/user/

cat > ~/.config/systemd/user/openclaw-gateway.service << 'EOF'
[Unit]
Description=OpenClaw Gateway
After=network-online.target
Wants=network-online.target

[Service]
ExecStart=/usr/bin/node /home/clawdbot/.npm-global/lib/node_modules/openclaw/dist/index.js gateway --port 18789
Restart=always
RestartSec=5
MemoryMax=1500M
MemorySwapMax=512M
KillMode=process
Environment=HOME=/home/clawdbot
Environment=OPENCLAW_GATEWAY_PORT=18789
# Остальные env из оригинального .service файла

[Install]
WantedBy=default.target
EOF

systemctl --user daemon-reload
systemctl --user enable openclaw-gateway
systemctl --user start openclaw-gateway

# Включить lingering (запуск при загрузке без логина)
sudo loginctl enable-linger clawdbot
```

## Шаг 8: Восстановить вспомогательные сервисы

```bash
# IMAP idle listener
cat > ~/.config/systemd/user/imap-idle.service << 'EOF'
[Unit]
Description=IMAP IDLE Listener
After=network-online.target

[Service]
ExecStart=/usr/bin/python3 /home/clawdbot/.openclaw/workspace/scripts/imap_idle_listener_v2.py
Restart=always
RestartSec=10
Environment=HOME=/home/clawdbot

[Install]
WantedBy=default.target
EOF

# Arkadiy userbot
cat > ~/.config/systemd/user/arkadiy-userbot.service << 'EOF'
[Unit]
Description=Arkadiy Telegram Userbot
After=network-online.target

[Service]
ExecStart=/usr/bin/python3 /home/clawdbot/.openclaw/workspace/scripts/arkadiy_userbot.py
Restart=always
RestartSec=10
Environment=HOME=/home/clawdbot

[Install]
WantedBy=default.target
EOF

systemctl --user enable imap-idle arkadiy-userbot
systemctl --user start imap-idle arkadiy-userbot
```

## Шаг 9: Восстановить crontab

```bash
crontab << 'EOF'
7 * * * * cd ~/.openclaw/workspace && python3 scripts/qdrant_indexer.py index-memory >> /tmp/memory-index.log 2>&1
30 3 * * * cd ~/.openclaw/workspace && git add -A && git diff --cached --quiet || git commit -m "auto: daily workspace sync $(date +%Y-%m-%d)" && git push origin master >> /tmp/git-sync.log 2>&1
0 4 * * * bash ~/.openclaw/workspace/scripts/s3_backup.sh >> /tmp/s3-backup.log 2>&1
EOF
```

## Шаг 10: Добавить swap

```bash
sudo fallocate -l 2G /swapfile2
sudo chmod 600 /swapfile2
sudo mkswap /swapfile2
sudo swapon /swapfile2
echo '/swapfile2 none swap sw 0 0' | sudo tee -a /etc/fstab
```

## Шаг 11: Проверка

```bash
# OpenClaw запущен?
systemctl --user status openclaw-gateway

# Могу ответить в Telegram?
# → Написать "Аркаш, ты там?" в личку

# Память на месте?
# → Написать "что ты помнишь обо мне?"

# Cron работает?
crontab -l
```

---

## Чеклист восстановления

- [ ] clawdbot создан, в группах sudo/adm/docker
- [ ] OpenClaw установлен
- [ ] Workspace клонирован из git
- [ ] Сессии восстановлены из S3
- [ ] secrets.env на месте (от Дениса вручную)
- [ ] config.json восстановлен
- [ ] openclaw-gateway.service запущен и в автозапуске
- [ ] imap-idle.service запущен
- [ ] arkadiy-userbot.service запущен
- [ ] crontab настроен
- [ ] swap добавлен
- [ ] Тест: Аркаша отвечает в Telegram и помнит Дениса

---

## Время восстановления

~20-30 минут при наличии secrets.env от Дениса.

## Контакты / Ссылки

- GitHub workspace: `git@github.com-arkasha:arkasha-ai/arkasha-workspace-backup.git`
- S3 bucket: `s3://arkasha` на `s3.firstvds.ru`
- OpenClaw docs: `/home/clawdbot/.openclaw/workspace/docs/`
