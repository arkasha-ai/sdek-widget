<script lang="ts">
  import { Separator } from '@ui/separator';
  import { Badge } from '@ui/badge';
  import { Mic, Upload, Play, Trash2 } from '@lucide/svelte';

  let recording = $state(false);
  let samples = $state([
    { id: 1, name: 'Образец 1', duration: '0:12', date: '10 фев 2026' },
    { id: 2, name: 'Образец 2', duration: '0:08', date: '10 фев 2026' },
  ]);
</script>

<div class="space-y-8">
  <div>
    <h2 class="text-xl font-semibold tracking-tight">Голосовой профиль</h2>
    <p class="text-sm text-[var(--muted-foreground)] mt-1">Загрузите образец голоса для улучшения распознавания и идентификации спикера</p>
  </div>

  <!-- Upload actions -->
  <div class="grid sm:grid-cols-2 gap-4 max-w-xl">
    <button
      class={[
        'flex flex-col items-center gap-3 p-6 rounded-xl border-2 border-dashed transition-all duration-200 cursor-pointer',
        recording
          ? 'border-red-400 bg-red-50/50 shadow-sm'
          : 'border-[var(--border)] hover:border-[var(--primary)] hover:bg-[var(--accent)]/30 hover:shadow-sm'
      ].join(' ')}
      onclick={() => recording = !recording}
    >
      <div class={['rounded-full p-3.5 transition-colors', recording ? 'bg-red-100 text-red-600 animate-pulse' : 'bg-[var(--accent)] text-[var(--primary)]'].join(' ')}>
        <Mic class="h-6 w-6" />
      </div>
      <span class="text-sm font-semibold">{recording ? 'Остановить запись' : 'Записать образец'}</span>
      <span class="text-xs text-[var(--muted-foreground)]">Прочитайте текст вслух</span>
    </button>
    <button class="flex flex-col items-center gap-3 p-6 rounded-xl border-2 border-dashed border-[var(--border)] hover:border-[var(--primary)] hover:bg-[var(--accent)]/30 hover:shadow-sm transition-all duration-200 cursor-pointer">
      <div class="rounded-full p-3.5 bg-[var(--accent)] text-[var(--primary)]">
        <Upload class="h-6 w-6" />
      </div>
      <span class="text-sm font-semibold">Загрузить файл</span>
      <span class="text-xs text-[var(--muted-foreground)]">WAV, MP3 до 10 МБ</span>
    </button>
  </div>

  <Separator />

  <!-- Samples list -->
  <div>
    <h3 class="text-sm font-semibold text-[var(--muted-foreground)] uppercase tracking-wider mb-4">Ваши образцы</h3>
    <div class="space-y-2.5">
      {#each samples as sample}
        <div class="flex items-center gap-3 p-3.5 rounded-xl border border-[var(--border)] bg-[var(--accent)]/20 hover:bg-[var(--accent)]/40 transition-colors">
          <button class="p-2.5 rounded-full bg-[var(--primary)]/10 hover:bg-[var(--primary)]/20 text-[var(--primary)] transition-colors">
            <Play class="h-4 w-4" />
          </button>
          <div class="flex-1 min-w-0">
            <p class="text-sm font-medium truncate">{sample.name}</p>
            <p class="text-xs text-[var(--muted-foreground)]">{sample.duration} · {sample.date}</p>
          </div>
          <Badge variant="secondary" class="text-xs">Активен</Badge>
          <button class="p-2 rounded-full hover:bg-red-50 hover:text-red-600 transition-colors text-[var(--muted-foreground)]">
            <Trash2 class="h-4 w-4" />
          </button>
        </div>
      {/each}
    </div>
  </div>
</div>
