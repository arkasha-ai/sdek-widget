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

<div class="space-y-8">
  <div>
    <h2 class="text-xl font-semibold tracking-tight">Безопасность</h2>
    <p class="text-sm text-[var(--muted-foreground)] mt-1">Пароль, двухфакторная аутентификация и сессии</p>
  </div>

  <!-- Password section -->
  <div>
    <h3 class="text-sm font-semibold text-[var(--muted-foreground)] uppercase tracking-wider mb-4">Изменить пароль</h3>
    <div class="space-y-3 max-w-lg">
      <div class="space-y-2"><Label for="currentPass">Текущий пароль</Label><Input id="currentPass" type="password" /></div>
      <div class="space-y-2"><Label for="newPass">Новый пароль</Label><Input id="newPass" type="password" /></div>
      <div class="space-y-2"><Label for="confirmPass">Подтвердите пароль</Label><Input id="confirmPass" type="password" /></div>
      <div class="pt-1"><Button>Обновить пароль</Button></div>
    </div>
  </div>

  <Separator />

  <!-- 2FA section -->
  <div class="flex items-center justify-between max-w-lg p-4 rounded-xl bg-[var(--accent)]/40 border border-[var(--border)]/50">
    <div class="flex items-center gap-3.5">
      <div class="p-2.5 rounded-xl bg-[var(--primary)]/10">
        <Shield class="h-5 w-5 text-[var(--primary)]" />
      </div>
      <div>
        <p class="text-sm font-semibold">Двухфакторная аутентификация</p>
        <p class="text-xs text-[var(--muted-foreground)] mt-0.5">Добавьте дополнительный уровень защиты</p>
      </div>
    </div>
    <Button variant="outline" size="sm">Включить</Button>
  </div>

  <Separator />

  <!-- Sessions -->
  <div>
    <div class="flex items-center justify-between mb-4">
      <h3 class="text-sm font-semibold text-[var(--muted-foreground)] uppercase tracking-wider">Активные сессии</h3>
      <Button variant="ghost" size="sm" class="text-red-600 hover:text-red-700 hover:bg-red-50"><LogOut class="h-4 w-4 mr-1.5" />Завершить все</Button>
    </div>
    <div class="space-y-2.5 max-w-lg">
      {#each sessions as session}
        <div class="flex items-center gap-3.5 p-3.5 rounded-xl border border-[var(--border)] hover:bg-[var(--accent)]/30 transition-colors">
          <div class="p-2 rounded-lg bg-[var(--accent)]">
            <session.icon class="h-4.5 w-4.5 text-[var(--muted-foreground)]" />
          </div>
          <div class="flex-1">
            <div class="flex items-center gap-2">
              <span class="text-sm font-medium">{session.device}</span>
              {#if session.current}<Badge variant="secondary" class="text-xs">Текущая</Badge>{/if}
            </div>
            <p class="text-xs text-[var(--muted-foreground)] mt-0.5">{session.ip} · {session.date}</p>
          </div>
          {#if !session.current}<Button variant="ghost" size="sm">Завершить</Button>{/if}
        </div>
      {/each}
    </div>
  </div>
</div>
