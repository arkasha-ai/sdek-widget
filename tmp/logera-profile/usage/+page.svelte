<script lang="ts">
  import { Separator } from '@ui/separator';
  import { Progress } from '@ui/progress';
  import { Clock, HardDrive, FileAudio, FileText } from '@lucide/svelte';
  let stats = { storage: { used: 2.4, total: 10, unit: 'ГБ' }, transcriptions: { count: 47, limit: 100 }, totalMinutes: 312, summaries: 38 };
</script>

<div class="space-y-8">
  <div>
    <h2 class="text-xl font-semibold tracking-tight">Использование</h2>
    <p class="text-sm text-[var(--muted-foreground)] mt-1">Статистика и лимиты вашего аккаунта</p>
  </div>

  <div class="grid sm:grid-cols-2 gap-4">
    <div class="p-5 rounded-xl border border-[var(--border)] bg-gradient-to-br from-blue-50/80 to-[var(--card)] hover:shadow-md transition-shadow">
      <div class="flex items-center gap-2.5 mb-3">
        <div class="p-2 rounded-lg bg-blue-100"><HardDrive class="h-4 w-4 text-blue-600" /></div>
        <span class="text-sm font-semibold">Хранилище</span>
      </div>
      <div class="text-2xl font-bold">{stats.storage.used} <span class="text-sm font-normal text-[var(--muted-foreground)]">/ {stats.storage.total} {stats.storage.unit}</span></div>
      <Progress value={(stats.storage.used / stats.storage.total) * 100} class="mt-3 h-2" />
    </div>

    <div class="p-5 rounded-xl border border-[var(--border)] bg-gradient-to-br from-purple-50/80 to-[var(--card)] hover:shadow-md transition-shadow">
      <div class="flex items-center gap-2.5 mb-3">
        <div class="p-2 rounded-lg bg-purple-100"><FileAudio class="h-4 w-4 text-purple-600" /></div>
        <span class="text-sm font-semibold">Транскрипции</span>
      </div>
      <div class="text-2xl font-bold">{stats.transcriptions.count} <span class="text-sm font-normal text-[var(--muted-foreground)]">/ {stats.transcriptions.limit} в месяц</span></div>
      <Progress value={(stats.transcriptions.count / stats.transcriptions.limit) * 100} class="mt-3 h-2" />
    </div>

    <div class="p-5 rounded-xl border border-[var(--border)] bg-gradient-to-br from-amber-50/80 to-[var(--card)] hover:shadow-md transition-shadow">
      <div class="flex items-center gap-2.5 mb-3">
        <div class="p-2 rounded-lg bg-amber-100"><Clock class="h-4 w-4 text-amber-600" /></div>
        <span class="text-sm font-semibold">Обработано минут</span>
      </div>
      <div class="text-2xl font-bold">{stats.totalMinutes}</div>
      <p class="text-xs text-[var(--muted-foreground)] mt-2">За текущий месяц</p>
    </div>

    <div class="p-5 rounded-xl border border-[var(--border)] bg-gradient-to-br from-emerald-50/80 to-[var(--card)] hover:shadow-md transition-shadow">
      <div class="flex items-center gap-2.5 mb-3">
        <div class="p-2 rounded-lg bg-emerald-100"><FileText class="h-4 w-4 text-emerald-600" /></div>
        <span class="text-sm font-semibold">Саммари</span>
      </div>
      <div class="text-2xl font-bold">{stats.summaries}</div>
      <p class="text-xs text-[var(--muted-foreground)] mt-2">Создано за месяц</p>
    </div>
  </div>
</div>
