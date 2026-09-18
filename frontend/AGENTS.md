# Frontend Agent Instructions

React + TypeScript UI for **Tradele**, built with Vite. These instructions cover the
`frontend/` tree and complement the root `AGENTS.md` (which covers the backend and general
project conventions).

## Stack

- **React 19** + **TypeScript** (strict mode, `noUnusedLocals`/`noUnusedParameters` are on)
- **Vite** for dev/build; **CSS Modules** for component styles
- No UI framework, no CSS framework, no state library - plain React state and hand-written CSS
- Fonts (loaded from Google Fonts in `index.html`):
  - `Bricolage Grotesque` - wordmark/branding only
  - `Newsreader` (serif) - large numeric hero values (prices, portfolio value, sheet titles)
  - `Space Mono` - tickers, numbers, labels, chips
  - `Instrument Sans` - UI text (buttons, body copy)

## Layout of `frontend/src/`

- `index.css` - design tokens (CSS custom properties on `:root`), global resets, and the
  `.shell` app container. Nothing else belongs here.
- `types.ts` - shared domain types: immutable data types plus the `*State` types that add
  mutable view state on top of them.
- `api/` - the HTTP layer: `client.ts` (fetch wrapper with bearer-token auth + the anonymous
  session bootstrap that creates a user and mints a token, stored in localStorage), `dto.ts`
  (raw request/response types mirroring `app/dtos/*.py` - keep them in sync by hand), and
  `mappers.ts` (DTO → domain-type translation). Nothing here knows about React.
- `services/` - one class per backend domain (`MarketService`, `PortfolioService`,
  `TradesService`, `MetadataService`), exported as singletons. They own the API calls and all
  mapping to domain types; this is also where methods for not-yet-existing endpoints live,
  marked with `TODO:` comments and backed by `mock/data.ts`.
- `hooks/` - thin data-loading hooks (`useAsync` plus one per service call). Components and
  screens read data through these, never through `api/` or `services/` directly.
- `utils/` - pure helpers with no React dependency (number/time formatting, order math). All
  user-visible number formatting goes through `utils/format.ts` so minus signs, grouping, and
  decimals stay consistent.
- `mock/` - deterministic (seeded) generators used by services for endpoints that don't exist
  yet (candle history, portfolio value history). Components never import from here; when an
  endpoint lands, swap the fallback in its service and delete what becomes unused.
- `components/` - components, including ones only used by a single screen.
- `screens/` - one module per tab. Screens own their local UI state and compose components.

## Data flow

`App` bootstraps the session (anonymous user + access token) before rendering any screen;
every API endpoint requires a token. Screens load data via hooks, which call services, which
call `api/`. Components are presentational: data comes in as props (or via a hook), and
interactions go back up as callbacks. Change indicators are always derived from the
displayed series (first point → last point), never from static per-range config - ticker
tiles' daily change comes from the same seeded 1-day series the quote chart uses.

## Conventions

- **Design tokens only.** Colors and font stacks must reference the CSS custom properties
  from `index.css` (`var(--ink)`, `var(--font-mono)`, ...). Never hardcode a hex color or
  font family in a component stylesheet. If the design needs a new color, add a token first.
- **CSS Modules, co-located.** Each component/screen has a sibling `*.module.css`. Class
  names are camelCase. Avoid element/type selectors and avoid `!important`.
- **Adaptive, mobile-first.** Styles target the ~400px mobile viewport first; a single
  `768px` breakpoint (CSS media queries - no JS user-agent sniffing) switches to the desktop
  layout: the `.shell` widens to 1000px and each screen splits into two columns via its
  `.columns`/`.primary`/`.secondary` wrappers (mobile: same wrappers, stacked). Keep the
  breakpoint value consistent across `index.css` and the screen modules. Use
  `env(safe-area-inset-*)` for header/footer padding instead of fixed notch allowances.
- **Components are functions** with named exports and an explicit `Props` interface; only
  `App` uses a default export. Interactive elements should be real `<button>`s (not
  click-handler `<div>`s) for keyboard/accessibility, styled to match the design.
- **Screens own shared state; components own their local UI state** (open/closed, selected
  range, form fields). Lift state to the screen (or `App`) only when more than one component
  needs it. Mock interactions (add/cancel/undo/submit) work purely client-side.
- **Extract screen sections into components.** When a screen grows hard to read, pull
  sections into `components/` even if they're only used by that one screen.
- **Keep component functions under ~50 lines.** When a screen or component grows past
  that, extract sections into `components/` (even single-use ones), or group state into
  private hooks inside the screen file - screens keep owning shared state, hooks just
  bundle it with its handlers.
- **Descriptive names.** No single/double-character variable or field names, except
  established math/graphics names (`x`, `y`) and iteration variables. Helpers use full words
  (`formatUsd`, not `fmtUsd`).
- **Immutable data, separate state.** Domain data types are `readonly` (like Python
  dataclasses); mutable view state (e.g. `cancelling`, `collapsed`) lives in separate
  `*State` types that wrap the data object, never mixed into it.
- **Quantities stay as entered.** Order quantities are `{ shares }` *or* `{ value }` - the
  client never converts between them for submission; the backend (or execution time) does.
  Client-side conversions are for display hints ("≈") only.
- **Charts are hand-rolled SVG** rendering from plain data arrays. Don't add a charting
  library unless there's a strong reason. Chart series come from the services (currently the
  seeded generators in `mock/` - see the TODOs there).
- **Endpoints missing on the backend** still get API-shaped service methods, marked with a
  `TODO:` comment (never prose like "mocked for now") and backed by `mock/data.ts`. When the
  endpoint lands, replace the fallback in the service.
- Keep TypeScript strict-clean: no `any`, no unused imports (the build runs `tsc --noEmit`).

## Design

The UI follows the original "warm-paper" design direction: muted paper backgrounds, ink-dark
text and buttons, green/red for up/down, amber for warnings, and a yellow highlight for the
most recent history set. The tokens in `index.css` are the source of truth for colors and
fonts - component stylesheets must not hardcode values. The iOS device chrome in the original
mockups (status bar, keyboard, home indicator) was presentation-only and is intentionally
**not** part of the app; real devices are handled with `env(safe-area-inset-*)` instead.
Times shown to the user are relative (e.g. "7h left"), never absolute clock times, since
players are in different timezones.

## Common commands

Run from `frontend/` (requires Node 22+):

```bash
npm install        # first time only
npm run dev        # Vite dev server on :5173 (proxies /api to :8000)
npm run build      # tsc --noEmit + vite build -> frontend/dist/
```
