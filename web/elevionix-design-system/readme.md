# Elevionix Tech Labs — Design System

Elevionix Tech Labs builds **software for small organizations to automate their business processes** — invoice-to-approval flows, client onboarding, GST/compliance checklists, payroll runs — with a dedicated **legal-process automation** vertical for firms and chambers (matters, deadlines, filings). The context is Indian SMB (₹ amounts, Tally, GST, registry filings).

The product promise, in the brand's own words: **"Automation your business can stand on."** The tone is dependable and operational — this is software you trust with the boring, exacting work.

## Sources

This system was derived entirely from materials the user supplied:

- **`company/elevionix-brand-foundation-v3-gold.html`** — the canonical brand foundation ("v3, gold edition"). Defines the full palette, type system, component patterns (buttons, badges, fields, empty states), and two product screens (process-automation operations view + legal matters view). Every token and pattern here is lifted verbatim from this file.
- **`uploads/elevionix_logo_nbg.png`** — the saffron "E" swoosh logo with "ELEVIONIX / TECH LABS" wordmark, transparent background. Copied to `assets/elevionix-logo.png`.

No codebase, Figma file, or slide deck was provided — so there is no product source code to cross-reference beyond the brand-foundation HTML. If a component repo or Figma exists, share it and this system can be tightened against it.

---

## Content fundamentals

How Elevionix writes:

- **Voice:** plain, declarative, operational. Short sentences. States facts about what the software does. *"Map your first process and Elevionix will run it on schedule."*
- **Person:** addresses the business/user as **you/your** ("your workflows", "your business"); the product is named in the third person ("Elevionix will run it").
- **Casing:** sentence case everywhere in prose and buttons ("Start automation", "Save changes"). **Uppercase is reserved** for mono labels, eyebrows, and the wordmark tagline (`TECH LABS`, `ACTIVE WORKFLOWS`).
- **Headings** are confident and concrete, often with a wry operational ring: *"Gold ledger, saffron action"*, *"Brown ink, weight does the talking"*, *"Processes, made dependable."*
- **Status is always written out**, never colour-only — "Active", "Awaiting review", "Draft", "2 overdue".
- **Data is explicit:** deadlines are full dates ("Due 24 Jul 2026"), never "soon"; IDs are mono (`MTR-2026-0148`); money carries the ₹ symbol and Indian digit grouping (₹1,20,000).
- **No emoji.** No exclamatory marketing hype. No em-dash-free run-ons — the brand uses em dashes as connective punctuation ("Invoice → approval → Tally").
- **Buttons name the action:** "Start automation", "Map a process", "Create workflow" — verbs, not "Submit"/"OK".

---

## Visual foundations

- **Palette — four families, each with one fixed job.** Brown is structure and text; gold is detail (labels, seals, table headers, rules); yellow is highlight and background warmth; orange (the logo saffron `#E57200`) is action. The rule that gives the brand its discipline: **orange appears once per screen**, on the single committing action. Everything else is brown/gold/yellow. No blues, no purples, no gradients.
- **Backgrounds:** flat warm cream (`--yellow-pale #FDF6E0`) for pages; a near-white cream (`--yellow-card #FFFBEE`) for raised cards; deep brown (`--brown-deep #33200D`) for anchor surfaces — headers, nav bars, footers, login hero. No photography, no textures, no illustration, no gradients. The warmth comes entirely from the cream/brown tone, not from imagery.
- **Type:** three faces. **Schibsted Grotesk** heavy (700–800), tight tracking (−.015 to −.02em) for all display/headings, stat values and the italic wordmark. **Instrument Sans** (400–600) for body, buttons, inputs. **IBM Plex Mono** (400–500) for all "data" — IDs, dates, amounts, and uppercase labels/eyebrows (letter-spacing .1–.16em). All type sits in brown; gold is used only for the small uppercase labels.
- **The seal.** The signature motif is a short **4px × 44px gold rule** ("seal") stamped beneath section headings — like a wax stamp on a ledger. It is the one decorative flourish.
- **Spacing:** 8px base grid (4/8/12/16/24/32/56/64). Sections breathe with 64px vertical padding.
- **Corner radii:** small and restrained — 4px (buttons, inputs), 8px (stat cards, chips), 12px (panels, app frame, code blocks). Badges are fully pill (999px). Nothing is heavily rounded.
- **Cards:** cream surface, **1px `--gold-soft #EBDFC0` hairline border**, 8–12px radius, and *flat by default* (no shadow). Elevation is reserved for floating/framed surfaces — the app frame and login card carry the single low, warm-brown-tinted shadow: `0 1px 2px rgba(51,32,13,.06), 0 10px 28px -14px rgba(51,32,13,.24)`.
- **Borders & rules:** hairline `--gold-soft` for card borders and table header rules; a fainter `#F3EBD6` for interior table-row rules.
- **Buttons:** three intents — `accent` (orange, commits), `primary` (deep brown, neutral-primary), `quiet` (transparent, gold-soft border, for reversible/cancel). 4px radius, 600 weight.
- **Hover / press:** hover *darkens* — orange → `--orange-deep #C05E00`, brown-primary → `--brown`; quiet buttons shift their border gold-soft → gold. Transitions are quick and utilitarian (background/border-color ~.15s). **No bounces, no scale, no elaborate motion.** The only motion in the source is a subtle 8px rise-and-fade on the masthead, gated behind `prefers-reduced-motion`.
- **Focus:** 2px orange outline (offset 2px) on buttons; inputs draw an orange border plus a soft 3px orange glow `rgba(229,114,0,.16)`.
- **Badges/status:** active fills yellow-tinted, pending leans orange-tinted, draft is a quiet outline — always with written-out text.
- **Transparency & blur:** used sparingly — badge fills are low-alpha tints of yellow/orange; the modal scrim is `rgba(51,32,13,.42)` brown. No backdrop blur, no glassmorphism.
- **Imagery vibe:** warm, dry, document-like. There is no photography in the brand; if imagery is added it should stay warm and restrained to keep the ledger feel.

