---
name: frontend-ui-ux-design
description: 前端 UI/UX 设计与工程规范技能(React/shadcn-ui 与 Vue/shadcn-vue 双栈):两遍设计契约(先定六语义色 Token/布局骨架/组件映射再写代码)、60-30-10 配色、8pt 间距网格、四态可用性基线与反 AI 俗套审查。Use when 用户要求创建、美化、重构或审查前端页面、组件、仪表盘、表单,界面显得简陋/有 AI 模板味,或需要产出前端设计契约与走查清单时。技术基线与自检细则以全局 AGENTS.md「前端 UI 规范」节为准。
---

# Frontend UI/UX Design — 前端 UI/UX 设计与工程规范

Enforce modern design systems, component library reuse, 8pt spacing grids, and four-state usability baselines when building or reviewing frontend interfaces. Eliminate generic AI visual cliches so every generated page looks clean, intentional, and production-ready.

## When to Use

- Building a new frontend page, dashboard, landing page, form, or modal in React, Vue, or Tailwind CSS
- Refactoring or beautifying an existing UI that looks cluttered, outdated, or overly generic
- Generating frontend design configurations (such as CLAUDE.md, .cursorrules, or sub-agent prompts)
- Auditing frontend code or DOM snapshots for layout breakage, contrast issues, or missing interaction states

## Steps

### 1. Execute the Two-Pass Design Contract Before Coding

Before writing component code for any new page or complex view, establish three design constraints:

- **Design Tokens**: Define semantic colors for bg-canvas (page background), bg-surface (card/container background), text-primary, text-muted, accent-primary (single primary CTA color), and border-subtle.
- **Layout Skeleton**: Select a standard layout pattern such as Sidebar + Topbar + Main Bento Grid, Single-Column Centered Flow (max-w-4xl), or Master-Detail Split View.
- **Component Mapping**: List existing UI library primitives to reuse (such as Dialog, Sheet, DataTable, Select, Skeleton, Toast). Never hand-roll raw HTML substitutes when a library primitive exists.

### 2. Match the Tech Stack and Reuse Mature Primitives

Adapt to the project's framework and rely on accessible component primitives rather than ad-hoc CSS:

- **React (React 18/19, Next.js, Vite)**: Use shadcn/ui (@radix-ui primitives) + Tailwind CSS, lucide-react icons (size-4 inside buttons, size-5 for navigation, strokeWidth={1.75}), and shadcn/ui charts (Recharts) for data visualization.
- **Vue (Vue 3.5+, Nuxt 3)**: Use shadcn-vue (reka-ui / radix-vue) or Nuxt UI with lucide-vue-next icons. When working with Element Plus or Ant Design Vue, override default primary colors and border radii via CSS variables for a cleaner visual hierarchy.
- **Forbidden Raw Controls**: Never use raw `<select>`, `<input type="date">`, window.alert(), window.confirm(), or custom fixed inset-0 bg-black/50 modals without focus trapping and keyboard escape support.

### 3. Apply the 60-30-10 Color and Contrast Discipline

Keep the color palette restrained so content and primary actions stand out clearly:

- **Light Mode**:
  - Canvas background (60%): Soft off-white or cool gray (bg-zinc-50/80 or bg-slate-50) to create subtle separation from white cards.
  - Card/Surface (30%): Pure white (bg-white) with a hairline border (border border-zinc-200/80), subtle elevation (shadow-2xs), and consistent rounding (rounded-xl).
  - Primary Accent (10%): High-contrast neutral (bg-zinc-900 text-zinc-50 hover:bg-zinc-800) or a single brand color (bg-blue-600 hover:bg-blue-700 text-white). Allow only one solid primary CTA button per viewport area; use outline, secondary, or ghost variants for secondary actions.
- **Dark Mode**:
  - Canvas background: Deep zinc (bg-zinc-950 / #09090B). Avoid pure black (#000000) paired with pure white (#FFFFFF) text to prevent halation.
  - Card/Surface: Elevated dark slate (bg-zinc-900/90 border border-zinc-800/80 rounded-xl).
  - Muted text: text-zinc-400 to maintain WCAG AA contrast (>= 4.5:1).

### 4. Enforce the 8pt Spacing Grid and Typography Scale

Establish visual hierarchy through font weight, color contrast, and predictable whitespace rather than oversized fonts:

- **Page Container**: max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6 md:py-8 space-y-6
- **Card Padding and Grid**: Use consistent p-5 or p-6 inside cards with space-y-4 between header and body. Align multi-card grids using grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 md:gap-6 and ensure equal card heights (h-full flex flex-col justify-between).
- **Typography Hierarchy**:
  - Page Title: text-2xl font-semibold tracking-tight text-zinc-900 dark:text-zinc-50
  - Card/Section Title: text-base font-semibold tracking-tight text-zinc-900 dark:text-zinc-100
  - Body Text: text-sm font-normal text-zinc-700 dark:text-zinc-300 leading-relaxed
  - Muted/Caption: text-xs font-normal text-zinc-500 dark:text-zinc-400
  - Numeric Metrics and Currency: text-2xl md:text-3xl font-bold tracking-tight tabular-nums. Always apply tabular-nums and text-right to numeric table columns and financial figures.

### 5. Implement the 4-State Usability Baseline

Every data-driven component or form must handle all four operational states:

- **Loading State**: Render layout-matching Skeleton placeholders during initial fetches instead of an isolated centered spinner. Disable submit buttons during async actions and prepend `<Loader2 className="mr-2 size-4 animate-spin" />`.
- **Empty State**: Never render plain "No data" text alone. Provide a centered muted icon container (size-10 rounded-full bg-zinc-100 flex items-center justify-center text-zinc-500), a clear title, a short explanation, and an actionable button (such as "+ Create Item" or "Reset Filters").
- **Error State**: Display inline field validation messages (text-xs text-red-600 dark:text-red-400) below invalid inputs with border-red-500. Provide a clear retry action when network requests fail.
- **Overflow and Responsive Protection**: Add min-w-0 to flex/grid children containing dynamic text, and apply truncate or line-clamp-2 to long titles, filenames, or emails. Add whitespace-nowrap to button labels and overflow-x-auto to wide data tables.

### 6. Run Pre-Delivery Visual and Accessibility Audit

Before completing the task, verify the output against these criteria:

- [ ] No unrequested purple/blue/pink gradients or rainbow gradient text
- [ ] No repetitive ALL-CAPS tracked-out eyebrow badges above every section heading
- [ ] Flex/Grid containers with long user text include min-w-0 and truncate
- [ ] All icon-only buttons include aria-label and Tooltip
- [ ] Button labels use specific action verbs ("Save Configuration", "Export CSV") rather than vague labels ("Submit", "OK")

## Gotchas

- **AI Slop Cliches**: Avoid defaulting to purple-to-indigo gradients (from-indigo-500 via-purple-500 to-pink-500), italicizing or highlighting a random word inside headings, or adding colored drop shadows (shadow-blue-500/30). These immediately make an interface look templated and artificial.
- **Flexbox Text Overflow**: In Tailwind CSS, truncate (overflow: hidden; text-overflow: ellipsis; white-space: nowrap;) fails inside a flex item unless the flex item or its wrapper has min-w-0. Always pair flex-1 min-w-0 with truncate.
- **Inconsistent Padding**: Mixing arbitrary spacing like p-2, p-3, and p-5 across sibling cards creates visual jitter. Stick strictly to p-5 or p-6 for cards and gap-4 or gap-6 for grids.
