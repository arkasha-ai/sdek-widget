---
name: dokploy
description: "Manage Dokploy deployments, projects, applications, and domains via the Dokploy API."
emoji: "🐳"
metadata:
  clawdhub:
    requires:
      bins: ["curl", "jq"]
---

# Dokploy Skill

Dokploy — self-hosted PaaS (аналог Vercel/Heroku) для деплоя приложений, баз данных, Docker Compose стеков. Управляет Traefik, Let's Encrypt, Docker Swarm.

Этот скилл позволяет агенту полностью управлять Dokploy через REST API: создавать проекты, деплоить приложения, настраивать домены, управлять базами данных.

## Конфигурация

```bash
# Из ~/.openclaw/secrets.env
DOKPLOY_API_URL="https://dokploy.jakeberrimor.com"
DOKPLOY_API_KEY="<64-символьный ключ>"
```

## Аутентификация

Все запросы требуют заголовок `x-api-key`:

```bash
source ~/.openclaw/secrets.env
curl -s -H "x-api-key: $DOKPLOY_API_KEY" "$DOKPLOY_API_URL/api/<endpoint>"
```

**Базовый URL:** `$DOKPLOY_API_URL/api`

**Формат:**
- GET-запросы: параметры в query string
- POST-запросы: JSON body с `Content-Type: application/json`
- Ответы: JSON

**Шаблон для всех curl-запросов:**
```bash
source ~/.openclaw/secrets.env
API="$DOKPLOY_API_URL/api"
AUTH="-H 'x-api-key: $DOKPLOY_API_KEY'"
```

---

## 1. Projects (Проекты)

Проект — верхний уровень организации. Содержит environments, которые содержат сервисы.

### Список всех проектов
```bash
curl -s -H "x-api-key: $DOKPLOY_API_KEY" "$DOKPLOY_API_URL/api/project.all" | jq
```

### Получить проект по ID
```bash
curl -s -H "x-api-key: $DOKPLOY_API_KEY" "$DOKPLOY_API_URL/api/project.one?projectId=<ID>" | jq
```

### Создать проект
```bash
curl -s -X POST -H "x-api-key: $DOKPLOY_API_KEY" -H "Content-Type: application/json" \
  "$DOKPLOY_API_URL/api/project.create" \
  -d '{"name": "My Project", "description": "Optional description"}' | jq
```

### Обновить проект
```bash
curl -s -X POST -H "x-api-key: $DOKPLOY_API_KEY" -H "Content-Type: application/json" \
  "$DOKPLOY_API_URL/api/project.update" \
  -d '{"projectId": "<ID>", "name": "New Name", "description": "Updated"}' | jq
```

### Удалить проект
```bash
curl -s -X POST -H "x-api-key: $DOKPLOY_API_KEY" -H "Content-Type: application/json" \
  "$DOKPLOY_API_URL/api/project.remove" \
  -d '{"projectId": "<ID>"}' | jq
```

### Дублировать проект
```bash
curl -s -X POST -H "x-api-key: $DOKPLOY_API_KEY" -H "Content-Type: application/json" \
  "$DOKPLOY_API_URL/api/project.duplicate" \
  -d '{"sourceEnvironmentId": "<ENV_ID>", "name": "Copy", "includeServices": true}' | jq
```

---

## 2. Environments (Окружения)

Каждый проект содержит environments (production, staging и т.д.). Сервисы создаются внутри environment.

### Список environments проекта
```bash
curl -s -H "x-api-key: $DOKPLOY_API_KEY" \
  "$DOKPLOY_API_URL/api/environment.byProjectId?projectId=<PROJECT_ID>" | jq
```

### Получить environment
```bash
curl -s -H "x-api-key: $DOKPLOY_API_KEY" \
  "$DOKPLOY_API_URL/api/environment.one?environmentId=<ENV_ID>" | jq
```

### Создать environment
```bash
curl -s -X POST -H "x-api-key: $DOKPLOY_API_KEY" -H "Content-Type: application/json" \
  "$DOKPLOY_API_URL/api/environment.create" \
  -d '{"name": "staging", "projectId": "<PROJECT_ID>"}' | jq
```

### Обновить / Удалить / Дублировать
```bash
# Update
curl -s -X POST ... "$DOKPLOY_API_URL/api/environment.update" \
  -d '{"environmentId": "<ID>", "name": "production"}'

# Remove
curl -s -X POST ... "$DOKPLOY_API_URL/api/environment.remove" \
  -d '{"environmentId": "<ID>"}'

# Duplicate
curl -s -X POST ... "$DOKPLOY_API_URL/api/environment.duplicate" \
  -d '{"environmentId": "<ID>", "name": "staging-copy"}'
```

---

## 3. Applications (Приложения)

Приложение — основная единица деплоя. Поддерживает разные source types и build types.

### Создать приложение
```bash
curl -s -X POST -H "x-api-key: $DOKPLOY_API_KEY" -H "Content-Type: application/json" \
  "$DOKPLOY_API_URL/api/application.create" \
  -d '{"name": "my-app", "environmentId": "<ENV_ID>"}' | jq
```
**Параметры:** `name`* (required), `appName` (Docker name), `description`, `environmentId`* (required), `serverId`

### Получить приложение
```bash
curl -s -H "x-api-key: $DOKPLOY_API_KEY" \
  "$DOKPLOY_API_URL/api/application.one?applicationId=<APP_ID>" | jq
```