---

## Iconography

The brand foundation and logo contain **no icon set** — the source uses none. Meaning is carried by **type, colour and the gold seal**, not glyphs. Consistent with that:

- **No icon font, no SVG icon system, no PNG icons** are defined by Elevionix. Do not invent one.
- **No emoji, no unicode symbols as icons.** The only non-alphabetic marks in use are the arrow "→" inside workflow names ("Invoice → approval → Tally") and the "·" middot as a separator in mono metadata.
- The one graphic mark is the **logo** (`assets/elevionix-logo.png`) — the saffron "E" swoosh. Use it for brand presence; use the `Wordmark` component for inline type lockups.
- **If a UI genuinely needs icons** (e.g. a real product build), introduce a single restrained line set — **Lucide** is the closest match to the brand's plain, utilitarian tone (link from CDN) — and keep strokes thin and monochrome in brown/gold. **This would be an addition not present in the source; flag it to the brand owners before shipping.**

---

## Fonts

All three faces are **Google Fonts** and are loaded via `@import` in `tokens/fonts.css` (Schibsted Grotesk, Instrument Sans, IBM Plex Mono). No binaries are vendored — consumers with internet access get them automatically. If you need self-hosted/offline binaries, ask and they can be vendored as `@font-face` files.

---

## Components

Reusable primitives — exactly the families the brand foundation defines (no invented extras). Import from the compiled bundle: `const { Button } = window.ElevionixDesignSystem_f5b95d`.

| Component | Group | What it is |
|---|---|---|
| `Button` | buttons | accent / primary / quiet action, 3 sizes, disabled |
| `Badge` | feedback | active / pending / draft status pill (text always shown) |
| `EmptyState` | feedback | zero-data placeholder, quiet heading + single action |
| `Field` | forms | labelled text input with hint and orange focus ring |
| `Panel` | surfaces | standard cream card with gold-soft hairline |
| `StatCard` | surfaces | KPI tile — gold label, heavy value, mono delta |
| `Wordmark` | brand | the "ELEVIONIX / TECH LABS" type lockup (light/dark/compact) |
| `Eyebrow` | typography | uppercase mono gold kicker label |
| `SealHeading` | typography | section heading with the signature gold seal rule |

Each component directory carries `<Name>.jsx`, `<Name>.d.ts`, `<Name>.prompt.md`, and a `@dsCard` HTML showing its states.

**Intentional additions:** none. Every component maps to a pattern in the brand foundation. `Documents`/`Reports` screens in the UI kit reuse `EmptyState` rather than inventing new content, since the source defines no such views.

---

## UI kits

- **`ui_kits/elevionix-app/`** — interactive recreation of the Elevionix automation workspace. Click-through: **login → workspace**, with nav across **Workflows** (stat tiles + workflow table), **Approvals** (queue with approve/decline), **Matters** (the legal vertical — mono IDs, deep-orange deadlines), and Documents/Reports empty states. A "Start automation" button opens the new-workflow modal. Composes the DS components throughout. Also registered as a Starting Point.

No slide template was provided, so no sample slides were created.

---

## Foundations (Design System tab)

Specimen cards live in `guidelines/`, grouped **Colors** (brown / gold / yellow / orange families), **Type** (display / heading / body / data), **Spacing** (scale, radius & shadow), and **Brand** (logo, wordmark & seal).

---

## Index / manifest

- **`styles.css`** — root entry; `@import`s the four token files. Consumers link this one file.
- **`tokens/`** — `colors.css`, `typography.css`, `spacing.css`, `fonts.css`.
- **`components/`** — `buttons/`, `feedback/`, `forms/`, `surfaces/`, `brand/`, `typography/`.
- **`guidelines/`** — foundation specimen cards.
- **`ui_kits/elevionix-app/`** — the automation workspace recreation (`index.html` + screen JSX + `data.js`).
- **`assets/elevionix-logo.png`** — the saffron logo.
- **`thumbnail.html`** — homepage tile.
- **`SKILL.md`** — Agent-Skill wrapper for use in Claude Code.
