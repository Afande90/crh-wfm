---
name: ibrahim-stitch-design
description: Premium frontend design system skill combining Google Stitch's anti-generic taste rules, prompt enhancement pipeline, React component architecture, and shadcn/ui integration. Use whenever building any frontend — websites, dashboards, artifacts, landing pages, React components, or HTML interfaces. Enforces strict typography, calibrated colour, asymmetric layouts, spring-physics motion intent, and a comprehensive anti-AI-slop ruleset. Works standalone or alongside Stitch-exported DESIGN.md files.
---

# Ibrahim Stitch Design System

This skill encodes the design philosophy and engineering standards from Google's Stitch Skills repo — adapted for Claude Code and Claude.ai artifact generation. It replaces vague aesthetic defaults with precise, opinionated rules that produce premium, non-generic interfaces.

This skill layers on top of `ibrahim-web-design` (for mode selection and aesthetic anchors), `ibrahim-dashboards` (for operational displays), and `frontend-design` (for base Anthropic rendering constraints). When rules conflict, this skill wins on visual taste; the mode-specific skills win on layout structure and audience targeting.

---

## 1. Style Configuration Dials

Before building any frontend, set these dials based on the project. State the chosen levels explicitly before generating code.

| Dial | Range | Default | Description |
|------|-------|---------|-------------|
| **Creativity** | 1–10 | 9 | 1 = Swiss minimal, monochrome. 5 = Clean with personality. 10 = Editorial, inline image typography, strong asymmetry |
| **Density** | 1–10 | 5 | 1 = Gallery-airy, massive whitespace. 5 = Balanced sections. 10 = Cockpit-dense, data-heavy |
| **Variance** | 1–10 | 8 | 1 = Predictable symmetric grids. 5 = Subtle offsets. 10 = Artsy chaotic, no two sections alike |
| **Motion Intent** | 1–10 | 6 | 1 = Static. 5 = Subtle hover/entrance. 10 = Cinematic choreography on every component |

Adapt dynamically: dashboards get Density 7–9, Creativity 4–6. Landing pages get Creativity 8–10, Variance 7–9. Product UI sits in the middle.

---

## 2. Colour Palette Rules

Every project gets ONE accent colour. Name colours by their descriptive character AND functional role.

