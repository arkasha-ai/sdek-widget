#!/bin/bash
set -e

BASE="/mnt/c/work/LogeraSpace/logera.space/app-front/src/routes/profile"

# Create directories
mkdir -p "$BASE/voice"
mkdir -p "$BASE/ai-settings"
mkdir -p "$BASE/security"
mkdir -p "$BASE/notifications"
mkdir -p "$BASE/usage"
mkdir -p "$BASE/organization"
mkdir -p "$BASE/billing"

###############################################
# 1. Layout with sidebar
###############################################
cat > "$BASE/+layout.svelte" << 'SVELTE_EOF'
<script lang="ts">
  import { page } from '$app/stores';
  import { goto } from '$app/navigation';
  import { onMount } from 'svelte';
  import { getMeFull } from '@entities/user/api';
  import { currentUser, currentScopes } from '@shared/stores/auth';
  import { getAccessToken } from '@shared/lib/apiClient';
  import type { UserReadWithOrganization } from '@shared/lib/openapi.types';
  import {
    User,
    Mic,
    Bot,
    Shield,
    Bell,
    BarChart3,
    Building2,
    CreditCard,
    ChevronLeft,
    Menu
  } from '@lucide/svelte';

  let { children } = $props();

  let me: UserReadWithOrganization | null = $state(null);
  let loading = $state(true);
  let mobileOpen = $state(false);

  const navItems = [
    { href: '/profile', label: 'Профиль', icon: User },
    { href: '/profile/voice', label: 'Голос', icon: Mic },
    { href: '/profile/ai-settings', label: 'AI настройки', icon: Bot },
    { href: '/profile/security', label: 'Безопасность', icon: Shield },
    { href: '/profile/notifications', label: 'Уведомления', icon: Bell },
    { href: '/profile/usage', label: 'Использование', icon: BarChart3 },
    { href: '/profile/organization', label: 'Организация', icon: Building2 },
    { href: '/profile/billing', label: 'Тарифы', icon: CreditCard },
  ];

  function isActive(href: string, pathname: string): boolean {
    if (href === '/profile') return pathname === '/profile';
    return pathname.startsWith(href);
  }

  onMount(async () => {
    if (!getAccessToken()) {
      goto('/auth/login?from=/profile');
      return;
    }
    try {
      const data = await getMeFull();
      me = data.user;
      currentUser.set(data.user);
      currentScopes.set(data.scopes);
    } catch {
      goto('/auth/login?from=/profile');
    } finally {
      loading = false;
    }
  });
</script>

