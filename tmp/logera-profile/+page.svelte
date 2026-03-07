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

<div class="space-y-8">
  <div>
    <h2 class="text-xl font-semibold tracking-tight">Профиль</h2>
    <p class="text-sm text-[var(--muted-foreground)] mt-1">Основная информация вашего аккаунта</p>
  </div>

  <!-- Avatar section -->
  <div class="flex items-center gap-5 p-4 rounded-xl bg-[var(--accent)]/40 border border-[var(--border)]/50">
    <div class="relative group">
      <Avatar class="h-20 w-20 text-xl ring-2 ring-white shadow-md">
        <AvatarFallback class="bg-gradient-to-br from-[var(--primary)] to-[var(--primary)]/70 text-white">{initials}</AvatarFallback>
      </Avatar>
      <button class="absolute inset-0 flex items-center justify-center rounded-full bg-black/40 opacity-0 group-hover:opacity-100 transition-opacity cursor-pointer">
        <Camera class="h-5 w-5 text-white" />
      </button>
    </div>
    <div>
      <p class="font-semibold text-lg">{firstName} {lastName}</p>
      <p class="text-sm text-[var(--muted-foreground)]">{email}</p>
    </div>
  </div>

  <Separator />

  <!-- Personal info form -->
  <div>
    <h3 class="text-sm font-semibold text-[var(--muted-foreground)] uppercase tracking-wider mb-4">Личные данные</h3>
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
        <Input id="email" type="email" bind:value={email} disabled class="bg-[var(--accent)]/30" />
        <p class="text-xs text-[var(--muted-foreground)]">Email нельзя изменить</p>
      </div>
      <div class="space-y-2">
        <Label for="phone">Телефон</Label>
        <Input id="phone" type="tel" bind:value={phone} placeholder="+7 (___) ___-__-__" />
      </div>
      <div class="flex gap-3 pt-3">
        <Button>Сохранить</Button>
        <Button variant="outline">Отмена</Button>
      </div>
    </div>
  </div>
</div>
