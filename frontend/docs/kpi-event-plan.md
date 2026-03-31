# KPI Event Instrumentation Plan

## Primary Metrics

- **Activation**: user generates first full daily recommendation in session
- **Time-to-Value**: time from login to first accepted suggestion
- **Recommendation Trust**: accepted suggestions / feedback submissions

## Event Schema

| Event | Trigger | Key Properties |
|---|---|---|
| `auth_session_ready` | user session established | `user_id`, `timestamp` |
| `guided_step_viewed` | guided card rendered | `step_status_profile`, `step_status_wardrobe`, `step_status_daily` |
| `wardrobe_item_created` | wardrobe item creation success | `category`, `color_family`, `source` |
| `first_suggestion_generated` | first successful Daily response in session | `mood`, `occasion`, `has_weather`, `count` |
| `suggestion_feedback_submitted` | feedback API success | `suggestion_id`, `accepted`, `rating`, `occasion` |
| `outfit_logged` | outfit log API success | `suggestion_id`, `item_count`, `mood`, `occasion` |

## Derived Computations

- **Activation rate** = users with `first_suggestion_generated` / authenticated users
- **Median time-to-value** = median(`suggestion_feedback_submitted(accepted=true)` - `auth_session_ready`)
- **Trust score** = accepted feedback / total feedback

## Minimal Rollout

1. emit core events in frontend interaction points
2. verify payload quality in console/log sink
3. build weekly KPI snapshot (activation, trust, time-to-value)

## Acceptance Criteria

- Events are emitted once per meaningful action (no duplicate spam).
- Event properties are sufficient to segment by mood/occasion/channel.
- Weekly KPI view can be computed from emitted events only.
