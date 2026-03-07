<script lang="ts">
  import { currentUser } from '@shared/stores/auth';
  import { Separator } from '@ui/separator';
  import { Button } from '@ui/button';
  import { Building2, Users, Plus } from '@lucide/svelte';
  let user = $derived($currentUser);
  let org = $derived(user?.organization);
</script>

<div class="space-y-8">
  <div>
    <h2 class="text-xl font-semibold tracking-tight">Организация</h2>
    <p class="text-sm text-[var(--muted-foreground)] mt-1">Управление организацией и участниками</p>
  </div>

  {#if org}
    <div class="p-5 rounded-xl border border-[var(--border)] bg-[var(--accent)]/30 max-w-lg">
      <div class="flex items-center gap-3.5 mb-4">
        <div class="p-2.5 rounded-xl bg-[var(--primary)]/10">
          <Building2 class="h-5 w-5 text-[var(--primary)]" />
        </div>
        <div>
          <p class="font-semibold">{org.name}</p>
          <p class="text-xs text-[var(--muted-foreground)] mt-0.5">ИНН: {org.inn}</p>
        </div>
      </div>
      <div class="flex items-center gap-2">
        <Button variant="outline" size="sm"><Users class="h-4 w-4 mr-1.5" />Участники</Button>
        <Button variant="outline" size="sm">Настройки</Button>
      </div>
    </div>
  {:else}
    <div class="flex flex-col items-center justify-center py-16 text-center max-w-md mx-auto">
      <div class="p-4 rounded-2xl bg-[var(--accent)] mb-5">
        <Building2 class="h-10 w-10 text-[var(--primary)]/60" />
      </div>
      <h3 class="font-semibold text-lg mb-1.5">Нет организации</h3>
      <p class="text-sm text-[var(--muted-foreground)] mb-6">Создайте или присоединитесь к организации для совместной работы</p>
      <div class="flex gap-3">
        <Button><Plus class="h-4 w-4 mr-1.5" />Создать</Button>
        <Button variant="outline">Присоединиться</Button>
      </div>
    </div>
  {/if}
</div>
