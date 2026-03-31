# Daily Explainability + Feedback Design

## Objective

Convert recommendation cards from "black-box scores" to trusted style decisions.

## Card Structure

Each suggestion card should include:
- outfit composition (`item_names`)
- plain-language match quality percentage
- factorized reasoning (`color`, `style`, `context`, `sustainability`)
- editorial explanation text
- optional evidence citations

## Feedback Actions

Expose high-intent actions directly on card:
- `Accept` (accepted=true, strong positive signal)
- `Skip` (accepted=false, negative signal)
- `Rate 4/5` (lightweight quality signal)
- `Log as worn` (behavioral confirmation)

## API Mapping

- `GET /api/v1/suggestions` for recommendation payload and reasoning breakdown
- `POST /api/v1/suggestions/{id}/feedback` for accept/rating
- `POST /api/v1/outfits/log` for worn-confirmation

## UX Guardrails

- Actions remain available even when one feedback call fails.
- Confirmation copy appears inline per card.
- No raw debug framing ("score 0.xyz") in the main user-facing hierarchy.

## Acceptance Criteria

- At least one explanation factor is visible per suggestion card.
- Feedback action success is acknowledged on-card.
- Users can log a worn outfit without leaving the Daily view.
