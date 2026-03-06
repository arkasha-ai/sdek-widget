<script lang="ts">
  import { Separator } from '@ui/separator';
  import { Button } from '@ui/button';
  import { Badge } from '@ui/badge';
  import { Check, Star } from '@lucide/svelte';
  let currentPlan = 'free';
  let plans = [
    { id: 'free', name: 'Free', price: '0 ₽', period: 'навсегда', recommended: false, features: ['5 ГБ хранилище', '20 транскрипций/мес', 'Базовое саммари'] },
    { id: 'pro', name: 'Pro', price: '990 ₽', period: '/месяц', recommended: true, features: ['50 ГБ хранилище', 'Безлимит транскрипций', 'Расширенное AI', 'Голосовой профиль', 'API доступ'] },
    { id: 'business', name: 'Business', price: '2 990 ₽', period: '/месяц', recommended: false, features: ['500 ГБ хранилище', 'Всё из Pro', 'Организация', 'SSO', 'Приоритетная поддержка'] },
  ];
</script>

<div class="space-y-8">
  <div>
    <h2 class="text-xl font-semibold tracking-tight">Тарифы и оплата</h2>
    <p class="text-sm text-[var(--muted-foreground)] mt-1">Управление подпиской и способами оплаты</p>
  </div>

  <div class="grid sm:grid-cols-3 gap-4">
    {#each plans as plan}
      {@const isCurrent = currentPlan === plan.id}
      <div
        class={[
          'relative p-5 rounded-xl border-2 transition-all duration-200 hover:shadow-md',
          plan.recommended && !isCurrent
            ? 'border-[var(--primary)] bg-gradient-to-b from-[var(--accent)]/60 to-[var(--card)] shadow-sm shadow-[var(--primary)]/10'
            : isCurrent
              ? 'border-[var(--primary)] bg-[var(--accent)]/30'
              : 'border-[var(--border)] hover:border-[var(--primary)]/40'
        ].join(' ')}
      >
        {#if plan.recommended && !isCurrent}
          <div class="absolute -top-3 left-1/2 -translate-x-1/2">
            <Badge class="bg-[var(--primary)] text-white text-xs px-2.5 py-0.5 shadow-sm">
              <Star class="h-3 w-3 mr-1" />Популярный
            </Badge>
          </div>
        {/if}
        <div class="flex items-center justify-between mb-4">
          <h3 class="font-bold text-base">{plan.name}</h3>
          {#if isCurrent}<Badge variant="secondary" class="text-xs">Текущий</Badge>{/if}
        </div>
        <div class="mb-5">
          <span class="text-3xl font-bold">{plan.price}</span>
          <span class="text-sm text-[var(--muted-foreground)]">{plan.period}</span>
        </div>
        <ul class="space-y-2.5 mb-6">
          {#each plan.features as feature}
            <li class="flex items-center gap-2.5 text-sm">
              <div class="flex-shrink-0 h-4.5 w-4.5 rounded-full bg-emerald-100 flex items-center justify-center">
                <Check class="h-3 w-3 text-emerald-600" />
              </div>
              {feature}
            </li>
          {/each}
        </ul>
        {#if isCurrent}
          <Button variant="outline" class="w-full" disabled>Текущий план</Button>
        {:else if plan.recommended}
          <Button class="w-full shadow-sm">Выбрать</Button>
        {:else}
          <Button variant="outline" class="w-full">Выбрать</Button>
        {/if}
      </div>
    {/each}
  </div>
</div>
