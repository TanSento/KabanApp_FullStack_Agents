# Frontend Strategy

## Overview

The frontend is a Next.js 16 application using React 19. It renders a single-board Kanban workspace with drag-and-drop card rearrangement, inline column renaming, and card creation/deletion. All state is currently local (in-memory via `useState`); there is no backend integration yet.

## Tech Stack

| Layer         | Technology                            |
|---------------|---------------------------------------|
| Framework     | Next.js 16.1.6 (App Router)          |
| UI Library    | React 19.2.3                         |
| Styling       | Tailwind CSS 4 (via `@tailwindcss/postcss`) |
| Drag and Drop | @dnd-kit/core 6, @dnd-kit/sortable 10 |
| Utility       | clsx                                  |
| Unit Tests    | Vitest 3 + Testing Library + jsdom   |
| E2E Tests     | Playwright 1.58                      |
| Language      | TypeScript 5                         |

## Project Structure

```
frontend/
  src/
    app/
      page.tsx         -- Root page, renders KanbanBoard
      layout.tsx       -- HTML shell, loads Space Grotesk + Manrope fonts
      globals.css      -- CSS custom properties (design tokens) + Tailwind import
      favicon.ico
    components/
      KanbanBoard.tsx       -- Top-level board component; owns all state + DnD context
      KanbanBoard.test.tsx  -- Unit tests for board rendering, column rename, card CRUD
      KanbanColumn.tsx      -- Single column; droppable zone, sortable card list, rename input
      KanbanCard.tsx        -- Single card; sortable, displays title/details, delete button
      KanbanCardPreview.tsx -- Card shown in DragOverlay during drag
      NewCardForm.tsx       -- Expandable form at bottom of each column for adding cards
    lib/
      kanban.ts        -- Types (Card, Column, BoardData), initial seed data, moveCard logic, createId helper
      kanban.test.ts   -- Unit tests for moveCard (reorder, cross-column, drop on column)
    test/
      setup.ts         -- Vitest setup (imports @testing-library/jest-dom)
      vitest.d.ts      -- Type declarations for Vitest globals
  tests/
    (Playwright E2E test directory -- currently empty)
  vitest.config.ts     -- Vitest config: jsdom, path alias @/ -> src/
  playwright.config.ts -- Playwright config: chromium, localhost:3000
  next.config.ts       -- Next.js config (currently empty)
  package.json
```

## Architecture

### Data Model (`lib/kanban.ts`)

- **Card**: `{id, title, details}`
- **Column**: `{id, title, cardIds}` -- `cardIds` is an ordered array of card IDs
- **BoardData**: `{columns: Column[], cards: Record<string, Card>}` -- normalized structure

The `moveCard` function is a pure function handling all card movement logic: same-column reorder, cross-column transfer, and drop-on-empty-column. `createId` generates unique IDs with a random + timestamp suffix.

### Component Hierarchy

```
page.tsx
  └── KanbanBoard (client component, "use client")
        ├── DndContext (dnd-kit)
        │     ├── KanbanColumn[] (useDroppable)
        │     │     ├── SortableContext
        │     │     │     └── KanbanCard[] (useSortable)
        │     │     └── NewCardForm
        │     └── DragOverlay
        │           └── KanbanCardPreview
        └── Header (inline, shows column pills)
```

### State Management

All board state lives in `KanbanBoard` via `useState<BoardData>`. Event handlers:
- `handleDragEnd` -- calls `moveCard` and updates state
- `handleRenameColumn` -- updates column title in state
- `handleAddCard` -- creates a new card via `createId` and adds to state
- `handleDeleteCard` -- removes card from state

No context providers, no external state libraries. This will need to be refactored when the backend is introduced (Part 7).

## Design System

CSS custom properties defined in `globals.css`:

| Token              | Value                        | Usage                     |
|--------------------|------------------------------|---------------------------|
| `--accent-yellow`  | `#ecad0a`                    | Accent lines, highlights  |
| `--primary-blue`   | `#209dd7`                    | Links, key sections       |
| `--secondary-purple` | `#753991`                  | Buttons, actions          |
| `--navy-dark`      | `#032147`                    | Main headings             |
| `--gray-text`      | `#888888`                    | Supporting text, labels   |
| `--surface`        | `#f7f8fb`                    | Page background           |
| `--surface-strong` | `#ffffff`                    | Card/column background    |
| `--stroke`         | `rgba(3,33,71,0.08)`        | Borders                   |
| `--shadow`         | `0 18px 40px rgba(...)` | Card/header elevation     |

Fonts: **Space Grotesk** (display/headings), **Manrope** (body text), loaded via `next/font/google`.

## Testing

### Unit Tests (Vitest)

Run with `npm run test:unit` from `frontend/`.

- `kanban.test.ts`: 3 tests for `moveCard` (reorder, cross-column, drop-on-column)
- `KanbanBoard.test.tsx`: 3 tests (renders 5 columns, renames column, adds/deletes card)

### E2E Tests (Playwright)

Run with `npm run test:e2e` from `frontend/`.

Config spins up a dev server on port 3000. Currently no test files in `tests/`.

## Key Conventions

- All components are named exports (not default exports)
- `data-testid` attributes on columns (`column-{id}`) and cards (`card-{id}`) for test targeting
- `aria-label` attributes on interactive elements for accessibility
- Tailwind utility classes used directly in JSX; no separate CSS modules
- Pure functions for logic (`moveCard`, `createId`), components for rendering