### Настроить Docker image (без GitHub!)
```bash
curl -s -X POST -H "x-api-key: $DOKPLOY_API_KEY" -H "Content-Type: application/json" \
  "$DOKPLOY_API_URL/api/application.saveDockerProvider" \
  -d '{"applicationId": "<APP_ID>", "dockerImage": "nginx:latest"}' | jq
```
**Параметры:** `applicationId`*, `dockerImage`, `username`, `password`, `registryUrl`

### Настроить build type
```bash
curl -s -X POST -H "x-api-key: $DOKPLOY_API_KEY" -H "Content-Type: application/json" \
  "$DOKPLOY_API_URL/api/application.saveBuildType" \
  -d '{
    "applicationId": "<APP_ID>",
    "buildType": "dockerfile",
    "dockerfile": "Dockerfile",
    "dockerContextPath": "."
  }' | jq
```
**buildType:** `"dockerfile"` | `"herokuish"` | `"paketo"` | `"nixpacks"` | `"static"` | `"railpack"`

### Сохранить environment variables
```bash
curl -s -X POST -H "x-api-key: $DOKPLOY_API_KEY" -H "Content-Type: application/json" \
  "$DOKPLOY_API_URL/api/application.saveEnvironment" \
  -d '{
    "applicationId": "<APP_ID>",
    "env": "DATABASE_URL=postgres://...\nNODE_ENV=production"
  }' | jq
```
**Формат env:** строка с `KEY=VALUE`, разделённая `\n`

### Деплой приложения
```bash
curl -s -X POST -H "x-api-key: $DOKPLOY_API_KEY" -H "Content-Type: application/json" \
  "$DOKPLOY_API_URL/api/application.deploy" \
  -d '{"applicationId": "<APP_ID>"}' | jq
```

### Редеплой
```bash
curl -s -X POST -H "x-api-key: $DOKPLOY_API_KEY" -H "Content-Type: application/json" \
  "$DOKPLOY_API_URL/api/application.redeploy" \
  -d '{"applicationId": "<APP_ID>"}' | jq
```

### Start / Stop / Delete
```bash
# Start
curl -s -X POST ... "$DOKPLOY_API_URL/api/application.start" \
  -d '{"applicationId": "<APP_ID>"}'

# Stop
curl -s -X POST ... "$DOKPLOY_API_URL/api/application.stop" \
  -d '{"applicationId": "<APP_ID>"}'

# Delete
curl -s -X POST ... "$DOKPLOY_API_URL/api/application.delete" \
  -d '{"applicationId": "<APP_ID>"}'
```

### Обновить приложение (update)
```bash
curl -s -X POST -H "x-api-key: $DOKPLOY_API_KEY" -H "Content-Type: application/json" \
  "$DOKPLOY_API_URL/api/application.update" \
  -d '{
    "applicationId": "<APP_ID>",
    "name": "new-name",
    "memoryLimit": "512m",
    "cpuLimit": "0.5"
  }' | jq
```

### Git providers (GitHub/GitLab/Gitea/Bitbucket/Custom Git)
```bash
# GitHub
curl -s -X POST ... "$DOKPLOY_API_URL/api/application.saveGithubProvider" \
  -d '{"applicationId":"<ID>","repository":"repo","branch":"main","owner":"user","githubId":"<GH_ID>"}'

# GitLab
curl -s -X POST ... "$DOKPLOY_API_URL/api/application.saveGitlabProvider" \
  -d '{"applicationId":"<ID>","gitlabRepository":"repo","gitlabBranch":"main","gitlabOwner":"user","gitlabId":"<GL_ID>","gitlabProjectId":123,"gitlabPathNamespace":"user/repo"}'

# Gitea
curl -s -X POST ... "$DOKPLOY_API_URL/api/application.saveGiteaProvider" \
  -d '{"applicationId":"<ID>","giteaRepository":"repo","giteaBranch":"main","giteaOwner":"user","giteaId":"<GITEA_ID>"}'

# Custom Git (SSH/HTTPS)
curl -s -X POST ... "$DOKPLOY_API_URL/api/application.saveGitProvider" \
  -d '{"applicationId":"<ID>","customGitUrl":"git@github.com:user/repo.git","customGitBranch":"main","customGitSSHKeyId":"<KEY_ID>"}'

# Disconnect git provider
curl -s -X POST ... "$DOKPLOY_API_URL/api/application.disconnectGitProvider" \
  -d '{"applicationId":"<ID>"}'
```

### Прочие операции
```bash
# Clean build queues
POST /application.cleanQueues {"applicationId":"<ID>"}

# Kill running build
POST /application.killBuild {"applicationId":"<ID>"}

# Cancel deployment
POST /application.cancelDeployment {"applicationId":"<ID>"}

# Move to another environment
POST /application.move {"applicationId":"<ID>","targetEnvironmentId":"<ENV_ID>"}

# Read Traefik config
GET /application.readTraefikConfig?applicationId=<ID>

# Update Traefik config
POST /application.updateTraefikConfig {"applicationId":"<ID>","traefikConfig":"..."}

# Read app monitoring
GET /application.readAppMonitoring?appName=<NAME>

# Refresh token
POST /application.refreshToken {"applicationId":"<ID>"}
```

---

## 4. Domains (Домены)

### Создать домен для приложения
```bash
curl -s -X POST -H "x-api-key: $DOKPLOY_API_KEY" -H "Content-Type: application/json" \
  "$DOKPLOY_API_URL/api/domain.create" \
  -d '{
    "host": "app.example.com",
    "applicationId": "<APP_ID>",
    "port": 3000,
    "https": true,
    "certificateType": "letsencrypt"
  }' | jq
```

