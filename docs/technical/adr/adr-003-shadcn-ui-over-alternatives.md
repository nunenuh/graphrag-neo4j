# ADR-003: Use Tailwind CSS + shadcn/ui for the Frontend

**Date:** 2026-03-02
**Status:** Accepted

---

## Context

The frontend (Vite + React + TypeScript) needs a UI library. The project requires:
- Chat panel with input, button, scroll area
- Node type badges (Paper / Method / Task / Dataset)
- Collapsible panel for the Cypher query block
- Card panels for layout
- Dark mode support
- Zero interference with `react-force-graph-2d` (client-side canvas)

---

## Decision

Use **Tailwind CSS + shadcn/ui**.

shadcn/ui is not a traditional component library — it's a collection of copy-paste components built on Radix UI primitives and styled with Tailwind. You own the component code; there is no runtime dependency.

---

## Alternatives Considered

### Tailwind + DaisyUI
- Fast setup (Tailwind plugin, no JS overhead)
- Fewer components — missing Collapsible and ScrollArea natively
- Less customizable for complex interaction patterns
- Good for fast prototyping, not ideal for explainability-focused UI

### Mantine
- 100+ components, built-in hooks
- ~50KB bundle overhead (small but adds up with graph lib)
- Opinionated theming — harder to match custom graph colors
- Occasionally conflicts with canvas-based components

### Chakra UI
- Highest adoption (~700k weekly downloads)
- CSS-in-JS runtime cost
- Largest bundle (~100KB+)
- Becoming less trendy relative to Tailwind-first solutions

### shadcn/ui + Tailwind (chosen)
- Zero runtime overhead — components live in your codebase
- Radix UI primitives = accessible, composable, unstyled by default
- Exact components needed: `Card`, `Badge`, `Collapsible`, `ScrollArea`, `Input`, `Button`, `Tooltip`
- Dark mode via CSS variables — one line of config
- Won't interfere with `react-force-graph-2d` (no global CSS side effects)
- Highest momentum in AI/ML dashboard projects (2025-2026)

---

## Note on CLI Package Name

The `shadcn-ui` npm package is deprecated. The project renamed its CLI to `shadcn`.
The component library itself is fully active (106k+ GitHub stars, actively maintained).

## Setup

```bash
# 1. Init Vite project
npm create vite@latest frontend -- --template react-ts

# 2. Install Tailwind
npm install -D tailwindcss postcss autoprefixer
npx tailwindcss init -p

# 3. Init shadcn (new CLI name — NOT shadcn-ui)
npx shadcn@latest init

# 4. Add components used in this project
npx shadcn@latest add card button badge input
npx shadcn@latest add collapsible scroll-area tooltip
```

---

## Components Used

| shadcn/ui Component | Used For |
|--------------------|----------|
| `Card` | Chat panel, graph panel containers |
| `Input` | Question input field |
| `Button` | Submit button, example question chips |
| `Badge` | Node type labels (Paper / Method / Task / Dataset) |
| `Collapsible` | Cypher query expandable panel |
| `ScrollArea` | Chat answer scroll container |
| `Tooltip` | Graph node hover details |

---

## Consequences

- Components live in `frontend/components/ui/` — fully owned, no version lock
- Updating a component means editing the file directly (not a package update)
- Tailwind config must include shadcn's CSS variable setup for theming
- Dark mode toggle is trivial to add in v2 (one CSS class on `<html>`)
