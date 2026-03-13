#!/usr/bin/env node
/**
 * mindgraph_ingest.js — Наполнение MindGraph данными из memory/
 * 
 * Ingests:
 * - People profiles (memory/people/*.md)
 * - Project summaries (memory/projects/*.md)
 * - Core knowledge from MEMORY.md
 * - Recent daily logs
 * 
 * Run: MINDGRAPH_TOKEN=xxx node scripts/mindgraph_ingest.js
 */

const fs = require('fs');
const path = require('path');

const BASE_URL = 'http://127.0.0.1:18790';
const TOKEN = process.env.MINDGRAPH_TOKEN || fs.readFileSync(
  path.join(process.env.HOME, '.openclaw', 'secrets.env'), 'utf8'
).match(/MINDGRAPH_TOKEN=(.+)/)?.[1]?.trim() || '';
const AGENT_ID = 'arkasha';
const WORKSPACE = path.join(process.env.HOME, '.openclaw', 'workspace');

async function api(method, endpoint, body) {
  const res = await fetch(`${BASE_URL}${endpoint}`, {
    method,
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${TOKEN}`,
    },
    body: body ? JSON.stringify(body) : undefined,
  });
  const text = await res.text();
  if (!res.ok) throw new Error(`${method} ${endpoint} → ${res.status}: ${text}`);
  return text ? JSON.parse(text) : null;
}

async function findOrCreateEntity(label, entityType, description = '') {
  try {
    const result = await api('POST', '/reality/entity', {
      action: 'create',
      agent_id: AGENT_ID,
      label,
      props: { entity_type: entityType, description },
    });
    // API returns the node directly with a `created` field mixed in
    const node = result.uid ? result : (result.node || null);
    const status = result.created ? '✨ Created' : '🔄 Exists';
    console.log(`  ${status}: [${entityType}] ${label} (uid=${node?.uid?.slice(0,8)})`);
    return node;
  } catch (e) {
    console.error(`  ❌ Entity error for "${label}": ${e.message}`);
    return null;
  }
}

async function evolveNode(uid, propsPatch, summary = '') {
  try {
    const body = { action: 'update', uid, agent_id: AGENT_ID, props_patch: propsPatch };
    if (summary) body.summary = summary;
    await api('POST', '/evolve', body);
    console.log(`  📝 Updated uid=${uid.slice(0,8)}...`);
  } catch (e) {
    console.error(`  ❌ Evolve error: ${e.message}`);
  }
}

async function relateEntities(sourceUid, targetUid, edgeType) {
  try {
    await api('POST', '/reality/entity', {
      action: 'relate',
      agent_id: AGENT_ID,
      source_uid: sourceUid,
      target_uid: targetUid,
      edge_type: edgeType,
    });
    console.log(`  🔗 Related: ${sourceUid.slice(0,8)} --[${edgeType}]--> ${targetUid.slice(0,8)}`);
  } catch (e) {
    // Ignore duplicate edge errors
    if (!e.message.includes('already exists') && !e.message.includes('duplicate')) {
      console.error(`  ❌ Relate error: ${e.message}`);
    }
  }
}

async function ingestObservation(label, content) {
  try {
    await api('POST', '/reality/ingest', {
      action: 'observation',
      agent_id: AGENT_ID,
      label,
      content,
    });
    console.log(`  📥 Ingested: "${label}"`);
  } catch (e) {
    console.error(`  ❌ Ingest error for "${label}": ${e.message}`);
  }
}

async function ingestSnippet(label, content, sourceUid) {
  try {
    const body = {
      action: 'snippet',
      agent_id: AGENT_ID,
      label,
      content,
    };
    if (sourceUid) body.source_uid = sourceUid;
    await api('POST', '/reality/ingest', body);
    console.log(`  📄 Snippet: "${label}"`);
  } catch (e) {
    console.error(`  ❌ Snippet error: ${e.message}`);
  }
}

async function textSearch(query) {
  try {
    const result = await api('POST', '/retrieve', { action: 'text', query, limit: 1 });
    return result?.items?.[0]?.node || null;
  } catch { return null; }
}

// ─── Ingest People ────────────────────────────────────────────────────────────

async function ingestPeople() {
  console.log('\n👥 Ingesting people...');

  const people = [
    {
      label: 'Денис Парменев',
      type: 'Person',
      description: 'Владелец и хозяин Аркаши. Тимлид/Проектный руководитель LLM проектов в Gravity Group. Живёт в Пензе. После операции по удалению щитовидной железы принимает ежедневные гормоны в 09:00. Интересуется LLM и агентами. Разрабатывает pet-проект — корпоративная база знаний Logera.',
      summary: 'Тимлид LLM проектов в Gravity Group, Пенза. Ежедневные лекарства в 09:00 критически важны.',
      identifiers: { telegram_id: '364935958', location: 'Пенза', timezone: 'Europe/Moscow' },
      observations: [
        'Здоровье: удалена щитовидная железа (рак, 2024). Принимает гормоны ежедневно в 09:00 — нельзя пропускать под угрозой рецидива.',
        'Работает в Gravity Group тимлидом LLM проектов. Также самостоятельный разработчик.',
        'Pet-проект: Logera — корпоративная база знаний с LLM-контекстом (SvelteKit + FastAPI).',
        'Telegram ID: 364935958. Основной канал общения с Аркашей.',
      ]
    },
    {
      label: 'Тимофей Шутов',
      type: 'Person',
      description: 'Финансовый директор Gravity Group. Муж Ксении Шутовой. Коллега Дениса. 18.02.2026 прислал ТЗ на ГИС-платформу КОМПАС (РТК) для оценки трудозатрат.',
      summary: 'Финансовый директор Gravity Group, коллега Дениса.',
      identifiers: { telegram_group: '-5112704488 (Оценки Аркаша)' },
    },
    {
      label: 'Ксения Шутова',
      type: 'Person',
      description: 'Руководитель детского центра Остров Аркаша. Логопед. Жена Тимофея Шутова. Telegram @shutovakv (ID: 458267070). Регулярно заказывает контент для соцсетей про занятия в детском центре.',
      summary: 'Руководитель детского центра Остров Аркаша, логопед. Заказывает контент для соцсетей.',
      identifiers: { telegram: '@shutovakv', telegram_id: '458267070', phone: '8 919 714 81 31' },
    },
    {
      label: 'Дмитрий Байдин',
      type: 'Person',
      description: 'CEO Energotrend.Com (Industrial Automation & Smart Home). Telegram @bdd1974. День рождения 6 марта 1974. Старый знакомый Дениса. Куратор/посредник в проекте SyncVoice — связывает Дениса с Константином из Estetic Sound и заказчиком.',
      summary: 'CEO Energotrend.Com. Посредник в SyncVoice: Денис → Дмитрий → Константин → заказчик.',
      identifiers: { telegram: '@bdd1974', phone: '+7 905 787 8773', birthday: '1974-03-06' },
    },
    {
      label: 'Александр Воробьев',
      type: 'Person',
      description: 'Юрист, работает в Gravity. Telegram ID: 942014320. Активно тестирует возможности Аркадия — присылает документы для анализа, переводов (Excel, DOCX). Знакомый Дениса из Gravity.',
      summary: 'Юрист в Gravity. Активный пользователь Аркадия, тестирует его на документах.',
      identifiers: { telegram_id: '942014320' },
    },
  ];

  const entityMap = {};
  for (const person of people) {
    const node = await findOrCreateEntity(person.label, person.type, person.description);
    if (node) {
      entityMap[person.label] = node.uid;
      // Update with rich data
      await evolveNode(node.uid, {
        description: person.description,
        identifiers: person.identifiers || {},
      }, person.summary);

      // Ingest detailed observations
      if (person.observations) {
        for (const obs of person.observations) {
          await ingestObservation(`[${person.label}] ${obs.slice(0, 60)}...`, obs);
        }
      }
      await sleep(100);
    }
  }
  return entityMap;
}

// ─── Ingest Organizations ─────────────────────────────────────────────────────

async function ingestOrganizations() {
  console.log('\n🏢 Ingesting organizations...');

  const orgs = [
    {
      label: 'Gravity',
      type: 'Organization',
      description: 'IT-компания Gravity Group (Gravity). Денис работает тимлидом LLM проектов. Коллеги: Тимофей Шутов (финдиректор), Александр Воробьев (юрист). Telegram: Gravity LLM (-1003676744192). Использует self-hosted GitLab + Redmine.',
      summary: 'IT-компания, где работает Денис тимлидом LLM проектов.',
    },
    {
      label: 'Energotrend.Com',
      type: 'Organization',
      description: 'Компания Дмитрия Байдина (CEO). Industrial Automation & Smart Home.',
      summary: 'Компания Дмитрия Байдина — Industrial Automation & Smart Home.',
    },
    {
      label: 'Остров Аркаша',
      type: 'Organization',
      description: 'Детский центр в Пензе. Руководитель: Ксения Шутова. Логопед, подготовка к школе, детские мероприятия. Telegram группа: -5056580782. Телефон: 8 919 714 81 31.',
      summary: 'Детский центр, руководит Ксения Шутова. Логопед, подготовка к школе.',
    },
    {
      label: 'Estetic Sound',
      type: 'Organization',
      description: 'Компания партнёра по проекту SyncVoice. Контактное лицо: Константин. Дмитрий Байдин является посредником между Денисом и Константином из Estetic Sound.',
      summary: 'Партнёр по проекту SyncVoice. Представитель: Константин.',
    },
  ];

  const entityMap = {};
  for (const org of orgs) {
    const node = await findOrCreateEntity(org.label, org.type, org.description);
    if (node) {
      entityMap[org.label] = node.uid;
      await evolveNode(node.uid, { description: org.description }, org.summary);
      await sleep(100);
    }
  }
  return entityMap;
}

// ─── Ingest Projects ──────────────────────────────────────────────────────────

async function ingestProjects() {
  console.log('\n📦 Ingesting projects...');

  const projects = [
    {
      label: 'Logera',
      type: 'Project',
      description: 'Pet-проект Дениса — корпоративная база знаний с LLM-контекстом. "Найдите ответ с цитатами из ваших страниц, файлов и звонков". Репозиторий: topitip/logera.space (приватный, GitHub). Стек: SvelteKit 5 + FastAPI + LangGraph + Qdrant + OpenSearch. 7 AMQP воркеров для медиа-пайплайна (транскрибация, диаризация, индексация). Multi-tenancy (org/personal spaces).',
      summary: 'Корпоративная база знаний Дениса с LLM-поиском. SvelteKit + FastAPI + LangGraph.',
    },
    {
      label: 'SyncVoice',
      type: 'Project',
      description: 'Система автоматического синхронного перевода (SyncVoice™ Platform). On-premise решение для корпоративного клиента с высокой специфической терминологией. Языки: RU ↔ EN ↔ HI ↔ ZH. Схема: микрофон → STT → перевод → TTS → вывод. Конфиденциальность критична. Облако исключено. Оценка: 994ч / 2.6M₽ / 20–26 нед. Посредник: Дмитрий Байдин → Константин (Estetic Sound).',
      summary: 'On-premise синхронный переводчик. RU/EN/HI/ZH. 994ч / 2.6M₽. Через Дмитрия Байдина.',
    },
    {
      label: 'archdoc',
      type: 'Project',
      description: 'Инструмент для автоматической генерации архитектурной документации. Проект Gravity.',
      summary: 'Авто-генерация архитектурной документации. Проект Gravity.',
    },
    {
      label: 'Hide and Seek',
      type: 'Project',
      description: 'Проект Hide and Seek. Детали в memory/projects/hide-and-seek.md.',
      summary: 'Проект Hide and Seek.',
    },
    {
      label: 'Portfolio Site',
      type: 'Project',
      description: 'Сайт-портфолио. Детали в memory/projects/portfolio-site.md.',
      summary: 'Персональный сайт-портфолио.',
    },
  ];

  const entityMap = {};
  for (const proj of projects) {
    const node = await findOrCreateEntity(proj.label, proj.type, proj.description);
    if (node) {
      entityMap[proj.label] = node.uid;
      await evolveNode(node.uid, { description: proj.description }, proj.summary);
      await sleep(100);
    }
  }
  return entityMap;
}

// ─── Ingest Infrastructure ────────────────────────────────────────────────────

async function ingestInfrastructure() {
  console.log('\n🖥️ Ingesting infrastructure...');

  const infra = [
    {
      label: 'clwd.jakeberrimor.com',
      type: 'System',
      description: 'Основной сервер Аркаши. Хостит: OpenClaw Gateway, MindGraph (порт 18790), IMAP IDLE listener, Qdrant, и все воркеры. OS: Linux x64. Постоянный uptime.',
      summary: 'Основной сервер Аркаши с OpenClaw Gateway и всеми сервисами.',
    },
    {
      label: 'i9-4090-beast',
      type: 'System',
      description: 'Мощный сервер с GPU (RTX 4090) для тяжёлых задач: транскрибация Whisper, диаризация pyannote, inference моделей. Для сложных задач через OpenClaw nodes.',
      summary: 'GPU-сервер с RTX 4090 для ML-задач.',
    },
  ];

  const entityMap = {};
  for (const item of infra) {
    const node = await findOrCreateEntity(item.label, item.type, item.description);
    if (node) {
      entityMap[item.label] = node.uid;
      await evolveNode(node.uid, { description: item.description }, item.summary);
      await sleep(100);
    }
  }
  return entityMap;
}

// ─── Ingest Core Knowledge ────────────────────────────────────────────────────

async function ingestCoreKnowledge() {
  console.log('\n🧠 Ingesting core knowledge...');

  const knowledge = [
    {
      label: 'Аркаша — ежедневные лекарства Дениса (09:00)',
      content: `Денис принимает ежедневные гормоны щитовидной железы в 09:00 строго натощак.
НЕЛЬЗЯ пропускать: последствия — туплю, сплю, вплоть до комы; риск рецидива рака.
Напоминания: 09:00 (основное), 09:20 (повтор), 09:45 (критичное) через system crontab.
Триггер: если Денис пишет "выпил"/"принял"/"выпил лекарство" → записать в medicine-today.json.`,
    },
    {
      label: 'Gravity LLM — рабочий контекст',
      content: `Gravity Group — IT-компания где Денис работает тимлидом LLM проектов.
Email для работы: a.parmeev@jakeberrimor.com
Инфраструктура: self-hosted GitLab + Redmine.
Telegram: Gravity LLM (-1003676744192) — общая тема, руководство наблюдает.
В рабочих чатах: максимально профессионально, никакой личной информации.`,
    },
    {
      label: 'Аркаша — правило: никогда не врать',
      content: `Критическое правило: НИКОГДА не врать.
Урок 2026-02-09: Сказал "тестирую" — а по факту нет. Денис поймал по логам.
Урок 2026-02-21: Дважды соврал про Personal Analytics.
Если не сделал — сказать что не сделал. Доверие — это всё. Вранье разрушает его навсегда.`,
    },
    {
      label: 'Аркаша — GitHub аккаунт',
      content: `GitHub аккаунт: arkasha-ai
Разблокирован 25.02.2026 (тикет GitHub Support 4087174).
SSH key: ~/.ssh/github_arkasha
НЕ использовать личный аккаунт Дениса (topitip) для автоматизации.`,
    },
    {
      label: 'Аркаша — MindGraph настройка',
      content: `MindGraph сервер: http://127.0.0.1:18790 (автостарт @reboot)
Токен: MINDGRAPH_TOKEN из ~/.openclaw/secrets.env
Клиент: skills/mindgraph-rs/mindgraph-client.js
Инструкция AGENTS.md: "Вопрос про человека/проект/решение → POST /retrieve"
Старый граф KuzuDB: archive/knowledge-graph-kuzu/ (не используется)`,
    },
    {
      label: 'TickTick — проекты Дениса',
      content: `TickTick проекты:
- Личный: 695bc6dd7d799105bb21e874
- Работа: 695bc7447dd51105bb21e8ee
- Фитнес: 695bfa4ba268d125f73668e9
- Back-end: 695bfb43ab63d125f7366aa6
- 🤖 Аркаша Tasks: 6998c6fb1ff4510b9e851f9f`,
    },
  ];

  for (const item of knowledge) {
    await ingestObservation(item.label, item.content);
    await sleep(150);
  }
}

// ─── Add Relationships ────────────────────────────────────────────────────────

async function addRelationships(people, orgs, projects) {
  console.log('\n🔗 Adding relationships...');

  // Denis → Gravity (WorksAt)
  const denisUid = people['Денис Парменев'];
  const gravityUid = orgs['Gravity'];
  if (denisUid && gravityUid) {
    await relateEntities(denisUid, gravityUid, 'WorksAt');
  }

  // Denis → Logera (Owns)
  const logeraUid = projects['Logera'];
  if (denisUid && logeraUid) {
    await relateEntities(denisUid, logeraUid, 'Owns');
    await relateEntities(denisUid, logeraUid, 'WorksOn');
  }

  // Denis → SyncVoice (WorksOn)
  const syncvoiceUid = projects['SyncVoice'];
  if (denisUid && syncvoiceUid) {
    await relateEntities(denisUid, syncvoiceUid, 'WorksOn');
  }

  // Timofey → Gravity (WorksAt)
  const timofeyUid = people['Тимофей Шутов'];
  if (timofeyUid && gravityUid) {
    await relateEntities(timofeyUid, gravityUid, 'WorksAt');
  }

  // Alexander Vorobyev → Gravity (WorksAt)
  const alexUid = people['Александр Воробьев'];
  if (alexUid && gravityUid) {
    await relateEntities(alexUid, gravityUid, 'WorksAt');
  }

  // Ksenia Shutova → Ostrov Arkasha (Runs)
  const kseniaUid = people['Ксения Шутова'];
  const ostrovUid = orgs['Остров Аркаша'];
  if (kseniaUid && ostrovUid) {
    await relateEntities(kseniaUid, ostrovUid, 'Runs');
  }

  // Timofey ↔ Ksenia (MarriedTo)
  if (timofeyUid && kseniaUid) {
    await relateEntities(timofeyUid, kseniaUid, 'MarriedTo');
  }

  // Dmitry Baydin → Energotrend (WorksAt CEO)
  const dmitryUid = people['Дмитрий Байдин'];
  const energoUid = orgs['Energotrend.Com'];
  if (dmitryUid && energoUid) {
    await relateEntities(dmitryUid, energoUid, 'WorksAt');
  }

  // Dmitry → SyncVoice (IsPartOf/Mediates)
  if (dmitryUid && syncvoiceUid) {
    await relateEntities(dmitryUid, syncvoiceUid, 'ParticipatesIn');
  }

  // Estetic Sound → SyncVoice
  const esteticUid = orgs['Estetic Sound'];
  if (esteticUid && syncvoiceUid) {
    await relateEntities(esteticUid, syncvoiceUid, 'ParticipatesIn');
  }

  console.log('  ✅ Relationships done');
}

// ─── Ingest Recent Daily Logs ─────────────────────────────────────────────────

async function ingestRecentDailyLogs() {
  console.log('\n📅 Ingesting recent daily logs...');

  const memDir = path.join(WORKSPACE, 'memory');
  const files = fs.readdirSync(memDir)
    .filter(f => /^\d{4}-\d{2}-\d{2}\.md$/.test(f))
    .sort()
    .slice(-7); // Last 7 days

  for (const file of files) {
    const date = file.replace('.md', '');
    const content = fs.readFileSync(path.join(memDir, file), 'utf8');
    
    // Take first 2000 chars to avoid huge ingestion
    const snippet = content.slice(0, 2000);
    if (snippet.trim().length < 50) continue;
    
    await ingestObservation(`Дневник ${date}`, snippet);
    await sleep(200);
  }
}

// ─── Utility ──────────────────────────────────────────────────────────────────

function sleep(ms) {
  return new Promise(r => setTimeout(r, ms));
}

// ─── Main ─────────────────────────────────────────────────────────────────────

async function main() {
  console.log('🚀 MindGraph Ingest Script');
  console.log(`📡 Server: ${BASE_URL}`);
  console.log(`🔑 Token: ${TOKEN ? TOKEN.slice(0,8) + '...' : '(missing!)'}`);
  
  if (!TOKEN) {
    console.error('❌ MINDGRAPH_TOKEN not found!');
    process.exit(1);
  }

  // Health check
  const health = await fetch(`${BASE_URL}/health`).then(r => r.text());
  console.log(`💚 Health: ${health}`);

  // Open session
  let sessionUid;
  try {
    const session = await api('POST', '/memory/session', {
      action: 'open',
      agent_id: AGENT_ID,
      label: `Ingest session ${new Date().toISOString().slice(0, 10)}`,
    });
    sessionUid = session?.uid;
    console.log(`📖 Session: ${sessionUid?.slice(0, 8)}...`);
  } catch (e) {
    console.warn('  ⚠️ Could not open session:', e.message);
  }

  // Run ingestion phases
  const people = await ingestPeople();
  const orgs = await ingestOrganizations();
  const projects = await ingestProjects();
  await ingestInfrastructure();
  await ingestCoreKnowledge();
  await addRelationships(people, orgs, projects);
  await ingestRecentDailyLogs();

  // Close session
  if (sessionUid) {
    try {
      await api('POST', '/memory/session', {
        action: 'close',
        agent_id: AGENT_ID,
        session_uid: sessionUid,
        summary: 'Batch ingest of workspace memory: people, projects, orgs, infrastructure, knowledge, daily logs',
      });
      console.log('\n📕 Session closed');
    } catch (e) {
      console.warn('⚠️ Could not close session:', e.message);
    }
  }

  console.log('\n✅ Ingest complete!');
}

main().catch(e => {
  console.error('💥 Fatal error:', e);
  process.exit(1);
});
