# Guided First Run Design

## Goal

Ensure new users reach first meaningful value quickly:
1. profile context captured
2. wardrobe seeded
3. first recommendation generated

## Clickable Flow (Implemented in Dashboard)

- A persistent `Guided First Run` card is shown at the top of the dashboard.
- It displays step progress (`0/3`, `1/3`, etc.) and a `Continue setup` button.
- Button routes user to the next incomplete step:
  - step 1 -> `/dashboard/profile`
  - step 2 -> `/dashboard/wardrobe`
  - step 3 -> `/dashboard/daily`

## Completion Logic

- **Profile complete**: profile contains at least one meaningful identity signal.
- **Wardrobe complete**: at least one wardrobe item exists.
- **Daily complete**: at least one suggestion has been generated during the session.

## UX Copy Principles

- Keep instruction concise: "Profile -> Wardrobe -> Daily recommendation".
- Avoid punitive language; always show "next best action."
- Treat completion as progress, not as gatekeeping.

## Acceptance Criteria

- New user sees progress card before entering deep settings.
- `Continue setup` never points to a completed step if a later step is incomplete.
- Step indicators visibly switch to completed state.
- Daily step is marked done immediately after successful suggestion generation.
