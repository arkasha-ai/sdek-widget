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
    Menu,
    Settings
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
  <div class="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
    <!-- Page header -->
    <div class="flex items-center gap-3 mb-6">
      <button
        class="sm:hidden p-2 rounded-lg hover:bg-[var(--accent)] transition-colors"
        onclick={() => mobileOpen = true}
      >
        <Menu class="h-5 w-5" />
      </button>
      <div class="flex items-center gap-2.5">
        <div class="p-2 rounded-lg bg-[var(--accent)]">
          <Settings class="h-4.5 w-4.5 text-[var(--primary)]" />
        </div>
        <h1 class="text-xl font-semibold tracking-tight">Настройки</h1>
      </div>
    </div>

    <div class="flex gap-6 lg:gap-8">
      <!-- Mobile overlay -->
      <!-- svelte-ignore a11y_click_events_have_key_events -->
      <!-- svelte-ignore a11y_no_static_element_interactions -->
      <div
        class={[
          'fixed inset-0 z-40 bg-black/40 backdrop-blur-sm sm:hidden transition-opacity duration-200',
          mobileOpen ? 'opacity-100' : 'opacity-0 pointer-events-none'
        ].join(' ')}
        onclick={() => mobileOpen = false}
      ></div>

      <!-- Sidebar navigation -->
      <nav
        class={[
          'fixed top-0 left-0 z-50 h-full w-64 bg-[var(--card)] border-r border-[var(--border)] p-5 transition-transform duration-200 sm:relative sm:translate-x-0 sm:z-auto sm:h-auto sm:w-56 sm:shrink-0 sm:border sm:rounded-xl sm:p-4 sm:shadow-sm sm:self-start sm:sticky sm:top-20',
          mobileOpen ? 'translate-x-0' : '-translate-x-full'
        ].join(' ')}
      >
        <div class="sm:hidden flex items-center justify-between mb-4 pb-4 border-b border-[var(--border)]">
          <span class="font-semibold text-sm">Настройки</span>
          <button
            class="p-1.5 rounded-lg hover:bg-[var(--accent)] transition-colors"
            onclick={() => mobileOpen = false}
          >
            <ChevronLeft class="h-4 w-4" />
          </button>
        </div>
        <ul class="space-y-0.5">
          {#each navItems as item}
            {@const active = isActive(item.href, $page.url.pathname)}
            <li>
              <a
                href={item.href}
                onclick={() => mobileOpen = false}
                class={[
                  'flex items-center gap-2.5 px-3 py-2 rounded-lg text-[13px] font-medium transition-all duration-150',
                  active
                    ? 'bg-[var(--primary)] text-white shadow-sm shadow-[var(--primary)]/25'
                    : 'text-[var(--muted-foreground)] hover:bg-[var(--accent)] hover:text-[var(--foreground)]'
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
      <main class="flex-1 min-w-0 bg-[var(--card)] border border-[var(--border)] rounded-xl shadow-sm p-6 sm:p-8">
        {@render children?.()}
      </main>
    </div>
  </div>
{/if}
