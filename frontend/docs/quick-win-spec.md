# Quick Win Specification (Week 1-2)

## Objective

Reduce friction and ambiguity in the existing experience without changing architecture.

## Quick Win A: Landing CTA Clarity

### Current Issue
- Secondary CTA implies direct studio entry, but unauthenticated users are redirected to login.

### Change
- Keep primary CTA: `Continue with magic link`.
- Rename secondary CTA to clarify auth expectation: `Open style studio (login required)`.
- Route secondary CTA to `/login` for expectation alignment.

### Acceptance Criteria
- Both CTAs on the public home lead users into a clear authentication path.
- No CTA text suggests access without sign-in.

## Quick Win B: Settings Email Context

### Current Issue
- Email field starts empty, despite known authenticated user email.

### Change
- Prefill settings email from authenticated user session.
- Show small context note with currently signed-in address.

### Acceptance Criteria
- Visiting settings displays the current email by default.
- Users can still edit and submit a new value.
- Success and error states remain visible and consistent.

## Quick Win C: Consistent Empty/Loading/Error States

### Current Issue
- Wardrobe and Daily pages have fragmented state handling and weak next-step guidance.

### Change
- Add clear loading labels, empty state blocks, and actionable helper text.
- Wardrobe empty state includes immediate "what to do next" copy.
- Daily empty state explains how to generate suggestions and what data is needed.

### Acceptance Criteria
- Loading state appears whenever API request is in progress.
- Empty state appears when data exists but is empty.
- Error state is visibly distinct and does not remove form controls.

## Implementation Scope

- `frontend/src/pages/PublicHome.tsx`
- `frontend/src/pages/SettingsPage.tsx`
- `frontend/src/pages/WardrobePage.tsx`
- `frontend/src/pages/DailyOutfitPage.tsx`
- `frontend/src/styles.css`
