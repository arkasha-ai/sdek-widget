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

<div class="space-y-8">
  <div>
    <h2 class="text-xl font-semibold tracking-tight">AI настройки</h2>
    <p class="text-sm text-[var(--muted-foreground)] mt-1">Настройте поведение AI при обработке транскрипций</p>
  </div>

  <div class="space-y-8 max-w-lg">
    <!-- Summary style -->
    <div>
      <h3 class="text-sm font-semibold text-[var(--muted-foreground)] uppercase tracking-wider mb-3">Стиль саммари</h3>
      <div class="grid grid-cols-3 gap-2.5">
        {#each [{value:'concise',label:'Краткий',desc:'Ключевые тезисы'},{value:'detailed',label:'Подробный',desc:'Полный пересказ'},{value:'bullets',label:'Список',desc:'Пункты и действия'}] as opt}
          <button
            class={[
              'p-3.5 rounded-xl border-2 text-left transition-all duration-150',
              summaryStyle === opt.value
                ? 'border-[var(--primary)] bg-[var(--accent)] shadow-sm shadow-[var(--primary)]/10'
                : 'border-[var(--border)] hover:border-[var(--primary)]/40 hover:bg-[var(--accent)]/30'
            ].join(' ')}
            onclick={() => summaryStyle = opt.value}
          >
            <p class="text-sm font-semibold">{opt.label}</p>
            <p class="text-xs text-[var(--muted-foreground)] mt-0.5">{opt.desc}</p>
          </button>
        {/each}
      </div>
    </div>

    <!-- Language -->
    <div>
      <h3 class="text-sm font-semibold text-[var(--muted-foreground)] uppercase tracking-wider mb-3">Язык обработки</h3>
      <div class="flex gap-2">
        {#each [{value:'ru',label:'🇷🇺 Русский'},{value:'en',label:'🇬🇧 English'},{value:'auto',label:'🌐 Авто'}] as lang}
          <button
            class={[
              'px-4 py-2.5 rounded-xl border-2 text-sm font-medium transition-all duration-150',
              language === lang.value
                ? 'border-[var(--primary)] bg-[var(--accent)] shadow-sm shadow-[var(--primary)]/10'
                : 'border-[var(--border)] hover:border-[var(--primary)]/40'
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
    <div>
      <h3 class="text-sm font-semibold text-[var(--muted-foreground)] uppercase tracking-wider mb-4">Автоматизация</h3>
      <div class="space-y-4">
        <div class="flex items-center justify-between p-3.5 rounded-xl bg-[var(--accent)]/30 border border-[var(--border)]/50">
          <div>
            <p class="text-sm font-medium">Автообработка</p>
            <p class="text-xs text-[var(--muted-foreground)] mt-0.5">Автоматически создавать саммари после транскрипции</p>
          </div>
          <Switch bind:checked={autoProcess} />
        </div>
        <div class="flex items-center justify-between p-3.5 rounded-xl bg-[var(--accent)]/30 border border-[var(--border)]/50">
          <div>
            <p class="text-sm font-medium">Детекция спикеров</p>
            <p class="text-xs text-[var(--muted-foreground)] mt-0.5">Определять и разделять голоса участников</p>
          </div>
          <Switch bind:checked={speakerDetection} />
        </div>
      </div>
    </div>

    <Separator />

    <!-- Custom prompt -->
    <div>
      <h3 class="text-sm font-semibold text-[var(--muted-foreground)] uppercase tracking-wider mb-3">Кастомный промпт</h3>
      <Textarea id="prompt" bind:value={customPrompt} placeholder="Дополнительные инструкции для AI..." rows={3} />
      <p class="text-xs text-[var(--muted-foreground)] mt-2">Эти инструкции будут добавлены при обработке каждой транскрипции</p>
    </div>

    <div class="flex gap-3 pt-2">
      <Button>Сохранить</Button>
      <Button variant="outline">Сбросить</Button>
    </div>
  </div>
</div>
