# shadcn-studio-mcp

## Подключение
```bash
mcporter config add shadcn-studio-mcp --stdio 'npx -y shadcn-studio-mcp' \
  --env 'API_KEY=F3A391ED-2051-489F-94BE-CE8C9D5ED92B' \
  --env 'EMAIL=contact@jakeberrimor.com'
```
Config: `~/.openclaw/workspace/config/mcporter.json`

## Инструменты

| Команда | Когда использовать |
|---|---|
| `get-create-instructions` | Создать новый shadcn блок с нуля (`/create-shadcn`) |
| `get-inspire-instructions` | Взять вдохновение из существующих блоков (`/inspire-shadcn`) |
| `get-refine-instructions` | Доработать/улучшить существующий блок (`/refine-shadcn`) |
| `get-blocks-metadata` | Список доступных блоков |
| `get-inspiration-block-content` | Получить контент конкретного блока |

## Как вызывать
```bash
mcporter call shadcn-studio-mcp.get-inspire-instructions
mcporter call shadcn-studio-mcp.get-blocks-metadata
mcporter call shadcn-studio-mcp.get-inspiration-block-content block=<name>
```

## Когда использовать
- При разработке UI компонентов на shadcn-vue / shadcn (React)
- Когда нужен красивый готовый блок (paywall, карточки, формы)
- При работе с Quasar + shadcn-vue проектами (как у Дениса в LuminesFox/PIM-front-end)
- Стек Дениса: reka-ui + tailwindcss + class-variance-authority + lucide-vue-next

## Credentials
- API_KEY: F3A391ED-2051-489F-94BE-CE8C9D5ED92B
- EMAIL: contact@jakeberrimor.com

_Подключено: 2026-03-02_
