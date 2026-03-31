# Safari Performance Patterns

Hard-won optimizations from the Upgrade page wheel animations. These patterns fix real Safari rendering bugs — apply them whenever you animate elements with complex compositing.

---

## 1. Never use `opacity: 0` — use `opacity: 0.01`

Safari deallocates the GPU backing store when an element reaches exactly `opacity: 0`. When the element needs to become visible again, Safari must:

1. Re-allocate the backing store
2. Re-rasterize the element (including all SVG filters, blur effects, etc.)
3. Only then start the opacity transition

This causes a 1-3 frame white flash visible to the naked eye.

```css
/* Bad — Safari drops the GPU layer */
.hidden { opacity: 0; }

/* Good — invisible to the eye, backing store preserved */
.hidden { opacity: 0.01; }
```

Same applies to `visibility: hidden` — it may also trigger backing store deallocation. Prefer `opacity: 0.01` + `pointer-events-none` over `invisible`.

---

## 2. Don't animate `transform` in `@keyframes` — animate `opacity` only

When a `@keyframes` animation includes `transform`, Safari may promote/demote the element to a GPU compositing layer mid-animation. This "layer thrashing" causes frame drops.

If the element already has `translate-z-0` via Tailwind classes, adding `transform` inside keyframes creates two competing sources of truth — Safari resolves this by re-compositing every frame.

```css
/* Bad — transform in keyframes conflicts with Tailwind translate-z-0 */
@keyframes fade-in {
  from { opacity: 0; transform: translateY(14px) translateZ(0); }
  to { opacity: 1; transform: translateY(0) translateZ(0); }
}

/* Good — opacity only, element already has translate-z-0 from classes */
@keyframes fade-in {
  from { opacity: 0.01; }
  to { opacity: 1; }
}
```

If you need `translateY` entrance, apply it via CSS `transition` on a class toggle instead of `@keyframes`.

---

## 3. Don't transition `color` on SVGs with `feGaussianBlur`

SVGs using `fill="currentColor"` with blur filters re-rasterize **every frame** when the CSS `color` property transitions. Each frame recalculates all blur operations.

```tsx
/* Bad — color transition forces SVG re-rasterization per frame */
<div className="transition-[opacity,color] text-purple → text-red">
  <GlowSvgWithBlurFilters />
</div>

/* Good — two SVGs, opacity-only crossfade, each rasterized once */
<div className={cn('transition-opacity', showPurple ? 'opacity-100' : 'opacity-[0.01]')}>
  <GlowSvg className="text-purple" />
</div>
<div className={cn('transition-opacity', showRed ? 'opacity-100' : 'opacity-[0.01]')}>
  <GlowSvg className="text-red" />
</div>
```

---

## 4. Don't use JS `setTimeout` for animation sequencing

`setTimeout` fires on the main thread. During heavy compositing (which we measured at 275-439ms in Safari), the JS event loop is blocked — timers fire late, causing visible gaps.

```tsx
/* Bad — timer fires after compositing finishes, not when you expect */
setTimeout(() => setRevealed(true), 100);  // Actually fires after 300-500ms

/* Good — pure CSS crossfade, compositor handles timing */
// Fast element: transition-opacity duration-100
// Slow element: transition-opacity duration-250
// Both start simultaneously, fast one finishes first = visual sequence
```

---

## 5. Force GPU layer with `translate-z-0 backface-hidden`

Safari doesn't auto-promote elements to GPU compositing layers during transitions (Chrome does). Without explicit promotion, opacity transitions run on the main thread.

```tsx
/* Always add to elements that transition opacity or transform */
className="translate-z-0 backface-hidden transition-opacity ..."
```

For text elements, also add `antialiased` to prevent font weight shift during animation:

```tsx
className="translate-z-0 backface-hidden antialiased animate-[...]"
```

---

## 6. Clean Figma SVG exports

Figma adds noop filter operations to every SVG:

```xml
<!-- Figma export — 3 operations per filter -->
<filter id="glow">
  <feFlood flood-opacity="0" result="bg"/>           <!-- noop -->
  <feBlend in="SourceGraphic" in2="bg" result="shape"/> <!-- noop -->
  <feGaussianBlur stdDeviation="58.59"/>
</filter>

<!-- Cleaned — 1 operation per filter -->
<filter id="glow">
  <feGaussianBlur in="SourceGraphic" stdDeviation="58.59"/>
</filter>
```

`feFlood(opacity=0)` + `feBlend` with transparent = identity operation. Remove them from every filter in Figma SVGs.

---

## 7. Conditional `will-change` — apply before animation, remove after

Each `will-change` creates a permanent GPU layer (~8MB per 1920x1080 element). Too many → layer explosion → worse performance than no `will-change`.

```tsx
/* Bad — permanent GPU layers on 11+ cards */
className="will-change-transform"

/* Good — only during animation */
className={cn(
  active
    ? 'will-change-[opacity,transform] animate-[pulse_2.4s_infinite]'
    : '[animation:none]',   // explicit stop + no will-change
)}
```

For JS-driven animations, use a timer to remove `will-change` after the transition completes (add ~100ms margin over the transition duration).

---

## Quick checklist

Before shipping any animation:

- [ ] No `opacity: 0` anywhere — use `0.01`
- [ ] No `invisible`/`visibility: hidden` on elements that will animate — use `opacity-[0.01]` + `pointer-events-none`
- [ ] `translate-z-0 backface-hidden` on every transitioning element
- [ ] `antialiased` on animated text
- [ ] `@keyframes` use opacity only, no `transform`
- [ ] No `transition: color` on SVGs with blur filters
- [ ] No `setTimeout` for animation sequencing — use CSS timing
- [ ] `will-change` is conditional, not permanent
- [ ] SVGs cleaned of Figma noop filters
