# Logera Profile Design Review & Fix Task

## Your Role
You are a senior UI/UX designer and Svelte developer. Review the Logera profile section design and fix issues.

## Environment
- Files are inside Docker container `logera-app-front` on node `i9-4090-beast`
- To read files: `nodes run node=i9-4090-beast command=["bash","-c","docker exec logera-app-front cat /path"]`
- To write files: `nodes run node=i9-4090-beast command=["bash","-c","docker exec logera-app-front sh -c 'cat > /path << ENDOFFILE\n...content...\nENDOFFILE'"]`
- To take screenshots: use browser tool with `target=node, node=i9-4090-beast, profile=openclaw`
- Browser targetId: DB8DB4C2CBB4E97867D2E0D87D86EE9E (already open at localhost)
- Tech stack: SvelteKit + Svelte 5 ($state, $derived, $effect, $props, #snippet), shadcn-svelte, Tailwind CSS, Lucide icons

## Brand Design System
```css
--brand-primary: #2481fe;
--background: #f6f9ff;
--card: #ffffff;
--foreground: #0b1220;
--muted-foreground: #3c4a67;
--accent: #e7f2ff;
--border: #d6e4ff;
--radius: 0.575rem;
--font-sans: DM Sans;
```

## Current Profile Pages (all at /app/src/routes/profile/)
1. `+layout.svelte` — sidebar navigation + content area
2. `+page.svelte` — Profile (name, email, phone, avatar)
3. `voice/+page.svelte` — Voice profile (record/upload samples)
4. `ai-settings/+page.svelte` — AI settings (summary style, language, toggles)
5. `security/+page.svelte` — Security (password, 2FA, sessions)
6. `notifications/+page.svelte` — Notification settings
7. `usage/+page.svelte` — Usage statistics
8. `organization/+page.svelte` — Organization management
9. `billing/+page.svelte` — Tariffs/plans

## Current Design Issues (from review)
The profile section was created by a previous sub-agent and has design inconsistencies:

1. **Layout feels flat** — no visual hierarchy, everything looks the same weight
2. **Sidebar navigation** — works but could be more polished (active state, spacing)
3. **Content area** — no container/card wrapping, content floats on background
4. **Inconsistent spacing** — some pages have max-w-lg, others don't
5. **Forms lack polish** — basic inputs without proper grouping
6. **Mobile experience** — sidebar drawer works but could be smoother
7. **No breadcrumbs or page context** — user can feel lost
8. **Avatar section on profile page** — basic, no upload interaction
9. **Billing page** — plan cards could be more attractive
10. **Usage page** — stats cards are plain

## Design Goals
- Make it feel like a **modern SaaS settings page** (think Linear, Vercel, Notion settings)
- Use the brand color system consistently
- Add visual depth with subtle shadows, cards, and spacing
- Group related settings with clear section headers
- Make the sidebar feel premium (better hover states, subtle indicators)
- Ensure consistency across all profile pages
- Keep it clean and minimal — no clutter

## Instructions
1. First, take screenshots of ALL profile pages to see current state
2. Analyze what needs improvement
3. Fix the files one by one, starting with +layout.svelte (sidebar/structure)
4. After each file change, screenshot to verify it looks good
5. Focus on: visual hierarchy, spacing, card usage, typography, hover states
6. Keep ALL existing functionality — only improve the visual design
7. Use only existing shadcn-svelte components (Card, Separator, Badge, Button, etc.)

## Important
- Do NOT break existing functionality
- Do NOT change import paths or API calls
- Use Svelte 5 syntax ($state, $derived, $effect, $props, {#snippet})
- All text should remain in Russian
- Test each page after changes via browser screenshots