**Параметры:**
- `host`* — доменное имя (без https://)
- `applicationId` или `composeId` — привязка к сервису
- `port` — порт контейнера (1-65535)
- `https` — включить HTTPS
- `certificateType` — `"letsencrypt"` | `"none"` | `"custom"`
- `path` — путь (например `/api`)
- `serviceName` — для compose (имя сервиса)
- `domainType` — `"application"` | `"compose"` | `"preview"`
- `internalPath` — внутренний путь для проксирования
- `stripPath` — убирать path при проксировании

### Домены приложения
```bash
curl -s -H "x-api-key: $DOKPLOY_API_KEY" \
  "$DOKPLOY_API_URL/api/domain.byApplicationId?applicationId=<APP_ID>" | jq
```

### Домены compose
```bash
curl -s -H "x-api-key: $DOKPLOY_API_KEY" \
  "$DOKPLOY_API_URL/api/domain.byComposeId?composeId=<COMPOSE_ID>" | jq
```

### Обновить домен
```bash
curl -s -X POST -H "x-api-key: $DOKPLOY_API_KEY" -H "Content-Type: application/json" \
  "$DOKPLOY_API_URL/api/domain.update" \
  -d '{"domainId": "<ID>", "host": "new.example.com", "port": 8080, "https": true}' | jq
```

### Удалить домен
```bash
curl -s -X POST ... "$DOKPLOY_API_URL/api/domain.delete" \
  -d '{"domainId": "<ID>"}'
```

### Сгенерировать домен (traefik.me)
```bash
curl -s -X POST ... "$DOKPLOY_API_URL/api/domain.generateDomain" \
  -d '{"appName": "my-app"}'
```

### Валидировать DNS
```bash
curl -s -X POST ... "$DOKPLOY_API_URL/api/domain.validateDomain" \
  -d '{"domain": "app.example.com"}'
```

---

## 5. Compose (Docker Compose)

### Создать compose сервис
```bash
curl -s -X POST -H "x-api-key: $DOKPLOY_API_KEY" -H "Content-Type: application/json" \
  "$DOKPLOY_API_URL/api/compose.create" \
  -d '{
    "name": "my-stack",
    "environmentId": "<ENV_ID>",
    "composeType": "docker-compose",
    "composeFile": "version: \"3.8\"\nservices:\n  web:\n    image: nginx:latest\n    ports:\n      - \"80:80\""
  }' | jq
```
**composeType:** `"docker-compose"` | `"stack"` (Docker Swarm)

### Получить compose
```bash
curl -s -H "x-api-key: $DOKPLOY_API_KEY" \
  "$DOKPLOY_API_URL/api/compose.one?composeId=<ID>" | jq
```

### Обновить compose
```bash
curl -s -X POST ... "$DOKPLOY_API_URL/api/compose.update" \
  -d '{
    "composeId": "<ID>",
    "composeFile": "version: 3.8\nservices:\n  ...",
    "env": "KEY=VALUE\nKEY2=VALUE2",
    "sourceType": "raw"
  }' | jq
```
**sourceType:** `"git"` | `"github"` | `"gitlab"` | `"bitbucket"` | `"gitea"` | `"raw"`

### Deploy / Redeploy / Stop / Start
```bash
# Deploy
curl -s -X POST ... "$DOKPLOY_API_URL/api/compose.deploy" \
  -d '{"composeId": "<ID>"}'

# Redeploy
curl -s -X POST ... "$DOKPLOY_API_URL/api/compose.redeploy" \
  -d '{"composeId": "<ID>"}'

# Stop
curl -s -X POST ... "$DOKPLOY_API_URL/api/compose.stop" \
  -d '{"composeId": "<ID>"}'

# Start
curl -s -X POST ... "$DOKPLOY_API_URL/api/compose.start" \
  -d '{"composeId": "<ID>"}'
```

### Удалить compose
```bash
curl -s -X POST ... "$DOKPLOY_API_URL/api/compose.delete" \
  -d '{"composeId": "<ID>", "deleteVolumes": false}'
```

### Load services (получить список сервисов из compose file)
```bash
curl -s -H "x-api-key: $DOKPLOY_API_KEY" \
  "$DOKPLOY_API_URL/api/compose.loadServices?composeId=<ID>" | jq
```

### Deploy from template
```bash
curl -s -X POST ... "$DOKPLOY_API_URL/api/compose.deployTemplate" \
  -d '{"environmentId": "<ENV_ID>", "id": "<TEMPLATE_ID>"}'
```

### Список шаблонов
```bash
curl -s -H "x-api-key: $DOKPLOY_API_KEY" \
  "$DOKPLOY_API_URL/api/compose.templates" | jq
```

---

## 6. Deployments (Деплойменты — логи и история)

### Список деплойментов приложения
```bash
curl -s -H "x-api-key: $DOKPLOY_API_KEY" \
  "$DOKPLOY_API_URL/api/deployment.all?applicationId=<APP_ID>" | jq
```

### Деплойменты compose
```bash
curl -s -H "x-api-key: $DOKPLOY_API_KEY" \
  "$DOKPLOY_API_URL/api/deployment.allByCompose?composeId=<ID>" | jq
```

### Деплойменты по типу
```bash
curl -s -H "x-api-key: $DOKPLOY_API_KEY" \
  "$DOKPLOY_API_URL/api/deployment.allByType?id=<ID>&type=application" | jq
# type: application | compose | server | schedule | previewDeployment | backup | volumeBackup
```

### Kill deployment process
```bash
curl -s -X POST ... "$DOKPLOY_API_URL/api/deployment.killProcess" \
  -d '{"deploymentId": "<ID>"}'
```

---

## 7. Databases (Базы данных)

Поддерживаются: PostgreSQL, MySQL, MariaDB, MongoDB, Redis. API идентичный для всех.

### PostgreSQL — создать
```bash
curl -s -X POST -H "x-api-key: $DOKPLOY_API_KEY" -H "Content-Type: application/json" \
  "$DOKPLOY_API_URL/api/postgres.create" \
  -d '{
    "name": "my-postgres",
    "databaseName": "mydb",
    "databaseUser": "admin",
    "databasePassword": "secret123",
    "dockerImage": "postgres:16",
    "environmentId": "<ENV_ID>"
  }' | jq
```

### MySQL — создать
```bash
curl -s -X POST ... "$DOKPLOY_API_URL/api/mysql.create" \
  -d '{
    "name": "my-mysql",
    "databaseName": "mydb",
    "databaseUser": "admin",
    "databasePassword": "secret123",
    "dockerImage": "mysql:8",
    "environmentId": "<ENV_ID>"
  }'
```

### Redis — создать
```bash
curl -s -X POST ... "$DOKPLOY_API_URL/api/redis.create" \
  -d '{
    "name": "my-redis",
    "databasePassword": "secret123",
    "dockerImage": "redis:8",
    "environmentId": "<ENV_ID>"
  }'
```

### MongoDB — создать
```bash
curl -s -X POST ... "$DOKPLOY_API_URL/api/mongo.create" \
  -d '{
    "name": "my-mongo",
    "databaseUser": "admin",
    "databasePassword": "secret123",
    "environmentId": "<ENV_ID>"
  }'
```

### MariaDB — создать
```bash
curl -s -X POST ... "$DOKPLOY_API_URL/api/mariadb.create" \
  -d '{
    "name": "my-mariadb",
    "databaseName": "mydb",
    "databaseUser": "admin",
    "databasePassword": "secret123",
    "environmentId": "<ENV_ID>"
  }'
```

### Общие операции для всех БД (замените `postgres` на `mysql`/`redis`/`mongo`/`mariadb`)
```bash
# Получить
GET /postgres.one?postgresId=<ID>

# Start / Stop / Deploy / Rebuild
POST /postgres.start     {"postgresId":"<ID>"}
POST /postgres.stop      {"postgresId":"<ID>"}
POST /postgres.deploy    {"postgresId":"<ID>"}
POST /postgres.rebuild   {"postgresId":"<ID>"}

# Сохранить env переменные
POST /postgres.saveEnvironment {"postgresId":"<ID>","env":"KEY=VALUE"}

# Настроить external port
POST /postgres.saveExternalPort {"postgresId":"<ID>","externalPort":5432}

# Удалить
POST /postgres.remove {"postgresId":"<ID>"}

# Переместить в другой environment
POST /postgres.move {"postgresId":"<ID>","targetEnvironmentId":"<ENV_ID>"}

# Изменить статус
POST /postgres.changeStatus {"postgresId":"<ID>","applicationStatus":"running"}
# applicationStatus: "idle" | "running" | "done" | "error"
```

---

## 8. Mounts (Тома и файлы)

### Создать mount
```bash
curl -s -X POST -H "x-api-key: $DOKPLOY_API_KEY" -H "Content-Type: application/json" \
  "$DOKPLOY_API_URL/api/mounts.create" \
  -d '{
    "type": "volume",
    "mountPath": "/data",
    "volumeName": "my-data",
    "serviceId": "<APP_ID>",
    "serviceType": "application"
  }' | jq
```
**type:** `"bind"` | `"volume"` | `"file"`
**serviceType:** `"application"` | `"postgres"` | `"mysql"` | `"mariadb"` | `"mongo"` | `"redis"` | `"compose"`

### File mount (встроить файл в контейнер)
```bash
curl -s -X POST ... "$DOKPLOY_API_URL/api/mounts.create" \
  -d '{
    "type": "file",
    "mountPath": "/app/config.json",
    "content": "{\"key\": \"value\"}",
    "serviceId": "<APP_ID>"
  }'
```

### Список mounts приложения
```bash
curl -s -H "x-api-key: $DOKPLOY_API_KEY" \
  "$DOKPLOY_API_URL/api/mounts.allNamedByApplicationId?applicationId=<APP_ID>" | jq
```

### Update / Remove
```bash
POST /mounts.update {"mountId":"<ID>","mountPath":"/new/path"}
POST /mounts.remove {"mountId":"<ID>"}
GET  /mounts.one?mountId=<ID>
```

---

## 9. Ports (Прямое проброс портов)

### Создать port mapping
```bash
curl -s -X POST -H "x-api-key: $DOKPLOY_API_KEY" -H "Content-Type: application/json" \
  "$DOKPLOY_API_URL/api/port.create" \
  -d '{
    "applicationId": "<APP_ID>",
    "publishedPort": 8080,
    "targetPort": 3000,
    "protocol": "tcp"
  }' | jq
```
**protocol:** `"tcp"` | `"udp"`
**publishMode:** `"ingress"` | `"host"`

### Update / Delete
```bash
POST /port.update {"portId":"<ID>","publishedPort":9090,"targetPort":3000}
POST /port.delete {"portId":"<ID>"}
GET  /port.one?portId=<ID>
```

---

## 10. Security (Basic Auth для приложений)

```bash
# Создать basic auth
POST /security.create {"applicationId":"<ID>","username":"admin","password":"secret"}

# Обновить
POST /security.update {"securityId":"<ID>","username":"admin","password":"newsecret"}

# Удалить
POST /security.delete {"securityId":"<ID>"}

# Получить
GET  /security.one?securityId=<ID>
```

---

## 11. Redirects (Перенаправления)

```bash
# Создать redirect
POST /redirects.create {"applicationId":"<ID>","regex":"^/old/(.*)","replacement":"/new/$1","permanent":true}

# Обновить
POST /redirects.update {"redirectId":"<ID>","regex":"^/api/v1/(.*)","replacement":"/api/v2/$1","permanent":false}

# Удалить
POST /redirects.delete {"redirectId":"<ID>"}
```

---

## 12. Docker (Контейнеры)

```bash
# Список контейнеров
GET /docker.getContainers

# Перезапустить контейнер
POST /docker.restartContainer {"containerId":"<ID>"}

# Конфиг контейнера
GET /docker.getConfig?containerId=<ID>

# Контейнеры по имени приложения
GET /docker.getContainersByAppNameMatch?appName=<NAME>
GET /docker.getContainersByAppLabel?appName=<NAME>&type=application
GET /docker.getStackContainersByAppName?appName=<NAME>
GET /docker.getServiceContainersByAppName?appName=<NAME>
```

---

## 13. Backups (Резервные копии)

### Создать backup
```bash
curl -s -X POST -H "x-api-key: $DOKPLOY_API_KEY" -H "Content-Type: application/json" \
  "$DOKPLOY_API_URL/api/backup.create" \
  -d '{
    "schedule": "0 2 * * *",
    "prefix": "daily-backup",
    "database": "mydb",
    "databaseType": "postgres",
    "postgresId": "<PG_ID>",
    "destinationId": "<DEST_ID>",
    "enabled": true
  }' | jq
```
**databaseType:** `"postgres"` | `"mariadb"` | `"mysql"` | `"mongo"` | `"web-server"`

### Ручной backup
```bash
POST /backup.manualBackupPostgres  {"backupId":"<ID>"}
POST /backup.manualBackupMySql     {"backupId":"<ID>"}
POST /backup.manualBackupMariadb   {"backupId":"<ID>"}
POST /backup.manualBackupMongo     {"backupId":"<ID>"}
POST /backup.manualBackupCompose   {"backupId":"<ID>"}
POST /backup.manualBackupWebServer {"backupId":"<ID>"}
```

### Список файлов backup
```bash
GET /backup.listBackupFiles?destinationId=<ID>&search=<prefix>
```

---

## 14. Destinations (S3-совместимые хранилища для бэкапов)

```bash
# Создать
POST /destination.create {
  "name":"s3-backup","accessKey":"...","secretAccessKey":"...",
  "bucket":"backups","region":"us-east-1","endpoint":"https://s3.amazonaws.com",
  "provider":"aws"
}

# Тест подключения
POST /destination.testConnection {<same params>}

# Список
GET /destination.all

# Удалить
POST /destination.remove {"destinationId":"<ID>"}
```

---

## 15. Registry (Docker Registry)

```bash
# Создать
POST /registry.create {
  "registryName":"ghcr","username":"user","password":"token",
  "registryUrl":"https://ghcr.io","registryType":"cloud","imagePrefix":"user"
}

# Тест
POST /registry.testRegistry {"username":"...","password":"...","registryUrl":"...","registryType":"cloud"}

# Список
GET /registry.all

# Удалить
POST /registry.remove {"registryId":"<ID>"}
```

---

## 16. SSH Keys

```bash
# Сгенерировать ключ
POST /sshKey.generate {"type":"ed25519"}  # или "rsa"

# Создать (импорт)
POST /sshKey.create {"name":"my-key","privateKey":"...","publicKey":"...","organizationId":"<ORG_ID>"}

# Список
GET /sshKey.all

# Удалить
POST /sshKey.remove {"sshKeyId":"<ID>"}
```

---

## 17. Servers (Удалённые серверы)

```bash
# Создать
POST /server.create {
  "name":"prod-server","ipAddress":"1.2.3.4","port":22,
  "username":"root","sshKeyId":"<KEY_ID>","serverType":"deploy"
}
# serverType: "deploy" | "build"

# Список
GET /server.all

# Setup (установить Docker, Swarm и т.д.)
POST /server.setup {"serverId":"<ID>"}

# Validate
GET /server.validate?serverId=<ID>

# Public IP
GET /server.publicIp

# Remove
POST /server.remove {"serverId":"<ID>"}
```

---

## 18. Notifications (Уведомления)

Поддерживаются: Slack, Telegram, Discord, Email, Resend, Gotify, Ntfy, Custom, Lark, Pushover.

### Создать Telegram уведомление
```bash
curl -s -X POST -H "x-api-key: $DOKPLOY_API_KEY" -H "Content-Type: application/json" \
  "$DOKPLOY_API_URL/api/notification.createTelegram" \
  -d '{
    "name": "deploy-alerts",
    "botToken": "<BOT_TOKEN>",
    "chatId": "<CHAT_ID>",
    "messageThreadId": "",
    "appBuildError": true,
    "appDeploy": true,
    "databaseBackup": true,
    "volumeBackup": false,
    "dokployRestart": true,
    "dockerCleanup": false,
    "serverThreshold": true
  }' | jq
```

### Тест подключения
```bash
POST /notification.testTelegramConnection {"botToken":"...","chatId":"...","messageThreadId":""}
```

### Список уведомлений
```bash
GET /notification.all
```

---

## 19. Schedules (Крон-задачи)

```bash
# Создать
POST /schedule.create {
  "name":"cleanup","cronExpression":"0 3 * * *",
  "command":"docker system prune -f",
  "scheduleType":"application","applicationId":"<ID>","shellType":"bash"
}
# scheduleType: "application" | "compose" | "server" | "dokploy-server"

# Список
GET /schedule.list?id=<APP_ID>&scheduleType=application

# Ручной запуск
POST /schedule.runManually {"scheduleId":"<ID>"}

# Удалить
POST /schedule.delete {"scheduleId":"<ID>"}
```

---

## 20. Rollbacks

```bash
# Откатить
POST /rollback.rollback {"rollbackId":"<ID>"}

# Удалить rollback
POST /rollback.delete {"rollbackId":"<ID>"}
```

---

## 21. Preview Deployments

```bash
# Список
GET /previewDeployment.all?applicationId=<ID>

# Одна
GET /previewDeployment.one?previewDeploymentId=<ID>

# Redeploy
POST /previewDeployment.redeploy {"previewDeploymentId":"<ID>"}

# Удалить
POST /previewDeployment.delete {"previewDeploymentId":"<ID>"}
```

---

## 22. Settings (Настройки Dokploy)

### Общее
```bash
# Версия
GET /settings.getDokployVersion

# Здоровье
GET /settings.health

# IP сервера
GET /settings.getIp

# Web server settings
GET /settings.getWebServerSettings
```

### Очистка
```bash
POST /settings.cleanUnusedImages     {"serverId":"<optional>"}
POST /settings.cleanUnusedVolumes    {"serverId":"<optional>"}
POST /settings.cleanStoppedContainers {"serverId":"<optional>"}
POST /settings.cleanDockerBuilder    {"serverId":"<optional>"}
POST /settings.cleanDockerPrune      {"serverId":"<optional>"}
POST /settings.cleanAll              {"serverId":"<optional>"}
POST /settings.cleanMonitoring
POST /settings.cleanAllDeploymentQueue
```

### Traefik
```bash
GET  /settings.readTraefikConfig
POST /settings.updateTraefikConfig {"traefikConfig":"..."}
POST /settings.reloadTraefik {"serverId":"<optional>"}
GET  /settings.readMiddlewareTraefikConfig
POST /settings.updateMiddlewareTraefikConfig {"traefikConfig":"..."}
GET  /settings.readTraefikEnv
POST /settings.writeTraefikEnv {"env":"..."}
```

### Домен для Dokploy dashboard
```bash
POST /settings.assignDomainServer {
  "host":"dokploy.example.com","certificateType":"letsencrypt",
  "letsEncryptEmail":"admin@example.com","https":true
}
```

### Docker cleanup автоматический
```bash
POST /settings.updateDockerCleanup {"enableDockerCleanup":true}
```

### Обновление Dokploy
```bash
POST /settings.getUpdateData
POST /settings.updateServer
```

---

## 23. Git Providers

```bash
# Все провайдеры
GET /gitProvider.getAll

# Удалить
POST /gitProvider.remove {"gitProviderId":"<ID>"}
```

### GitHub
```bash
GET /github.githubProviders
GET /github.getGithubRepositories?githubId=<ID>
GET /github.getGithubBranches?repo=<REPO>&owner=<OWNER>&githubId=<ID>
```

### Gitea
```bash
GET /gitea.giteaProviders
POST /gitea.create {"name":"my-gitea","giteaUrl":"https://git.example.com"}
GET /gitea.getGiteaRepositories?giteaId=<ID>
GET /gitea.getGiteaBranches?owner=<OWNER>&repositoryName=<REPO>&giteaId=<ID>
```

### GitLab / Bitbucket — аналогичная структура

---

## 24. Organizations

```bash
POST /organization.create {"name":"My Org"}
GET  /organization.all
GET  /organization.one?organizationId=<ID>
POST /organization.update {"organizationId":"<ID>","name":"New Name"}
POST /organization.delete {"organizationId":"<ID>"}
POST /organization.setDefault {"organizationId":"<ID>"}
```

---

## 25. Users

```bash
GET  /user.all
GET  /user.get            # текущий пользователь
GET  /user.one?userId=<ID>
POST /user.remove {"userId":"<ID>"}

# Permissions
POST /user.assignPermissions {
  "id":"<USER_ID>",
  "accessedProjects":["<PROJECT_ID>"],
  "accessedEnvironments":["<ENV_ID>"],
  "accessedServices":["<SERVICE_ID>"],
  "canCreateProjects":true,
  "canCreateServices":true,
  "canDeleteProjects":false,
  "canDeleteServices":false,
  "canAccessToDocker":false,
  "canAccessToTraefikFiles":false,
  "canAccessToAPI":true,
  "canAccessToSSHKeys":false,
  "canAccessToGitProviders":false,
  "canDeleteEnvironments":false,
  "canCreateEnvironments":true
}

# API Keys
POST /user.createApiKey {"name":"my-key","metadata":{"organizationId":"<ORG_ID>"}}
POST /user.deleteApiKey {"apiKeyId":"<ID>"}
```

---

## 26. Certificates

```bash
POST /certificates.create {
  "name":"wildcard","certificateData":"...","privateKey":"...",
  "organizationId":"<ORG_ID>"
}
GET  /certificates.all
POST /certificates.remove {"certificateId":"<ID>"}
```

---

## 27. AI (встроенный AI-помощник)

```bash
POST /ai.create {"name":"gpt","apiUrl":"https://api.openai.com/v1","apiKey":"...","model":"gpt-4","isEnabled":true}
GET  /ai.getAll
POST /ai.suggest {"aiId":"<ID>","input":"How to deploy Node.js app?"}
POST /ai.deploy  {"environmentId":"<ID>","id":"<ID>","dockerCompose":"...","envVariables":"...","name":"...","description":"..."}
```

---

## Типичные Workflows

### Workflow 1: Деплой Docker image

```bash
source ~/.openclaw/secrets.env
API="$DOKPLOY_API_URL/api"
H=(-H "x-api-key: $DOKPLOY_API_KEY" -H "Content-Type: application/json")

# 1. Список проектов, найти нужный
PROJECT_ID=$(curl -s -H "x-api-key: $DOKPLOY_API_KEY" "$API/project.all" | jq -r '.[0].projectId')

# 2. Получить environment
ENV_ID=$(curl -s -H "x-api-key: $DOKPLOY_API_KEY" "$API/project.one?projectId=$PROJECT_ID" | jq -r '.environments[0].environmentId')

# 3. Создать приложение
APP_ID=$(curl -s -X POST "${H[@]}" "$API/application.create" \
  -d "{\"name\":\"my-app\",\"environmentId\":\"$ENV_ID\"}" | jq -r '.applicationId')

# 4. Настроить Docker image
curl -s -X POST "${H[@]}" "$API/application.saveDockerProvider" \
  -d "{\"applicationId\":\"$APP_ID\",\"dockerImage\":\"nginx:latest\"}"

# 5. Добавить домен
curl -s -X POST "${H[@]}" "$API/domain.create" \
  -d "{\"host\":\"app.example.com\",\"applicationId\":\"$APP_ID\",\"port\":80,\"https\":true,\"certificateType\":\"letsencrypt\"}"

# 6. Деплой
curl -s -X POST "${H[@]}" "$API/application.deploy" \
  -d "{\"applicationId\":\"$APP_ID\"}"
```

### Workflow 2: Деплой Docker Compose стека

```bash
# 1. Создать compose сервис
COMPOSE_ID=$(curl -s -X POST "${H[@]}" "$API/compose.create" \
  -d "{
    \"name\":\"my-stack\",
    \"environmentId\":\"$ENV_ID\",
    \"composeType\":\"docker-compose\"
  }" | jq -r '.composeId')

# 2. Обновить compose file и env
curl -s -X POST "${H[@]}" "$API/compose.update" \
  -d "{
    \"composeId\":\"$COMPOSE_ID\",
    \"composeFile\":\"version: '3.8'\\nservices:\\n  web:\\n    image: nginx\\n    ports:\\n      - '80:80'\",
    \"sourceType\":\"raw\"
  }"

# 3. Домен для конкретного сервиса
curl -s -X POST "${H[@]}" "$API/domain.create" \
  -d "{\"host\":\"stack.example.com\",\"composeId\":\"$COMPOSE_ID\",\"serviceName\":\"web\",\"port\":80,\"https\":true,\"certificateType\":\"letsencrypt\",\"domainType\":\"compose\"}"

# 4. Deploy
curl -s -X POST "${H[@]}" "$API/compose.deploy" \
  -d "{\"composeId\":\"$COMPOSE_ID\"}"
```

### Workflow 3: Деплой из Git (Custom Git)

```bash
# 1. Создать приложение
APP_ID=$(curl -s -X POST "${H[@]}" "$API/application.create" \
  -d "{\"name\":\"git-app\",\"environmentId\":\"$ENV_ID\"}" | jq -r '.applicationId')

# 2. Настроить git source
curl -s -X POST "${H[@]}" "$API/application.saveGitProvider" \
  -d "{\"applicationId\":\"$APP_ID\",\"customGitUrl\":\"https://github.com/user/repo.git\",\"customGitBranch\":\"main\"}"

# 3. Настроить build type
curl -s -X POST "${H[@]}" "$API/application.saveBuildType" \
  -d "{\"applicationId\":\"$APP_ID\",\"buildType\":\"nixpacks\",\"dockerContextPath\":\".\"}"

# 4. Deploy
curl -s -X POST "${H[@]}" "$API/application.deploy" \
  -d "{\"applicationId\":\"$APP_ID\"}"
```

### Workflow 4: PostgreSQL + приложение

```bash
# 1. Создать PostgreSQL
PG_ID=$(curl -s -X POST "${H[@]}" "$API/postgres.create" \
  -d "{
    \"name\":\"app-db\",
    \"databaseName\":\"appdb\",
    \"databaseUser\":\"app\",
    \"databasePassword\":\"$(openssl rand -hex 16)\",
    \"environmentId\":\"$ENV_ID\"
  }" | jq -r '.postgresId')

# 2. Deploy PostgreSQL
curl -s -X POST "${H[@]}" "$API/postgres.deploy" \
  -d "{\"postgresId\":\"$PG_ID\"}"

# 3. Создать приложение
APP_ID=$(curl -s -X POST "${H[@]}" "$API/application.create" \
  -d "{\"name\":\"app\",\"environmentId\":\"$ENV_ID\"}" | jq -r '.applicationId')

# 4. Прокинуть DATABASE_URL
curl -s -X POST "${H[@]}" "$API/application.saveEnvironment" \
  -d "{\"applicationId\":\"$APP_ID\",\"env\":\"DATABASE_URL=postgres://app:password@app-db:5432/appdb\"}"
```

---

## ⚠️ Gotchas и подводные камни

### 1. sourceType по умолчанию "github"
При создании приложения `sourceType` по умолчанию `"github"`. Если GitHub provider не настроен, деплой упадёт с ошибкой:
```
Github Provider not found
```
**Решение:** Используй `application.saveDockerProvider` для Docker image или `application.saveGitProvider` для custom git URL.

### 2. application.update с sourceType="drop" УДАЛЯЕТ приложение!
Не передавай `sourceType: "drop"` в `application.update` — это может удалить приложение. sourceType для update НЕ используй без крайней необходимости.

### 3. Build type через saveBuildType, не через update
Для смены build type используй `application.saveBuildType`, не `application.update`. Через update может не применяться корректно.

### 4. Environment переменные — это строка, не массив
Формат env: `"KEY1=VALUE1\nKEY2=VALUE2"` — переводы строк `\n` в JSON-строке. НЕ массив объектов.

### 5. /etc/dokploy/applications/ требует root
Файлы приложений на сервере лежат в `/etc/dokploy/applications/<appName>/` — для прямого доступа нужен root.

### 6. Compose sourceType "raw" для inline compose
Если хочешь просто вставить compose file, выставь `sourceType: "raw"` в `compose.update`. Иначе Dokploy будет пытаться клонировать git репозиторий.

### 7. appName — Docker container name
Поле `appName` — это имя Docker контейнера/сервиса. Ограничения: `[a-zA-Z0-9._-]`, max 63 символа. Генерируется автоматически если не указано.

### 8. environmentId обязателен при создании сервисов
При создании application, compose, postgres и т.д. нужно передать `environmentId`, а не `projectId`. Сначала получи environment через `project.one` или `environment.byProjectId`.

### 9. POST-запросы без body
Некоторые POST-запросы не требуют body (например `settings.reloadServer`). Но большинство требуют JSON body. Всегда проверяй.

### 10. Деплой асинхронный
`application.deploy` и `compose.deploy` возвращают ответ сразу, деплой выполняется в фоне. Проверяй статус через `deployment.all`.

### 11. Удаление compose volumes
`compose.delete` требует `deleteVolumes: true/false` — обязательное поле. Если `true`, удалит все Docker volumes стека.

### 12. Domain port — порт ВНУТРИ контейнера
Поле `port` в domain.create — это порт на котором приложение слушает ВНУТРИ контейнера, не external port.

---

## Полная таблица эндпоинтов

| Категория | Эндпоинтов | Основные |
|-----------|-----------|----------|
| project | 6 | create, all, one, update, remove, duplicate |
| environment | 6 | create, one, byProjectId, update, remove, duplicate |
| application | 27 | create, one, deploy, redeploy, start, stop, delete, update, saveBuildType, saveDockerProvider, saveGitProvider, saveEnvironment |
| compose | 26 | create, one, update, deploy, redeploy, stop, start, delete, loadServices, templates |
| domain | 9 | create, byApplicationId, byComposeId, update, delete, generateDomain, validateDomain |
| deployment | 5 | all, allByCompose, allByServer, allByType, killProcess |
| postgres | 13 | create, one, start, stop, deploy, rebuild, remove, update, saveEnvironment, saveExternalPort |
| mysql | 13 | (same pattern) |
| redis | 13 | (same pattern) |
| mongo | 13 | (same pattern) |
| mariadb | 13 | (same pattern) |
| mounts | 5 | create, one, update, remove, allNamedByApplicationId |
| port | 4 | create, one, update, delete |
| security | 4 | create, one, update, delete |
| redirects | 4 | create, one, update, delete |
| docker | 7 | getContainers, restartContainer, getConfig, getContainersByAppNameMatch |
| backup | 11 | create, update, remove, manualBackup*, listBackupFiles |
| destination | 6 | create, testConnection, all, one, update, remove |
| registry | 7 | create, all, one, update, remove, testRegistry |
| notification | 35 | create/update/test для Slack, Telegram, Discord, Email, Gotify, Ntfy, Custom, Lark, Pushover |
| schedule | 6 | create, update, delete, list, one, runManually |
| rollback | 2 | rollback, delete |
| previewDeployment | 4 | all, one, redeploy, delete |
| settings | 49 | version, health, IP, Traefik config, Docker cleanup, update |
| server | 16 | create, all, one, setup, validate, update, remove |
| sshKey | 6 | create, all, one, update, remove, generate |
| user | 18 | all, get, one, update, remove, assignPermissions, createApiKey |
| organization | 9 | create, all, one, update, delete |
| gitProvider | 2 | getAll, remove |
| github/gitlab/gitea/bitbucket | 6-8 каждый | providers, repositories, branches, testConnection |
| certificates | 4 | create, all, one, remove |
| volumeBackups | 6 | list, create, one, update, delete, runManually |
| ai | 9 | create, update, getAll, suggest, deploy |

---

## Хелпер-скрипт

Для удобства можно использовать скрипт `skills/dokploy/scripts/dokploy-api.sh`:

```bash
# Пример: ./scripts/dokploy-api.sh GET project.all
# Пример: ./scripts/dokploy-api.sh POST application.deploy '{"applicationId":"xxx"}'
```