### Foundation Palette
- **Canvas White** (#F9FAFB) — Primary background. Warm-neutral, never clinical blue-white
- **Pure Surface** (#FFFFFF) — Card and container fill with whisper shadow for elevation
- **Charcoal Ink** (#18181B) — Primary text. Zinc-950 depth
- **Steel Secondary** (#71717A) — Body text, descriptions, metadata. Zinc-500
- **Muted Slate** (#94A3B8) — Tertiary text, timestamps, disabled states
- **Whisper Border** (rgba(226,232,240,0.5)) — Card borders, structural 1px lines
- **Diffused Shadow** (rgba(0,0,0,0.05)) — Card elevation. 40px blur, -15px offset

### Accent Selection (pick ONE per project)
- **Emerald Signal** (#10B981) — Growth, success, positive dashboards
- **Electric Blue** (#3B82F6) — Productivity, SaaS, developer tools
- **Deep Rose** (#E11D48) — Creative, editorial, fashion-adjacent
- **Amber Warmth** (#F59E0B) — Community, social, warm-toned products

### Banned Colours
- Purple/Violet neon gradients (the "AI Purple" aesthetic) — STRICTLY BANNED
- Pure Black (#000000) — always Off-Black or Zinc-950
- Oversaturated accents above 80% saturation
- Mixed warm/cool gray systems within one project

### Format Rule
When specifying colours in code or prompts, always use: `Descriptive Name (#hexcode) for functional role`

---

## 3. Typography Rules

### Font Selection
- **Display:** `Geist`, `Satoshi`, `Cabinet Grotesk`, or `Outfit` — Track-tight (-0.025em), controlled fluid scale, weight-driven hierarchy (700–900). Leading compressed (1.1)
- **Body:** Same family at weight 400. Relaxed leading (1.65), 65ch max-width, Steel Secondary colour
- **Mono:** `Geist Mono` or `JetBrains Mono` — For code, metadata, timestamps. When Density exceeds 7, all numbers switch to monospace
- **Scale:** Display at `clamp(2.25rem, 5vw, 3.75rem)`. Body at 1rem/1.125rem. Mono metadata at 0.8125rem

### Banned Fonts
- `Inter` — BANNED everywhere in premium/creative contexts
- Generic serif fonts (`Times New Roman`, `Georgia`, `Garamond`, `Palatino`) — BANNED. If serif is needed for editorial/creative contexts, use only: `Fraunces`, `Gambarino`, `Editorial New`, or `Instrument Serif`
- Serif is ALWAYS BANNED in dashboards or software UIs regardless
- `Roboto`, `Arial`, `Helvetica` as display typefaces — BANNED

### In Claude.ai Artifacts (React .jsx)
When building artifacts where Google Fonts cannot be loaded, fall back to system font stacks that approximate the intended character. Never default to `sans-serif` without specifying the stack. Use Tailwind's `font-sans` only as last resort.

---

## 4. Hero Section Rules

The Hero is the first impression — it must be striking and never generic.

- **Inline Image Typography:** At Creativity 7+, embed small contextual photos directly between words in the headline. Images sit inline at type-height, rounded, acting as visual punctuation. This is the signature creative technique
- **No Overlapping:** Text must never overlap images or other text. Every element occupies its own clean spatial zone. No z-index stacking of content layers
- **No Filler Text:** "Scroll to explore", "Swipe down", scroll arrow icons, bouncing chevrons — ALL BANNED. The content pulls users in naturally
- **Asymmetric Structure:** Centred Hero layouts BANNED when Variance exceeds 4. Use Split Screen, Left-Aligned text / Right visual, or Asymmetric Whitespace
- **CTA Restraint:** Maximum one primary CTA. No secondary "Learn more" links. No redundant micro-copy below the headline

---

## 5. Component Stylings

### Buttons
- Flat surface, no outer glow. Primary: accent fill with white text. Secondary: ghost/outline
- Active state: `-1px translateY` or `scale(0.98)` for tactile push feedback
- Hover: subtle background shift, never glow. No custom mouse cursors
- Full-width on mobile

### Cards/Containers
- Generously rounded corners (2.5rem). Pure white fill. Whisper border (1px, semi-transparent)
- Diffused shadow: `0 20px 40px -15px rgba(0,0,0,0.05)`
- Internal padding 2rem–2.5rem
- Used ONLY when elevation communicates hierarchy — high-density layouts (Density 7+) replace cards with `border-top` dividers or negative space

### Inputs/Forms
- Label above input. Error text below in Deep Rose. Focus ring in accent colour, 2px offset
- No floating labels. Standard 0.5rem gap between label-input-error stack

### Navigation
- Sleek, sticky. No hamburger on desktop. Clean horizontal with generous spacing
- Desktop horizontal nav collapses to clean mobile menu (slide-in or full-screen overlay)

### Loaders
- Skeletal shimmer matching exact layout dimensions and rounded corners
- Never circular spinners — skeletal shimmer only

### Empty States
- Composed illustration or icon composition with guidance text
- Never just "No data found"

---

## 6. Layout Principles

- **Grid-First:** CSS Grid for all structural layouts. Never flexbox percentage math (`calc(33% - 1rem)` is BANNED)
- **No Overlapping:** Elements must never overlap. Every element occupies its own grid cell or flow position
- **Feature Sections:** The "3 equal cards in a row" pattern is BANNED. Use 2-column Zig-Zag, asymmetric Bento grids (2fr 1fr 1fr), or horizontal scroll galleries
- **Containment:** All content within `max-width: 1400px`, centred. Generous horizontal padding (1rem mobile, 2rem tablet, 4rem desktop)
- **Full-Height:** Use `min-height: 100dvh` — never `height: 100vh` (iOS Safari address bar jump)
- **Bento Architecture:** For feature grids: Row 1 = 3 columns, Row 2 = 2 columns (70/30 split). Each tile contains a perpetual micro-animation

---

## 7. Responsive Rules — MANDATORY

Every screen must work across all viewports. This is a hard requirement, not optional polish.

- **Mobile-First Collapse (< 768px):** All multi-column layouts collapse to single column. `width: 100%`, `padding: 1rem`, `gap: 1.5rem`. No exceptions
- **No Horizontal Scroll:** Horizontal overflow on mobile is a critical failure
- **Typography Scaling:** Headlines scale via `clamp()`. Body text minimum 1rem/14px
- **Touch Targets:** All interactive elements minimum 44px tap target
- **Image Behaviour:** Inline typography images stack below headline on mobile
- **Navigation:** Desktop horizontal nav collapses to clean mobile menu
- **Cards & Grids:** Bento grids revert to stacked single-column cards with full-width on mobile
- **Spacing:** Vertical section gaps reduce proportionally: `clamp(3rem, 8vw, 6rem)`
- **Testing Viewports:** 375px (iPhone SE), 390px (iPhone 14), 768px (iPad), 1024px (laptop), 1440px (desktop)

---

## 8. Motion & Interaction Intent

Stitch and static renders don't animate — this section documents intended motion for the coding phase.

- **Spring Physics:** `stiffness: 100, damping: 20`. No linear easing anywhere
- **Perpetual Micro-Loops:** Pulse on status dots, Typewriter on search bars, Float on feature icons, Shimmer on loading states
- **Staggered Orchestration:** Lists mount with cascaded delays: `animation-delay: calc(var(--index) * 100ms)`. Waterfall reveals, never instant mount
- **Hardware Rules:** Animate ONLY `transform` and `opacity`. Never `top`, `left`, `width`, `height`
- **Performance:** CPU-heavy perpetual animations isolated in leaf components. Never trigger parent re-renders. Target 60fps

---

## 9. Prompt Enhancement Pipeline

When Ibrahim describes a UI vaguely, enhance the prompt before building. This is the Stitch prompt engineering methodology applied to Claude.

### Step 1: Assess What's Missing

| Element | Check for | If missing... |
|---------|-----------|---------------|
| Platform | "web", "mobile", "desktop" | Add based on context |
| Page type | "landing page", "dashboard", "form" | Infer from description |
| Structure | Numbered sections/components | Create logical page structure |
| Visual style | Adjectives, mood, vibe | Add descriptors from this skill |
| Colours | Specific values or roles | Apply foundation palette + one accent |
| Components | UI-specific terms | Translate to proper keywords |

### Step 2: Refine Vague Terms

| Vague | Enhanced |
|-------|---------|
| "menu at the top" | "sticky navigation bar with logo and menu items" |
| "button" | "primary call-to-action button with tactile push feedback" |
| "list of items" | "responsive card grid with hover states and subtle elevations" |
| "form" | "clean form with labeled input fields, validation states, and submit button" |
| "big photo" | "high-impact hero section with full-width imagery" |
| "modern" | "clean, minimal, with generous whitespace and high-contrast typography" |
| "professional" | "sophisticated, trustworthy, utilizing subtle shadows and a restricted, premium palette" |
| "dark mode" | "electric, high-contrast accents on deep slate or near-black backgrounds" |

### Step 3: Structure the Output

Format the enhanced prompt:
```
[One-line page purpose and vibe]

DESIGN SYSTEM:
- Platform: [Web/Mobile], [Desktop/Mobile]-first
- Theme: [Light/Dark], [style descriptors]
- Background: [Colour description] (#hex)
- Primary Accent: [Colour description] (#hex) for [role]
- Text Primary: [Colour description] (#hex)

PAGE STRUCTURE:
1. [Section]: [Description]
2. [Section]: [Description]
...
```

---

## 10. React Component Architecture

When building React components (artifacts or files), follow these structural rules:

- **Modular components:** Break designs into independent files. Avoid monolithic single-file outputs
- **Logic isolation:** Event handlers and business logic go in custom hooks
- **Data decoupling:** All static text, image URLs, and lists into separate data objects/files
- **Type safety:** Every component includes a TypeScript interface named `[ComponentName]Props` (when using .tsx)
- **Style mapping:** Use theme-mapped Tailwind classes instead of arbitrary hex codes
- **Dark mode:** Apply `dark:` variants to all colour classes
- **No hardcoded hex values** in className strings — use CSS custom properties or Tailwind theme extensions

### Architecture Checklist
- [ ] Logic extracted to custom hooks
- [ ] No monolithic files — atomic/composite modularity
- [ ] All static text/URLs in data layer
- [ ] Props use `Readonly<T>` interfaces (TypeScript)
- [ ] Dark mode applied to all colour classes
- [ ] No hardcoded hex values — theme-mapped classes only

---

## 11. shadcn/ui Integration

When using shadcn/ui components (available in Claude.ai React artifacts):

- Import from `@/components/ui/[component]`
- Use `cn()` utility for class merging: `import { clsx } from "clsx"` + `twMerge`
- Customise radii, colours, shadows to match this design system — no generic shadcn defaults
- Available component categories: buttons, cards, dialogs, inputs, tables, tabs, accordions, alerts, badges, tooltips
- Use `class-variance-authority` (cva) for variant logic
- Extend components in a wrapper layer, never modify the base component directly

---

## 12. DESIGN.md Integration

If Ibrahim provides a DESIGN.md file (exported from Stitch or hand-written), it becomes the single source of truth for that project. This skill's defaults are overridden by any DESIGN.md tokens.

To create a DESIGN.md for a new project, follow this structure:

```
# Design System: [Project Title]

## 1. Visual Theme & Atmosphere
(Evocative description of mood, density, variance, motion intensity)

## 2. Colour Palette & Roles
(Descriptive Name + #hex + Functional Role for each colour)

## 3. Typography Rules
(Font families, weight hierarchy, scale, banned fonts)

## 4. Component Stylings
(Buttons, cards, inputs, loaders, empty states — shape, colour, behaviour)

## 5. Layout Principles
(Grid system, whitespace strategy, containment, responsive architecture)

## 6. Motion & Interaction
(Spring physics, stagger rules, hardware constraints)

## 7. Anti-Patterns (Banned)
(Explicit list of forbidden patterns)
```

---

## 13. Anti-Patterns — BANNED LIST

This is the most critical section. These rules prevent AI-generated-looking output.

### Visual Anti-Patterns
- No emojis anywhere in UI
- No `Inter` font
- No generic serif fonts — distinctive modern serifs only if editorial context demands it
- No pure black (#000000) — Off-Black or Zinc-950 only
- No neon outer glows or default box-shadow glows
- No oversaturated accent colours above 80%
- No excessive gradient text on large headers
- No custom mouse cursors
- No overlapping elements — clean spatial separation always
- No 3-column equal card layouts for features
- No centred Hero sections (when Variance exceeds 4)
- No circular loading spinners — skeletal shimmer only
- No `h-screen` — always `min-h-[100dvh]`
- No `z-index` spam — only for Navbar, Modal, Overlay contexts

### Content Anti-Patterns
- No filler UI text: "Scroll to explore", "Swipe down", scroll arrows, bouncing chevrons
- No generic names: "John Doe", "Sarah Chan", "Acme", "Nexus", "SmartFlow"
- No fake round numbers: `99.99%`, `50%` — use organic data: `47.2%`
- No fabricated data or statistics — never generate metrics, uptime percentages, response times, or any data not explicitly provided. Use `[metric]` placeholders if real data unavailable
- No fake system/metric sections — "SYSTEM PERFORMANCE METRICS", "KEY STATISTICS" cards with invented data are BANNED
- No `LABEL // YEAR` formatting — "SYSTEM // 2024" is a lazy AI convention
- No AI copywriting clichés: "Elevate", "Seamless", "Unleash", "Next-Gen", "Revolutionize"
- No broken Unsplash links — use `picsum.photos/seed/{id}/800/600` or SVG avatars
- No generic shadcn/ui defaults without customisation

### Technical Anti-Patterns
- No flexbox percentage math: `calc(33% - 1rem)` — use CSS Grid
- No `height: 100vh` — use `min-height: 100dvh`
- No animating `top`, `left`, `width`, `height` — only `transform` and `opacity`
- No `z-index` stacking beyond navbar/modal/overlay contexts

---

## 14. Shape & Depth Translation

When describing or implementing shapes:

| Technical | Natural Language |
|-----------|-----------------|
| `rounded-none` | Sharp, squared-off edges |
| `rounded-sm` | Slightly softened corners |
| `rounded-md` | Gently rounded corners |
| `rounded-lg` | Generously rounded corners |
| `rounded-xl` | Very rounded, pillow-like |
| `rounded-full` | Pill-shaped, circular |

Depth levels:
- **Flat:** No shadows, colour blocking and borders only
- **Whisper-soft:** Diffused, light shadows for subtle lift
- **Floating:** High-offset, soft shadows for elevated elements
- **Inset:** Inner shadows for pressable or nested elements

---

## What This Skill Is Not For

- Not a replacement for `ibrahim-web-design` mode selection — use that skill to pick Editorial Minimal / Agency Bold / Product UI / Creative Range, then apply this skill's taste rules within the chosen mode
- Not for PDF generation — use `ibrahim-pdf-documents`
- Not for CVs — use `ibrahim-healthcare-application`
- Not for Stitch MCP server calls (generate_screen, edit_screens) — those require the Stitch MCP which is not available in Claude Code/claude.ai
