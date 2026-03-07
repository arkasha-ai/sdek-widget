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

<div class="space-y-8">
  <div>
    <h2 class="text-xl font-semibold tracking-tight">Уведомления</h2>
    <p class="text-sm text-[var(--muted-foreground)] mt-1">Настройте как и когда получать уведомления</p>
  </div>

  <div class="space-y-8 max-w-lg">
    <!-- Channels -->
    <div>
      <h3 class="text-sm font-semibold text-[var(--muted-foreground)] uppercase tracking-wider mb-4">Каналы</h3>
      <div class="space-y-3">
        <div class="flex items-center justify-between p-3.5 rounded-xl bg-[var(--accent)]/30 border border-[var(--border)]/50">
          <div><p class="text-sm font-medium">Email уведомления</p><p class="text-xs text-[var(--muted-foreground)] mt-0.5">Получать на почту</p></div>
          <Switch bind:checked={emailNotifs} />
        </div>
        <div class="flex items-center justify-between p-3.5 rounded-xl bg-[var(--accent)]/30 border border-[var(--border)]/50">
          <div><p class="text-sm font-medium">Push уведомления</p><p class="text-xs text-[var(--muted-foreground)] mt-0.5">Уведомления в браузере</p></div>
          <Switch bind:checked={pushNotifs} />
        </div>
      </div>
    </div>

    <Separator />

    <!-- Events -->
    <div>
      <h3 class="text-sm font-semibold text-[var(--muted-foreground)] uppercase tracking-wider mb-4">События</h3>
      <div class="space-y-3">
        <div class="flex items-center justify-between p-3.5 rounded-xl bg-[var(--accent)]/30 border border-[var(--border)]/50">
          <div><p class="text-sm font-medium">Транскрипция завершена</p><p class="text-xs text-[var(--muted-foreground)] mt-0.5">Когда аудио/видео обработано</p></div>
          <Switch bind:checked={transcriptionDone} />
        </div>
        <div class="flex items-center justify-between p-3.5 rounded-xl bg-[var(--accent)]/30 border border-[var(--border)]/50">
          <div><p class="text-sm font-medium">Саммари готово</p><p class="text-xs text-[var(--muted-foreground)] mt-0.5">Когда AI создал краткое содержание</p></div>
          <Switch bind:checked={summaryReady} />
        </div>
        <div class="flex items-center justify-between p-3.5 rounded-xl bg-[var(--accent)]/30 border border-[var(--border)]/50">
          <div><p class="text-sm font-medium">Еженедельный дайджест</p><p class="text-xs text-[var(--muted-foreground)] mt-0.5">Сводка за неделю</p></div>
          <Switch bind:checked={weeklyDigest} />
        </div>
        <div class="flex items-center justify-between p-3.5 rounded-xl bg-[var(--accent)]/30 border border-[var(--border)]/50">
          <div><p class="text-sm font-medium">Предупреждение о хранилище</p><p class="text-xs text-[var(--muted-foreground)] mt-0.5">Когда места остаётся &lt; 10%</p></div>
          <Switch bind:checked={storageWarning} />
        </div>
      </div>
    </div>

    <div class="pt-2"><Button>Сохранить</Button></div>
  </div>
</div>