{#if loading}
  <div class="flex items-center justify-center min-h-[60vh]">
    <div class="animate-spin rounded-full h-8 w-8 border-b-2 border-[var(--primary)]"></div>
  </div>
{:else if me}
  <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6 sm:py-10">
    <!-- Page header -->
    <div class="mb-6 sm:mb-8 flex items-center gap-3">
      <button
        class="sm:hidden p-2 rounded-lg hover:bg-[var(--accent)] transition-colors"
        onclick={() => mobileOpen = !mobileOpen}
      >
        <Menu class="h-5 w-5" />
      </button>
      <div>
        <h1 class="text-2xl sm:text-3xl font-bold tracking-tight">Настройки</h1>
        <p class="text-sm text-[var(--muted-foreground)] mt-1">
          Управляйте аккаунтом и настройками платформы
        </p>
      </div>
    </div>

    <div class="flex gap-6 lg:gap-8">
      <!-- Sidebar navigation -->
      <!-- svelte-ignore a11y_click_events_have_key_events -->
      <!-- svelte-ignore a11y_no_static_element_interactions -->
      <div
        class={[
          'fixed inset-0 z-40 bg-black/50 sm:hidden transition-opacity',
          mobileOpen ? 'opacity-100' : 'opacity-0 pointer-events-none'
        ].join(' ')}
        onclick={() => mobileOpen = false}
      ></div>
      <nav
        class={[
          'fixed top-0 left-0 z-50 h-full w-64 bg-[var(--card)] border-r border-[var(--border)] p-4 transition-transform sm:relative sm:translate-x-0 sm:z-auto sm:h-auto sm:w-56 sm:shrink-0 sm:bg-transparent sm:border-0 sm:p-0',
          mobileOpen ? 'translate-x-0' : '-translate-x-full'
        ].join(' ')}
      >
        <div class="sm:hidden flex items-center justify-between mb-4 pb-4 border-b border-[var(--border)]">
          <span class="font-semibold">Настройки</span>
          <button
            class="p-1 rounded hover:bg-[var(--accent)]"
            onclick={() => mobileOpen = false}
          >
            <ChevronLeft class="h-5 w-5" />
          </button>
        </div>
        <ul class="space-y-1">
          {#each navItems as item}
            {@const active = isActive(item.href, $page.url.pathname)}
            <li>
              <a
                href={item.href}
                onclick={() => mobileOpen = false}
                class={[
                  'flex items-center gap-3 px-3 py-2 rounded-lg text-sm font-medium transition-colors',
                  active
                    ? 'bg-[var(--accent)] text-[var(--accent-foreground)]'
                    : 'text-[var(--muted-foreground)] hover:bg-[var(--accent)]/50 hover:text-[var(--foreground)]'
                ].join(' ')}
              >
                <item.icon class="h-4 w-4 shrink-0" />
                {item.label}
              </a>
            </li>
          {/each}
        </ul>
      </nav>

      <!-- Content area -->
      <main class="flex-1 min-w-0">
        {@render children?.()}
      </main>
    </div>
  </div>
{/if}
SVELTE_EOF

###############################################
# 2. Profile page (main - uses real API)
###############################################
cat > "$BASE/+page.svelte" << 'SVELTE_EOF'
<script lang="ts">
  import { currentUser } from '@shared/stores/auth';
  import { Avatar, AvatarFallback } from '@ui/avatar';
  import { Button } from '@ui/button';
  import { Separator } from '@ui/separator';
  import { Input } from '@ui/input';
  import { Label } from '@ui/label';
  import { Camera } from '@lucide/svelte';

  let user = $derived($currentUser);
  let initials = $derived.by(() => {
    if (!user) return '';
    const f = (user.first_name || '')[0] || '';
    const l = (user.last_name || '')[0] || '';
    return (f + l).toUpperCase() || 'U';
  });

  let firstName = $state('');
  let lastName = $state('');
  let email = $state('');
  let phone = $state('');

  $effect(() => {
    if (user) {
      firstName = user.first_name || '';
      lastName = user.last_name || '';
      email = user.email || '';
      phone = user.phone || '';
    }
  });
</script>

<div class="space-y-6">
  <div>
    <h2 class="text-lg font-semibold">Профиль</h2>
    <p class="text-sm text-[var(--muted-foreground)]">Основная информация вашего аккаунта</p>
  </div>

  <Separator />

  <!-- Avatar section -->
  <div class="flex items-center gap-5">
    <div class="relative group">
      <Avatar class="h-20 w-20 text-xl">
        <AvatarFallback>{initials}</AvatarFallback>
      </Avatar>
      <button
        class="absolute inset-0 flex items-center justify-center rounded-full bg-black/40 opacity-0 group-hover:opacity-100 transition-opacity cursor-pointer"
      >
        <Camera class="h-5 w-5 text-white" />
      </button>
    </div>
    <div>
      <p class="font-medium">{firstName} {lastName}</p>
      <p class="text-sm text-[var(--muted-foreground)]">{email}</p>
    </div>
  </div>

  <Separator />

  <!-- Form -->
  <div class="grid gap-5 max-w-lg">
    <div class="grid grid-cols-2 gap-4">
      <div class="space-y-2">
        <Label for="firstName">Имя</Label>
        <Input id="firstName" bind:value={firstName} placeholder="Имя" />
      </div>
      <div class="space-y-2">
        <Label for="lastName">Фамилия</Label>
        <Input id="lastName" bind:value={lastName} placeholder="Фамилия" />
      </div>
    </div>

    <div class="space-y-2">
      <Label for="email">Email</Label>
      <Input id="email" type="email" bind:value={email} disabled />
      <p class="text-xs text-[var(--muted-foreground)]">Email нельзя изменить</p>
    </div>

    <div class="space-y-2">
      <Label for="phone">Телефон</Label>
      <Input id="phone" type="tel" bind:value={phone} placeholder="+7 (___) ___-__-__" />
    </div>

    <div class="flex gap-3 pt-2">
      <Button>Сохранить</Button>
      <Button variant="outline">Отмена</Button>
    </div>
  </div>
</div>
SVELTE_EOF

###############################################
# 3. Voice page (mock)
###############################################
cat > "$BASE/voice/+page.svelte" << 'SVELTE_EOF'
<script lang="ts">
  import { Separator } from '@ui/separator';
  import { Button } from '@ui/button';
  import { Badge } from '@ui/badge';
  import { Mic, Upload, Play, Trash2 } from '@lucide/svelte';

  let recording = $state(false);
  let samples = $state([
    { id: 1, name: 'Образец 1', duration: '0:12', date: '10 фев 2026' },
    { id: 2, name: 'Образец 2', duration: '0:08', date: '10 фев 2026' },
  ]);
</script>

<div class="space-y-6">
  <div>
    <h2 class="text-lg font-semibold">Голосовой профиль</h2>
    <p class="text-sm text-[var(--muted-foreground)]">
      Загрузите образец голоса для улучшения распознавания и идентификации спикера
    </p>
  </div>

  <Separator />

  <!-- Record / Upload -->
  <div class="grid sm:grid-cols-2 gap-4 max-w-xl">
    <button
      class="flex flex-col items-center gap-3 p-6 rounded-xl border-2 border-dashed border-[var(--border)] hover:border-[var(--primary)] hover:bg-[var(--accent)]/30 transition-colors cursor-pointer"
      onclick={() => recording = !recording}
    >
      <div class={['rounded-full p-3', recording ? 'bg-red-100 text-red-600 animate-pulse' : 'bg-[var(--accent)] text-[var(--primary)]'].join(' ')}>
        <Mic class="h-6 w-6" />
      </div>
      <span class="text-sm font-medium">{recording ? 'Остановить запись' : 'Записать образец'}</span>
      <span class="text-xs text-[var(--muted-foreground)]">Прочитайте текст вслух</span>
    </button>

    <button class="flex flex-col items-center gap-3 p-6 rounded-xl border-2 border-dashed border-[var(--border)] hover:border-[var(--primary)] hover:bg-[var(--accent)]/30 transition-colors cursor-pointer">
      <div class="rounded-full p-3 bg-[var(--accent)] text-[var(--primary)]">
        <Upload class="h-6 w-6" />
      </div>
      <span class="text-sm font-medium">Загрузить файл</span>
      <span class="text-xs text-[var(--muted-foreground)]">WAV, MP3 до 10 МБ</span>
    </button>
  </div>

  <Separator />

  <!-- Existing samples -->
  <div>
    <h3 class="text-sm font-medium mb-3">Ваши образцы</h3>
    <div class="space-y-2">
      {#each samples as sample}
        <div class="flex items-center gap-3 p-3 rounded-lg border border-[var(--border)] bg-[var(--card)]">
          <button class="p-2 rounded-full hover:bg-[var(--accent)] transition-colors">
            <Play class="h-4 w-4" />
          </button>
          <div class="flex-1 min-w-0">
            <p class="text-sm font-medium truncate">{sample.name}</p>
            <p class="text-xs text-[var(--muted-foreground)]">{sample.duration} · {sample.date}</p>
          </div>
          <Badge variant="secondary">Активен</Badge>
          <button class="p-2 rounded-full hover:bg-red-50 hover:text-red-600 transition-colors">
            <Trash2 class="h-4 w-4" />
          </button>
        </div>
      {/each}
    </div>
  </div>
</div>
SVELTE_EOF

###############################################
# 4. AI Settings (mock)
###############################################
cat > "$BASE/ai-settings/+page.svelte" << 'SVELTE_EOF'
<script lang="ts">
  import { Separator } from '@ui/separator';
  import { Button } from '@ui/button';
  import { Label } from '@ui/label';
  import { Switch } from '@ui/switch';
  import { Textarea } from '@ui/textarea';

  let summaryStyle = $state('concise');
  let language = $state('ru');
  let autoProcess = $state(true);
  let speakerDetection = $state(true);
  let customPrompt = $state('');
</script>

<div class="space-y-6">
  <div>
    <h2 class="text-lg font-semibold">AI настройки</h2>
    <p class="text-sm text-[var(--muted-foreground)]">
      Настройте поведение AI при обработке транскрипций
    </p>
  </div>

  <Separator />

  <div class="space-y-6 max-w-lg">
    <!-- Summary style -->
    <div class="space-y-3">
      <Label>Стиль саммари</Label>
      <div class="grid grid-cols-3 gap-2">
        {#each [
          { value: 'concise', label: 'Краткий', desc: 'Ключевые тезисы' },
          { value: 'detailed', label: 'Подробный', desc: 'Полный пересказ' },
          { value: 'bullets', label: 'Список', desc: 'Пункты и действия' },
        ] as opt}
          <button
            class={[
              'p-3 rounded-lg border text-left transition-colors',
              summaryStyle === opt.value
                ? 'border-[var(--primary)] bg-[var(--accent)]'
                : 'border-[var(--border)] hover:border-[var(--primary)]/50'
            ].join(' ')}
            onclick={() => summaryStyle = opt.value}
          >
            <p class="text-sm font-medium">{opt.label}</p>
            <p class="text-xs text-[var(--muted-foreground)]">{opt.desc}</p>
          </button>
        {/each}
      </div>
    </div>

    <!-- Language -->
    <div class="space-y-3">
      <Label>Язык обработки</Label>
      <div class="flex gap-2">
        {#each [
          { value: 'ru', label: '🇷🇺 Русский' },
          { value: 'en', label: '🇬🇧 English' },
          { value: 'auto', label: '🌐 Авто' },
        ] as lang}
          <button
            class={[
              'px-4 py-2 rounded-lg border text-sm transition-colors',
              language === lang.value
                ? 'border-[var(--primary)] bg-[var(--accent)]'
                : 'border-[var(--border)] hover:border-[var(--primary)]/50'
            ].join(' ')}
            onclick={() => language = lang.value}
          >
            {lang.label}
          </button>
        {/each}
      </div>
    </div>

    <Separator />

    <!-- Toggles -->
    <div class="space-y-4">
      <div class="flex items-center justify-between">
        <div>
          <p class="text-sm font-medium">Автообработка</p>
          <p class="text-xs text-[var(--muted-foreground)]">Автоматически создавать саммари после транскрипции</p>
        </div>
        <Switch bind:checked={autoProcess} />
      </div>

      <div class="flex items-center justify-between">
        <div>
          <p class="text-sm font-medium">Детекция спикеров</p>
          <p class="text-xs text-[var(--muted-foreground)]">Определять и разделять голоса участников</p>
        </div>
        <Switch bind:checked={speakerDetection} />
      </div>
    </div>

    <Separator />

    <!-- Custom prompt -->
    <div class="space-y-2">
      <Label for="prompt">Кастомный промпт</Label>
      <Textarea
        id="prompt"
        bind:value={customPrompt}
        placeholder="Дополнительные инструкции для AI..."
        rows={3}
      />
      <p class="text-xs text-[var(--muted-foreground)]">
        Эти инструкции будут добавлены при обработке каждой транскрипции
      </p>
    </div>

    <div class="flex gap-3 pt-2">
      <Button>Сохранить</Button>
      <Button variant="outline">Сбросить</Button>
    </div>
  </div>
</div>
SVELTE_EOF

###############################################
# 5. Security
###############################################
cat > "$BASE/security/+page.svelte" << 'SVELTE_EOF'
<script lang="ts">
  import { Separator } from '@ui/separator';
  import { Button } from '@ui/button';
  import { Input } from '@ui/input';
  import { Label } from '@ui/label';
  import { Badge } from '@ui/badge';
  import { Shield, Smartphone, Monitor, LogOut } from '@lucide/svelte';

  let sessions = [
    { id: 1, device: 'Chrome · Windows', icon: Monitor, ip: '192.168.1.1', date: 'Сейчас', current: true },
    { id: 2, device: 'Safari · iPhone', icon: Smartphone, ip: '10.0.0.5', date: '2 часа назад', current: false },
  ];
</script>

<div class="space-y-6">
  <div>
    <h2 class="text-lg font-semibold">Безопасность</h2>
    <p class="text-sm text-[var(--muted-foreground)]">Пароль, двухфакторная аутентификация и сессии</p>
  </div>

  <Separator />

  <!-- Password -->
  <div class="space-y-4 max-w-lg">
    <h3 class="text-sm font-medium">Изменить пароль</h3>
    <div class="space-y-3">
      <div class="space-y-2">
        <Label for="currentPass">Текущий пароль</Label>
        <Input id="currentPass" type="password" />
      </div>
      <div class="space-y-2">
        <Label for="newPass">Новый пароль</Label>
        <Input id="newPass" type="password" />
      </div>
      <div class="space-y-2">
        <Label for="confirmPass">Подтвердите пароль</Label>
        <Input id="confirmPass" type="password" />
      </div>
      <Button>Обновить пароль</Button>
    </div>
  </div>

  <Separator />

  <!-- 2FA -->
  <div class="flex items-center justify-between max-w-lg">
    <div class="flex items-center gap-3">
      <div class="p-2 rounded-lg bg-[var(--accent)]">
        <Shield class="h-5 w-5 text-[var(--primary)]" />
      </div>
      <div>
        <p class="text-sm font-medium">Двухфакторная аутентификация</p>
        <p class="text-xs text-[var(--muted-foreground)]">Добавьте дополнительный уровень защиты</p>
      </div>
    </div>
    <Button variant="outline" size="sm">Включить</Button>
  </div>

  <Separator />

  <!-- Sessions -->
  <div>
    <div class="flex items-center justify-between mb-3">
      <h3 class="text-sm font-medium">Активные сессии</h3>
      <Button variant="ghost" size="sm" class="text-red-600 hover:text-red-700">
        <LogOut class="h-4 w-4 mr-1" />
        Завершить все
      </Button>
    </div>
    <div class="space-y-2 max-w-lg">
      {#each sessions as session}
        <div class="flex items-center gap-3 p-3 rounded-lg border border-[var(--border)]">
          <session.icon class="h-5 w-5 text-[var(--muted-foreground)]" />
          <div class="flex-1">
            <div class="flex items-center gap-2">
              <span class="text-sm font-medium">{session.device}</span>
              {#if session.current}<Badge variant="secondary">Текущая</Badge>{/if}
            </div>
            <p class="text-xs text-[var(--muted-foreground)]">{session.ip} · {session.date}</p>
          </div>
          {#if !session.current}
            <Button variant="ghost" size="sm">Завершить</Button>
          {/if}
        </div>
      {/each}
    </div>
  </div>
</div>
SVELTE_EOF

###############################################
# 6. Notifications
###############################################
cat > "$BASE/notifications/+page.svelte" << 'SVELTE_EOF'
<script lang="ts">
  import { Separator } from '@ui/separator';
  import { Button } from '@ui/button';
  import { Switch } from '@ui/switch';

  let emailNotifs = $state(true);
  let pushNotifs = $state(false);
  let transcriptionDone = $state(true);
  let summaryReady = $state(true);
  let weeklyDigest = $state(false);
  let storageWarning = $state(true);
</script>

<div class="space-y-6">
  <div>
    <h2 class="text-lg font-semibold">Уведомления</h2>
    <p class="text-sm text-[var(--muted-foreground)]">Настройте как и когда получать уведомления</p>
  </div>

  <Separator />

  <div class="space-y-6 max-w-lg">
    <!-- Channels -->
    <div class="space-y-4">
      <h3 class="text-sm font-medium">Каналы</h3>
      <div class="flex items-center justify-between">
        <div>
          <p class="text-sm">Email уведомления</p>
          <p class="text-xs text-[var(--muted-foreground)]">Получать на почту</p>
        </div>
        <Switch bind:checked={emailNotifs} />
      </div>
      <div class="flex items-center justify-between">
        <div>
          <p class="text-sm">Push уведомления</p>
          <p class="text-xs text-[var(--muted-foreground)]">Уведомления в браузере</p>
        </div>
        <Switch bind:checked={pushNotifs} />
      </div>
    </div>

    <Separator />

    <!-- Events -->
    <div class="space-y-4">
      <h3 class="text-sm font-medium">События</h3>
      {#each [
        { label: 'Транскрипция завершена', desc: 'Когда аудио/видео обработано', get: () => transcriptionDone, set: (v: boolean) => transcriptionDone = v },
        { label: 'Саммари готово', desc: 'Когда AI создал краткое содержание', get: () => summaryReady, set: (v: boolean) => summaryReady = v },
        { label: 'Еженедельный дайджест', desc: 'Сводка за неделю', get: () => weeklyDigest, set: (v: boolean) => weeklyDigest = v },
        { label: 'Предупреждение о хранилище', desc: 'Когда места остаётся < 10%', get: () => storageWarning, set: (v: boolean) => storageWarning = v },
      ] as item}
        <div class="flex items-center justify-between">
          <div>
            <p class="text-sm">{item.label}</p>
            <p class="text-xs text-[var(--muted-foreground)]">{item.desc}</p>
          </div>
          <Switch checked={item.get()} onCheckedChange={item.set} />
        </div>
      {/each}
    </div>

    <div class="pt-2">
      <Button>Сохранить</Button>
    </div>
  </div>
</div>
SVELTE_EOF

###############################################
# 7. Usage
###############################################
cat > "$BASE/usage/+page.svelte" << 'SVELTE_EOF'
<script lang="ts">
  import { Separator } from '@ui/separator';
  import { Progress } from '@ui/progress';
  import { Clock, HardDrive, FileAudio, FileText } from '@lucide/svelte';

  let stats = {
    storage: { used: 2.4, total: 10, unit: 'ГБ' },
    transcriptions: { count: 47, limit: 100 },
    totalMinutes: 312,
    summaries: 38,
  };
</script>

<div class="space-y-6">
  <div>
    <h2 class="text-lg font-semibold">Использование</h2>
    <p class="text-sm text-[var(--muted-foreground)]">Статистика и лимиты вашего аккаунта</p>
  </div>

  <Separator />

  <!-- Stats grid -->
  <div class="grid sm:grid-cols-2 gap-4">
    <div class="p-4 rounded-xl border border-[var(--border)] bg-[var(--card)]">
      <div class="flex items-center gap-2 mb-3">
        <HardDrive class="h-4 w-4 text-[var(--muted-foreground)]" />
        <span class="text-sm font-medium">Хранилище</span>
      </div>
      <div class="text-2xl font-bold">{stats.storage.used} <span class="text-sm font-normal text-[var(--muted-foreground)]">/ {stats.storage.total} {stats.storage.unit}</span></div>
      <Progress value={(stats.storage.used / stats.storage.total) * 100} class="mt-2 h-2" />
    </div>

    <div class="p-4 rounded-xl border border-[var(--border)] bg-[var(--card)]">
      <div class="flex items-center gap-2 mb-3">
        <FileAudio class="h-4 w-4 text-[var(--muted-foreground)]" />
        <span class="text-sm font-medium">Транскрипции</span>
      </div>
      <div class="text-2xl font-bold">{stats.transcriptions.count} <span class="text-sm font-normal text-[var(--muted-foreground)]">/ {stats.transcriptions.limit} в месяц</span></div>
      <Progress value={(stats.transcriptions.count / stats.transcriptions.limit) * 100} class="mt-2 h-2" />
    </div>

    <div class="p-4 rounded-xl border border-[var(--border)] bg-[var(--card)]">
      <div class="flex items-center gap-2 mb-3">
        <Clock class="h-4 w-4 text-[var(--muted-foreground)]" />
        <span class="text-sm font-medium">Обработано минут</span>
      </div>
      <div class="text-2xl font-bold">{stats.totalMinutes}</div>
      <p class="text-xs text-[var(--muted-foreground)] mt-1">За текущий месяц</p>
    </div>

    <div class="p-4 rounded-xl border border-[var(--border)] bg-[var(--card)]">
      <div class="flex items-center gap-2 mb-3">
        <FileText class="h-4 w-4 text-[var(--muted-foreground)]" />
        <span class="text-sm font-medium">Саммари</span>
      </div>
      <div class="text-2xl font-bold">{stats.summaries}</div>
      <p class="text-xs text-[var(--muted-foreground)] mt-1">Создано за месяц</p>
    </div>
  </div>
</div>
SVELTE_EOF

###############################################
# 8. Organization
###############################################
cat > "$BASE/organization/+page.svelte" << 'SVELTE_EOF'
<script lang="ts">
  import { currentUser } from '@shared/stores/auth';
  import { Separator } from '@ui/separator';
  import { Button } from '@ui/button';
  import { Badge } from '@ui/badge';
  import { Building2, Users, Plus } from '@lucide/svelte';

  let user = $derived($currentUser);
  let org = $derived(user?.organization);
</script>

<div class="space-y-6">
  <div>
    <h2 class="text-lg font-semibold">Организация</h2>
    <p class="text-sm text-[var(--muted-foreground)]">Управление организацией и участниками</p>
  </div>

  <Separator />

  {#if org}
    <div class="p-4 rounded-xl border border-[var(--border)] bg-[var(--card)] max-w-lg">
      <div class="flex items-center gap-3 mb-4">
        <div class="p-2 rounded-lg bg-[var(--accent)]">
          <Building2 class="h-5 w-5 text-[var(--primary)]" />
        </div>
        <div>
          <p class="font-medium">{org.name}</p>
          <p class="text-xs text-[var(--muted-foreground)]">ИНН: {org.inn}</p>
        </div>
      </div>

      <div class="flex items-center gap-2">
        <Button variant="outline" size="sm">
          <Users class="h-4 w-4 mr-1" />
          Участники
        </Button>
        <Button variant="outline" size="sm">Настройки</Button>
      </div>
    </div>
  {:else}
    <div class="flex flex-col items-center justify-center py-12 text-center max-w-md mx-auto">
      <div class="p-3 rounded-full bg-[var(--accent)] mb-4">
        <Building2 class="h-8 w-8 text-[var(--muted-foreground)]" />
      </div>
      <h3 class="font-medium mb-1">Нет организации</h3>
      <p class="text-sm text-[var(--muted-foreground)] mb-4">
        Создайте или присоединитесь к организации для совместной работы
      </p>
      <div class="flex gap-2">
        <Button>
          <Plus class="h-4 w-4 mr-1" />
          Создать
        </Button>
        <Button variant="outline">Присоединиться</Button>
      </div>
    </div>
  {/if}
</div>
SVELTE_EOF

###############################################
# 9. Billing (mock)
###############################################
cat > "$BASE/billing/+page.svelte" << 'SVELTE_EOF'
<script lang="ts">
  import { Separator } from '@ui/separator';
  import { Button } from '@ui/button';
  import { Badge } from '@ui/badge';
  import { Check } from '@lucide/svelte';

  let currentPlan = 'free';
  let plans = [
    {
      id: 'free',
      name: 'Free',
      price: '0 ₽',
      period: 'навсегда',
      features: ['5 ГБ хранилище', '20 транскрипций/мес', 'Базовое саммари'],
    },
    {
      id: 'pro',
      name: 'Pro',
      price: '990 ₽',
      period: '/месяц',
      features: ['50 ГБ хранилище', 'Безлимит транскрипций', 'Расширенное AI', 'Голосовой профиль', 'API доступ'],
    },
    {
      id: 'business',
      name: 'Business',
      price: '2 990 ₽',
      period: '/месяц',
      features: ['500 ГБ хранилище', 'Всё из Pro', 'Организация', 'SSO', 'Приоритетная поддержка'],
    },
  ];
</script>

<div class="space-y-6">
  <div>
    <h2 class="text-lg font-semibold">Тарифы и оплата</h2>
    <p class="text-sm text-[var(--muted-foreground)]">Управление подпиской и способами оплаты</p>
  </div>

  <Separator />

  <!-- Plans -->
  <div class="grid sm:grid-cols-3 gap-4">
    {#each plans as plan}
      {@const isCurrent = currentPlan === plan.id}
      <div class={[
        'p-5 rounded-xl border-2 transition-colors',
        isCurrent ? 'border-[var(--primary)] bg-[var(--accent)]/30' : 'border-[var(--border)]'
      ].join(' ')}>
        <div class="flex items-center justify-between mb-3">
          <h3 class="font-semibold">{plan.name}</h3>
          {#if isCurrent}<Badge>Текущий</Badge>{/if}
        </div>
        <div class="mb-4">
          <span class="text-2xl font-bold">{plan.price}</span>
          <span class="text-sm text-[var(--muted-foreground)]">{plan.period}</span>
        </div>
        <ul class="space-y-2 mb-5">
          {#each plan.features as feature}
            <li class="flex items-center gap-2 text-sm">
              <Check class="h-4 w-4 text-green-500 shrink-0" />
              {feature}
            </li>
          {/each}
        </ul>
        {#if isCurrent}
          <Button variant="outline" class="w-full" disabled>Текущий план</Button>
        {:else}
          <Button class="w-full">Выбрать</Button>
        {/if}
      </div>
    {/each}
  </div>
</div>
SVELTE_EOF

echo "✅ All profile pages created successfully!"
ls -la "$BASE"
find "$BASE" -name '*.svelte' | sort
