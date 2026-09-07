# Style lock — BatteryWala operations portal

Established: 2026-09-07. Source: existing BatteryWala and Engine D-Carb brand material.

## Palette

- Background: #f3f6f4
- Surface: #ffffff
- Primary: #c94b10 (actions and active state)
- Primary dark: #9e3508 (links and hover)
- Text primary: #102e3c — 13.06:1 on background
- Text muted: #586c72 — 5.07:1 on background
- Button label: #ffffff — 4.67:1 on Primary
- Dark mode: not needed; single mode only

## Color contract

- Text-safe: text/surface, text/background, white/primary, white/primary-dark, muted/surface, muted/background, primary-dark/surface, success/surface, error/surface.
- UI-safe: primary/background, primary/border, text/primary.
- Decorative only: surface/border and background/border hairlines; never sole state indicators.
- Verified with `check_contrast.py --matrix` on 2026-09-07.

## Typography

- Heading and body: Inter with Segoe UI and Arial fallbacks.
- Scale: fluid display headings with compact 12–16px operational UI text.

## Shape language

- Radius: 8px controls, 14px panels, 22px primary cards.
- Soft low-opacity shadows on raised cards only; 1px hairlines elsewhere.

## Density & spacing

- Base unit: 4px; content card padding 28px; compact tiles 24px.
- Overall density: information-rich with generous section separation.
- Section separation: fixed spacing and hairline-contained panels.

## Reference intelligence

- Design read: operational dashboard for staff, mode Operate, technical visual lane.
- Dials: variance 4, motion 2, density 7, art direction 5.
- Foundation: existing Flask stack and source brand colors.
- Direction contract: immediate business switch; scannable live table; restrained technical surfaces; avoid generic gradient-heavy SaaS styling.

## Taste memory

- Profile priors used: none.
- Decision log: `.tastemaker/decisions.log`.
- Pending review: combined navy/orange portal direction.
- Profile promotion: none.

## Navigation chrome

- Navy sticky sidebar; pale content background.
- Active item: transparent row with a 3px orange left border.
- Inactive hover: white at 8% opacity.
- Shell density: 44px navigation rows and compact table text.

## Mood descriptors

Confident, technical, restrained.

## Assets

- Anchor assets: existing BatteryWala logo and Engine D-Carb source website.
- Logo treatment: preserved existing public identities; geometric portal mark is CSS-only.

## Motion

- Feel: quick and restrained.
- Curve: cubic-bezier(.23,1,.32,1).
- Durations: 120ms press/state, 220ms panel entrance, 10px rise.
- Repeated live-table polling does not animate.
- Reduced motion collapses to a 120ms opacity change.
- Verified by `audit_motion.py` on 2026-09-07.

## Do not

- No decorative gradients in the operational portal.
- No pill-shaped controls or excessive card grids.
- Do not mix BatteryWala and Engine D-Carb records in one export.
